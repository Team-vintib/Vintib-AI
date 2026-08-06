"""person1(긴팔 원본) + 반팔 셔츠 케이스의 갭 채우기 파이프라인을 한 장으로 시각화한다.

`result/alpha_test_gap_20260731_124316/alpha1_person1_shirt_*`에 이미 저장된 중간 산출물
(마스크·스킨 패치·after_skin·최종 결과)을 그대로 재사용하고, 저장 안 된 값(스킨 패치를
어디서 뽑았는지의 정확한 좌표)만 `AutoMasker`(DensePose/SCHP, diffusion 파이프라인은 불필요
— 가볍다)를 다시 돌려서 계산한다.

이 스크립트는 결과를 "만드는" 게 아니라 이미 나온 결과를 "설명"하는 용도다 — 팔뚝이 왜
아직도 소매처럼 보이는지(스킨 패치는 맞게 뽑혔는데, 생성 단계에서 주변 원본 재킷 색에
영향을 받는 것으로 보임)를 한 장으로 보여줘서, 다음 고도화 방향을 잡는 데 참고하게 한다.

pytest 안 걸림 — `python analyze_alpha1_gap_case.py`로 직접 실행 후 `result/`에 저장된
PNG를 육안 확인한다(기존 verify_*.py 관례).
"""

import os
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))
_PRODUCTION_CATVTON_PATH = os.path.join(_REPO_ROOT, "worker", "models", "catvton")
sys.path.insert(0, _PRODUCTION_CATVTON_PATH)

import numpy as np  # noqa: E402
from huggingface_hub import snapshot_download  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from model.adaptive_fit import classify_garment_length  # noqa: E402
from model.cloth_masker import AutoMasker, DENSE_INDEX_MAP, LIP_MAPPING, part_mask_of, split_mask_by_gap  # noqa: E402
from utils import resize_and_crop  # noqa: E402

RESULT_SRC_DIR = os.path.join("result", "alpha_test_gap_20260731_124316")
OUT_DIR = os.path.join("result", "analysis_alpha1_person1_shirt")
os.makedirs(OUT_DIR, exist_ok=True)

WIDTH, HEIGHT = 768, 1024
FONT_PATH = r"C:\Windows\Fonts\malgun.ttf"


def _font(size):
    return ImageFont.truetype(FONT_PATH, size)


print("=== AutoMasker 초기화 (diffusion 파이프라인 없이 마스킹만) ===")
repo_path = snapshot_download(repo_id="zhengchong/CatVTON")
automasker = AutoMasker(
    densepose_ckpt=os.path.join(repo_path, "DensePose"),
    schp_ckpt=os.path.join(repo_path, "SCHP"),
    device="cuda",
)
print("초기화 완료")

person_image = resize_and_crop(
    Image.open("image/alpha_1/person.png").convert("RGB"), (WIDTH, HEIGHT)
)

mask_result = automasker(person_image, mask_type="upper", fit_type="regular")
raw_mask = mask_result["mask"]
densepose_np = np.array(mask_result["densepose"])
schp_lip_np = np.array(mask_result["schp_lip"])

garment_measurements = {"SLEEVE_LENGTH": 22.0}
length_class = classify_garment_length("upper", garment_measurements)
garment_mask_np, gap_mask_np = split_mask_by_gap(np.array(raw_mask) // 255, densepose_np, "forearms")

# --- extract_skin_patch와 같은 로직으로 추출 지점(cy, cx)만 별도로 계산(시각화용) --------
face_area = part_mask_of(["Face"], schp_lip_np, LIP_MAPPING)
rows = np.where(face_area.any(axis=1))[0]
cols = np.where(face_area.any(axis=0))[0]
top, bottom = int(rows.min()), int(rows.max())
left, right = int(cols.min()), int(cols.max())
cheek_y = top + int((bottom - top) * 0.55)
extraction_point = None
for offset in (0.25, 0.75):
    cheek_x = left + int((right - left) * offset)
    if face_area[cheek_y, cheek_x]:
        extraction_point = (cheek_x, cheek_y)  # PIL은 (x, y)
        break
if extraction_point is None:
    extraction_point = (person_image.width // 2, person_image.height // 2)

print(f"classify_garment_length(upper) -> {length_class}")
print(f"extraction_point(x,y) -> {extraction_point}")
print(f"gap_mask pixel count -> {int(gap_mask_np.sum())}")

# --- 저장된 중간 산출물 로드 ------------------------------------------------------
skin_patch = Image.open(os.path.join(RESULT_SRC_DIR, "alpha1_person1_shirt_skin_patch.png"))
after_skin = Image.open(os.path.join(RESULT_SRC_DIR, "alpha1_person1_shirt_after_skin.png"))
final_result = Image.open(os.path.join(RESULT_SRC_DIR, "alpha1_person1_shirt_tryon.png"))
shirt_image = Image.open("image/alpha_1/shirt.png").convert("RGB")


def _panel(size=(360, 480)):
    img = Image.new("RGB", size, (255, 255, 255))
    return img


def _fit(image, size):
    return image.copy().resize(size)


PANEL_SIZE = (340, 460)


def _wrap_by_pixel_width(draw, text, font, max_width):
    """실제 렌더링 폭(textlength) 기준으로 줄바꿈한다 — 한글은 글자 수 기준 줄바꿈이 잘
    안 맞아서 픽셀 폭으로 직접 잰다."""
    lines = []
    current = ""
    for ch in text:
        candidate = current + ch
        if draw.textlength(candidate, font=font) > max_width and current:
            lines.append(current)
            current = ch
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def make_panel_with_caption(image, caption, size=PANEL_SIZE, caption_h=170):
    canvas = Image.new("RGB", (size[0], size[1] + caption_h), (255, 255, 255))
    canvas.paste(_fit(image, size), (0, 0))
    draw = ImageDraw.Draw(canvas)
    font = _font(15)
    lines = _wrap_by_pixel_width(draw, caption, font, size[0] - 12)
    y = size[1] + 8
    for ln in lines:
        draw.text((6, y), ln, fill=(20, 20, 20), font=font)
        y += 19
    return canvas


# --- Panel 1: 원본 + 추출 지점 + 갭(forearm) 영역 아웃라인 ------------------------
p1 = person_image.copy()
draw1 = ImageDraw.Draw(p1)
# 얼굴 bbox
draw1.rectangle([left, top, right, bottom], outline=(0, 140, 255), width=3)
# 추출 지점 마커
ex, ey = extraction_point
r = 10
draw1.ellipse([ex - r, ey - r, ex + r, ey + r], outline=(255, 0, 0), width=4)
draw1.text((ex + 14, ey - 10), "스킨 추출 지점(볼)", fill=(255, 0, 0), font=_font(18))
# 갭 영역(forearm) 아웃라인 — gap_mask_np에서 컨투어 대신 바운딩박스로 단순 표시
gap_rows = np.where(gap_mask_np.any(axis=1))[0]
gap_cols = np.where(gap_mask_np.any(axis=0))[0]
if len(gap_rows) and len(gap_cols):
    gy0, gy1 = int(gap_rows.min()), int(gap_rows.max())
    gx0, gx1 = int(gap_cols.min()), int(gap_cols.max())
    for x0, x1 in [(gx0, (gx0 + gx1) // 2 - 10), ((gx0 + gx1) // 2 + 10, gx1)]:
        pass  # (좌우 팔뚝이 하나의 바운딩박스로 합쳐지므로 아래에서 연결 좌표만 따로 계산)
# 좌/우 팔뚝을 따로 찾아 점선 박스 표시
gap_u8 = (gap_mask_np * 255).astype(np.uint8)
mid_x = gap_u8.shape[1] // 2
for side, (cs, ce) in (("left", (0, mid_x)), ("right", (mid_x, gap_u8.shape[1]))):
    sub = gap_u8[:, cs:ce]
    rows_s = np.where(sub.any(axis=1))[0]
    cols_s = np.where(sub.any(axis=0))[0]
    if len(rows_s) == 0:
        continue
    by0, by1 = int(rows_s.min()), int(rows_s.max())
    bx0, bx1 = cs + int(cols_s.min()), cs + int(cols_s.max())
    # 점선 사각형(짧은 선분을 반복해서 그려 점선 효과)
    for x in range(bx0, bx1, 10):
        draw1.line([(x, by0), (min(x + 5, bx1), by0)], fill=(255, 140, 0), width=3)
        draw1.line([(x, by1), (min(x + 5, bx1), by1)], fill=(255, 140, 0), width=3)
    for y in range(by0, by1, 10):
        draw1.line([(bx0, y), (bx0, min(y + 5, by1))], fill=(255, 140, 0), width=3)
        draw1.line([(bx1, y), (bx1, min(y + 5, by1))], fill=(255, 140, 0), width=3)
draw1.text((10, 10), "1) 원본 + 얼굴bbox(파랑) + 추출지점(빨강) + 갭영역(주황 점선)", fill=(0, 0, 0), font=_font(16))

# --- Panel 2: garment_mask(초록) / gap_mask(빨강) 오버레이 -----------------------
overlay_np = np.array(person_image).astype(np.float32)
garment_overlay = np.zeros_like(overlay_np)
garment_overlay[..., 1] = 255  # green
gap_overlay = np.zeros_like(overlay_np)
gap_overlay[..., 0] = 255  # red

g_alpha = (garment_mask_np[..., None] * 0.45)
r_alpha = (gap_mask_np[..., None] * 0.55)
blended = overlay_np * (1 - g_alpha) + garment_overlay * g_alpha
blended = blended * (1 - r_alpha) + gap_overlay * r_alpha
p2 = Image.fromarray(blended.astype(np.uint8))
draw2 = ImageDraw.Draw(p2)
draw2.text((10, 10), "2) 마스크 분리: 초록=의류 영역, 빨강=갭(피부) 영역", fill=(255, 255, 255), font=_font(16))

# --- Panel 3: 레퍼런스 의류 ------------------------------------------------------
p3 = shirt_image.copy()

# --- Panel 4: 스킨 패치(확대) ----------------------------------------------------
p4_thumb = skin_patch.resize((PANEL_SIZE[0] - 40, PANEL_SIZE[0] - 40))
p4 = Image.new("RGB", PANEL_SIZE, (255, 255, 255))
p4.paste(p4_thumb, (20, 60))
ImageDraw.Draw(p4).text((10, 10), "④ 추출된 스킨 패치(①의 조건 이미지)", fill=(0, 0, 0), font=_font(16))

# --- Panel 5: after_skin(1차 생성: 갭만 스킨 패치로 채움) -------------------------
p5 = after_skin.copy()

# --- Panel 6: 최종 결과(2차 생성: 의류 패스 적용) --------------------------------
p6 = final_result.copy()

panels = [
    make_panel_with_caption(p1, "① 원본 사진 — 파랑 박스: 얼굴 인식 범위. 빨강 원: 스킨 패치를 뽑은 지점(볼). 주황 점선: 이번에 채워야 할 갭(팔뚝) 범위."),
    make_panel_with_caption(p2, "② 마스크 분리 결과 — 초록: 레퍼런스 의류(반팔 셔츠)로 채울 영역. 빨강: 스킨 패치로 채울 갭 영역. 둘은 겹치지 않는다. (배경 인물도 초록으로 잡힌 건 별개 이슈 — 아래 분석 참고)"),
    make_panel_with_caption(p3, "③ 레퍼런스 의류 — 이 반팔 셔츠 사진이 초록 영역(②)의 조건 이미지로 들어간다."),
    make_panel_with_caption(p4, "④ ①의 빨강 원 지점에서 뽑은 40x40 스킨 패치 — 빨강 영역(갭)의 조건 이미지로 들어간다."),
    make_panel_with_caption(p5, "⑤ 1차 생성 결과(스킨 패스만 적용) — 빨강(갭) 영역만 스킨 패치 조건으로 먼저 채운 중간 상태. 팔뚝이 ④ 패치 색보다 원래 재킷 색에 더 가깝다 — 조건 이미지보다 인접한 원본 재킷 색의 영향이 더 크다는 뜻."),
    make_panel_with_caption(p6, "⑥ 최종 결과(2차 생성: ⑤ 위에 초록 영역만 셔츠로 덮음) — 상의는 셔츠로 바뀌었지만 팔뚝은 ⑤의 문제가 그대로 남아 소매처럼 보인다."),
]

cols_n = 3
rows_n = 2
pad = 24
panel_w, panel_h = panels[0].size
canvas_w = cols_n * panel_w + (cols_n + 1) * pad
canvas_h = rows_n * panel_h + (rows_n + 1) * pad + 140
canvas = Image.new("RGB", (canvas_w, canvas_h), (250, 250, 250))
draw = ImageDraw.Draw(canvas)
draw.text(
    (pad, 16),
    "알파테스트1 (person1: 긴팔 원본 + 반팔 셔츠) — 갭 채우기 파이프라인 진단",
    fill=(0, 0, 0),
    font=_font(26),
)
draw.text(
    (pad, 55),
    f"classify_garment_length(upper, SLEEVE_LENGTH=22.0) -> {length_class}"
    f" | gap_fill_used -> {bool(gap_mask_np.any())} | gap pixel 수 -> {int(gap_mask_np.sum())}",
    fill=(60, 60, 60),
    font=_font(18),
)
top_y = 110
for i, panel in enumerate(panels):
    r, c = divmod(i, cols_n)
    x = pad + c * (panel_w + pad)
    y = top_y + pad + r * (panel_h + pad)
    canvas.paste(panel, (x, y))

# 화살표: ①의 추출 지점 -> ④ 스킨 패치 패널로
p1_x, p1_y = pad, top_y + pad
p4_col, p4_row = 0, 1
p4_x = pad + p4_col * (panel_w + pad)
p4_y = top_y + pad + 1 * (panel_h + pad)
start = (p1_x + extraction_point[0] * (PANEL_SIZE[0] / WIDTH), p1_y + extraction_point[1] * (PANEL_SIZE[1] / HEIGHT))
end = (p4_x + PANEL_SIZE[0] // 2, p4_y)
draw.line([start, end], fill=(255, 0, 0), width=3)
ax, ay = end
draw.polygon([(ax - 8, ay - 12), (ax + 8, ay - 12), (ax, ay)], fill=(255, 0, 0))
draw.text(((start[0] + end[0]) // 2 + 10, (start[1] + end[1]) // 2), "패치 추출", fill=(255, 0, 0), font=_font(16))

out_path = os.path.join(OUT_DIR, "alpha1_person1_shirt_pipeline_analysis.png")
canvas.save(out_path)
print(f"\n완료 -> {out_path}")
