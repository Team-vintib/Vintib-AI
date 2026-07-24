"""
의류 세그멘테이션 파인튜닝용 데이터셋 로더 (LAB-24 1순위 전략 PoC)

서로 다른 폴리곤 라벨 스키마를 쓰는 세 AIHub 데이터셋(의류 통합 데이터, 의류 가상착용
3D 이미지, K-Fashion 이미지)을 공통 4-클래스 taxonomy(상의/하의/아우터/원피스)로
통일해 (이미지, 멀티클래스 마스크) 쌍을 만든다. finetune_segmentation.py /
evaluate_masks.py / compare_with_schp_baseline.py에서 공용으로 import한다.

실행 전 준비사항:
- 아래 DATASET_ROOT를 로컬 sample_dsets 경로(리포 밖)에 맞게 조정할 것
- pip install -r AI/test/requirements-test.txt (torch, Pillow, numpy 포함)
"""

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageDraw
from torch.utils.data import Dataset

# ---- 설정 ----
# 리포 밖에 있는 로컬 sample_dsets 경로. 실행자 환경에 맞게 조정할 것.
DATASET_ROOT = Path(r"C:\Users\SSAFY\Downloads\PJT\AI\sample_dsets")

CLASS_NAMES = ["background", "상의", "하의", "아우터", "원피스"]
CLASS_TO_IDX = {name: idx for idx, name in enumerate(CLASS_NAMES)}

Point = tuple[float, float]
Polygon = tuple[list[Point], str]  # (좌표 목록, 카테고리명)


@dataclass
class Sample:
    image_path: Path
    polygons: list[Polygon]
    source: str  # "integrated" | "tryon3d" | "kfashion"


# ---------------------------------------------------------------------------
# 카테고리 추론 (파일명/경로에 박힌 토큰 기반)
# ---------------------------------------------------------------------------


def _infer_category_from_text(text: str) -> str | None:
    lowered = text.lower()
    if "outer" in lowered:
        return "아우터"
    if "onepiece" in lowered or "dress" in lowered:
        return "원피스"
    if "bottom" in lowered:
        return "하의"
    if "top" in lowered:
        return "상의"
    return None


# ---------------------------------------------------------------------------
# 데이터셋별 라벨 파서: json 경로 -> [(points, category)]
# ---------------------------------------------------------------------------


def _points_from_flat(flat: list[float]) -> list[Point]:
    return list(zip(flat[0::2], flat[1::2], strict=True))


def parse_integrated_dataset_label(json_path: Path) -> list[Polygon]:
    """의류 통합 데이터: annotation[].annotation_point가 평탄화된 [x1,y1,x2,y2,...] 리스트.

    카테고리 필드가 없어 dataset.image_path의 파일명 토큰(01outer/02top/03-1onepiece/
    03-2onepiece/04bottom)으로 추론한다.
    """
    data = json.loads(json_path.read_text(encoding="utf-8"))
    dataset_info = data.get("dataset", {})
    stem = Path(dataset_info.get("image_path", json_path.name)).stem
    category = _infer_category_from_text(stem)
    if category is None:
        return []

    polygons: list[Polygon] = []
    for annotation in data.get("annotation", []):
        if annotation.get("annotation_type") != "Polygon":
            continue
        points = _points_from_flat(annotation.get("annotation_point") or [])
        if len(points) >= 3:
            polygons.append((points, category))
    return polygons


def parse_tryon3d_label(json_path: Path) -> list[Polygon]:
    """의류 가상착용 3D 이미지: labelme 스타일 shapes[].points ([[x,y], ...]).

    카테고리 필드(label)는 shorts/long pants 같은 세부 종류라 우리 4-클래스와 맞지
    않으므로, 대신 경로에 박힌 상위 카테고리 토큰(bottoms 등)으로 추론한다.
    """
    data = json.loads(json_path.read_text(encoding="utf-8"))
    category = _infer_category_from_text(str(json_path))
    if category is None:
        return []

    polygons: list[Polygon] = []
    for shape in data.get("shapes", []):
        if shape.get("shape_type") != "polygon":
            continue
        points = [(float(x), float(y)) for x, y in shape.get("points", [])]
        if len(points) >= 3:
            polygons.append((points, category))
    return polygons


_KFASHION_POINT_KEY = re.compile(r"^([XY])좌표(\d+)$")


def _parse_kfashion_point_dict(entry: dict) -> list[Point]:
    xs: dict[int, float] = {}
    ys: dict[int, float] = {}
    for key, value in entry.items():
        match = _KFASHION_POINT_KEY.match(key)
        if not match:
            continue
        axis, idx = match.group(1), int(match.group(2))
        (xs if axis == "X" else ys)[idx] = value
    indices = sorted(set(xs) & set(ys))
    return [(xs[i], ys[i]) for i in indices]


def parse_kfashion_label(json_path: Path) -> list[Polygon]:
    """K-Fashion: 폴리곤좌표.{아우터,하의,원피스,상의}[0]이 X좌표N/Y좌표N 키를 가진 딕셔너리.

    카테고리가 이미 우리 4-클래스 taxonomy와 정확히 일치하는 가장 깨끗한 소스.
    """
    data = json.loads(json_path.read_text(encoding="utf-8"))
    detail = data.get("데이터셋 정보", {}).get("데이터셋 상세설명", {})
    poly_section = detail.get("폴리곤좌표", {})

    polygons: list[Polygon] = []
    for category in ("상의", "하의", "아우터", "원피스"):
        for entry in poly_section.get(category) or []:
            points = _parse_kfashion_point_dict(entry)
            if len(points) >= 3:
                polygons.append((points, category))
    return polygons


# ---------------------------------------------------------------------------
# 래스터화: 폴리곤 -> 멀티클래스 마스크
# ---------------------------------------------------------------------------


def rasterize(image_size: tuple[int, int], polygons: list[Polygon]) -> np.ndarray:
    """polygons를 (W, H) 크기의 멀티클래스 마스크(0=배경, 1..4=CLASS_NAMES 인덱스)로 그린다.

    겹치는 영역은 polygons 리스트의 뒤쪽 항목이 앞쪽을 덮어쓴다.
    """
    mask = Image.new("L", image_size, 0)
    draw = ImageDraw.Draw(mask)
    for points, category in polygons:
        class_idx = CLASS_TO_IDX.get(category)
        if class_idx is None or len(points) < 3:
            continue
        draw.polygon(points, fill=class_idx)
    return np.array(mask, dtype=np.uint8)


# ---------------------------------------------------------------------------
# 데이터셋 전체 수집
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DatasetSpec:
    source: str
    images_root: Path
    labels_root: Path
    image_exts: tuple[str, ...]
    label_ext: str
    parser: Callable[[Path], list[Polygon]]


def dataset_specs(dataset_root: Path) -> list[DatasetSpec]:
    """collect_samples()와 dataset_quality_report.py가 공유하는 데이터셋별 스펙.

    dataset_quality_report.py는 collect_samples()가 조용히 건너뛰는 매칭/파싱 실패
    건수까지 점검해야 해서 이 스펙을 직접 순회한다.
    """
    return [
        DatasetSpec(
            source="integrated",
            images_root=dataset_root / "의류 통합 데이터" / "Sample" / "01.원천데이터" / "상품",
            labels_root=dataset_root / "의류 통합 데이터" / "Sample" / "02.라벨링데이터",
            image_exts=(".jpg", ".jpeg"),
            label_ext=".json",
            parser=parse_integrated_dataset_label,
        ),
        DatasetSpec(
            source="tryon3d",
            images_root=(
                dataset_root
                / "의류 가상착용 3D 이미지"
                / "원천데이터"
                / "상품_미착용_Product(2D)_bottoms"
            ),
            labels_root=(
                dataset_root
                / "의류 가상착용 3D 이미지"
                / "라벨링데이터"
                / "상품_미착용_Product(2D)_bottoms"
            ),
            image_exts=(".jpg", ".jpeg"),
            label_ext=".json",
            parser=parse_tryon3d_label,
        ),
        DatasetSpec(
            source="kfashion",
            images_root=dataset_root / "K-Fashion 이미지" / "원천데이터" / "원천데이터_1",
            labels_root=dataset_root / "K-Fashion 이미지" / "라벨링데이터",
            image_exts=(".jpg", ".jpeg"),
            label_ext=".json",
            parser=parse_kfashion_label,
        ),
    ]


def collect_samples(dataset_root: Path = DATASET_ROOT) -> list[Sample]:
    """dataset_root 아래 세 데이터셋을 모두 훑어 (이미지, 라벨) 쌍을 모은다.

    이미지-라벨 매칭은 각 데이터셋의 images_root/labels_root 아래 동일한 상대경로 +
    파일명(stem)으로 이루어진다.
    """
    samples: list[Sample] = []
    for spec in dataset_specs(dataset_root):
        if not spec.images_root.exists():
            continue
        for image_path in spec.images_root.rglob("*"):
            if image_path.suffix.lower() not in spec.image_exts:
                continue
            relative = image_path.relative_to(spec.images_root)
            label_path = spec.labels_root / relative.with_suffix(spec.label_ext)
            if not label_path.exists():
                continue
            polygons = spec.parser(label_path)
            if polygons:
                samples.append(Sample(image_path=image_path, polygons=polygons, source=spec.source))
    return samples


# ---------------------------------------------------------------------------
# torch Dataset
# ---------------------------------------------------------------------------


class GarmentSegDataset(Dataset):
    def __init__(self, samples: list[Sample], image_size: tuple[int, int] = (512, 512)):
        self.samples = samples
        self.image_size = image_size

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor]:
        sample = self.samples[index]
        image = Image.open(sample.image_path).convert("RGB")
        mask = rasterize(image.size, sample.polygons)

        image = image.resize(self.image_size, Image.BILINEAR)
        mask_img = Image.fromarray(mask).resize(self.image_size, Image.NEAREST)

        image_tensor = torch.from_numpy(np.array(image)).permute(2, 0, 1).float() / 255.0
        mask_tensor = torch.from_numpy(np.array(mask_img)).long()
        return image_tensor, mask_tensor
