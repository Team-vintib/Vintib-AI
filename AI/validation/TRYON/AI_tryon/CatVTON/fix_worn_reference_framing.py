"""FLUX worn-reference 생성 시, 옷이 오버사이즈로 묘사될수록 카메라가 인물을 확대(줌인)해서
찍는 프레이밍 버그를 후처리로 고친다.

1차 시도(배경색과의 픽셀 차이로 전경 검출)는 흰 운동화가 흰 배경과 색이 거의 같아서
바운딩박스를 신뢰할 수 없었다(실제로는 XXL에서 발이 프레임 밖으로 잘려나갔는데도 색상
임계값 검출로는 M과 거의 같은 bbox로 나옴). CatVTON의 AutoMasker가 이미 로드하는 SCHP
인체 파싱(`process_schp_atr` -- Background=0, Left-shoe/Right-shoe 클래스 포함)을 대신
써서, 색상이 아니라 의미 기반으로 사람 실루엣(신발 포함)을 검출한다.

기준을 worn-reference 중 하나(예: M)로 잡으면 그 자체도 이미 원본 대비 얼마나 틀어졌는지
알 수 없다는 문제가 있다(실측 결과 M도 진짜 원본보다 이미 3.5% 확대돼 있었다). 그래서
AI 모델 생성에 쓰인 진짜 원본 중립 사진(`models_ai_generated/{person}.png`, 옷 없는
베이스)을 참 기준으로 삼는다.

전신(발끝까지 포함) bbox는 스케일 지표로 못 쓴다 -- 실측해보니 아래쪽이 이미지 맨 아래
행(1023)에 거의 항상 닿아서(신발이 배경과 색이 비슷해 경계가 애매하거나, 실제로 프레임
밖으로 잘려서) 사이즈가 달라져도 bbox 높이가 992~993으로 거의 안 바뀌는 포화 현상이
있었다. 반면 머리(Hair|Face, 옷과 완전히 무관한 부위)만 따로 재보면 M~XXL 사이에 head
height가 188->260px(38% 증가)로 뚜렷하게 벌어졌다 -- 이게 실제 "인물이 확대되는" 버그의
진짜 신호다. 그래서 스케일/재배치 기준을 머리 bbox로 잡는다.
"""

import os

import numpy as np
from huggingface_hub import snapshot_download
from PIL import Image

from model.cloth_masker import AutoMasker
from utils import resize_and_crop

WIDTH, HEIGHT = 768, 1024


HAIR_CLASS = 2
FACE_CLASS = 11


def compute_head_bbox(automasker: AutoMasker, image: Image.Image) -> tuple[int, int, int, int]:
    """(top, bottom, left, right) -- SCHP ATR 파싱에서 Hair|Face 픽셀만. 옷(재킷 폭 등)과
    무관하게 사람 자체의 스케일을 알려주는 지표라 정규화 기준으로 쓴다."""
    parse = np.array(automasker.process_schp_atr(image))
    fg_mask = (parse == HAIR_CLASS) | (parse == FACE_CLASS)
    rows = np.where(fg_mask.any(axis=1))[0]
    cols = np.where(fg_mask.any(axis=0))[0]
    if len(rows) == 0 or len(cols) == 0:
        raise ValueError("머리를 찾지 못했습니다")
    return int(rows[0]), int(rows[-1]), int(cols[0]), int(cols[-1])


def estimate_bg_color(image: Image.Image, patch: int = 15) -> tuple[int, int, int]:
    arr = np.array(image.convert("RGB")).astype(np.int16)
    corners = np.concatenate([
        arr[:patch, :patch].reshape(-1, 3),
        arr[:patch, -patch:].reshape(-1, 3),
        arr[-patch:, :patch].reshape(-1, 3),
        arr[-patch:, -patch:].reshape(-1, 3),
    ])
    return tuple(corners.mean(axis=0).round().astype(int).tolist())


def normalize_vertical_scale(image: Image.Image, src_bbox: tuple[int, int, int, int], ref_bbox: tuple[int, int, int, int]) -> Image.Image:
    """src_bbox(top,bottom,left,right)의 세로 길이를 ref_bbox 세로 길이에 맞춰 이미지 전체를
    스케일하고, 사람의 세로 중심이 ref_bbox의 세로 중심과 같은 위치에 오도록 캔버스에
    재배치한다(가로는 원래 중심을 유지)."""
    top, bottom, left, right = src_bbox
    ref_top, ref_bottom, _, _ = ref_bbox

    src_height = bottom - top
    ref_height = ref_bottom - ref_top
    scale = ref_height / src_height

    scaled_w, scaled_h = round(image.width * scale), round(image.height * scale)
    scaled = image.resize((scaled_w, scaled_h), Image.LANCZOS)

    src_center_y = (top + bottom) / 2
    ref_center_y = (ref_top + ref_bottom) / 2
    src_center_x = (left + right) / 2

    scaled_center_y = round(src_center_y * scale)
    scaled_center_x = round(src_center_x * scale)

    paste_y = round(ref_center_y) - scaled_center_y
    paste_x = round(src_center_x) - scaled_center_x  # 가로는 원래 중심 위치를 그대로 유지

    canvas = Image.new("RGB", (WIDTH, HEIGHT), estimate_bg_color(image))
    canvas.paste(scaled, (paste_x, paste_y))
    return canvas


def main(person_name: str, sizes: list[str], name_prefix: str):
    print("=== AutoMasker(SCHP) 초기화 ===")
    repo_path = snapshot_download(repo_id="zhengchong/CatVTON")
    automasker = AutoMasker(
        densepose_ckpt=os.path.join(repo_path, "DensePose"),
        schp_ckpt=os.path.join(repo_path, "SCHP"),
        device="cuda",
    )
    print("초기화 완료")

    orig_path = os.path.join("..", "models_ai_generated", f"{person_name}.png")
    orig_image = resize_and_crop(Image.open(orig_path).convert("RGB"), (WIDTH, HEIGHT))
    ref_bbox = compute_head_bbox(automasker, orig_image)
    print(f"참 기준(원본 {person_name}.png) bbox: top={ref_bbox[0]} bottom={ref_bbox[1]} left={ref_bbox[2]} right={ref_bbox[3]} (height={ref_bbox[1]-ref_bbox[0]})")

    ref_dir = os.path.join("result", "worn_references")
    for size_label in sizes:
        path = os.path.join(ref_dir, f"{name_prefix}_worn_reference_{person_name}_{size_label}.png")
        image = Image.open(path).convert("RGB")
        before_bbox = compute_head_bbox(automasker, image)
        normalized = normalize_vertical_scale(image, before_bbox, ref_bbox)
        after_bbox = compute_head_bbox(automasker, normalized)
        image.save(path.replace(".png", "_before_framing_fix.png"))
        normalized.save(path)
        print(
            f"{size_label}: height {before_bbox[1]-before_bbox[0]} -> {after_bbox[1]-after_bbox[0]} "
            f"(bbox {before_bbox} -> {after_bbox}, 덮어씀, 원본은 *_before_framing_fix.png로 백업)"
        )


if __name__ == "__main__":
    main(
        person_name="heedongi",
        sizes=["M", "L", "XL", "XXL"],
        name_prefix="outer",
    )
