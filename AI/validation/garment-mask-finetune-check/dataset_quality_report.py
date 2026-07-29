"""
데이터셋 품질/라벨링 상태 점검 리포트 (Jira S15P11A108-178: 파인튜닝 데이터셋 탐색 및 검증)

의류 통합 데이터·의류 가상착용 3D 이미지·K-Fashion 이미지 세 데이터셋을 dataset.py의
파서로 훑어, 카테고리별 폴리곤 인스턴스 수·해상도 분포·이미지-라벨 매칭/파싱 실패
건수를 리포트한다. collect_samples()는 실패 건을 조용히 건너뛰므로, 이 스크립트는
dataset_specs()를 직접 순회해 실패 사유까지 드러낸다.

"연도별 패션 선호도 파악 및 추천 데이터"는 시착과 무관한 추천 기능 자료라(Notion
LAB-24 전략 검토 참고) 이 리포트 대상에서 제외한다.

실행 전 준비사항:
- dataset.py의 DATASET_ROOT를 로컬 sample_dsets 경로로 조정할 것
- pip install -r AI/test/requirements-test.txt (Pillow 포함, torch는 불필요)
"""

import json
from collections import Counter, defaultdict
from pathlib import Path

from dataset import CLASS_NAMES, DATASET_ROOT, Sample, collect_samples, dataset_specs
from PIL import Image, UnidentifiedImageError


def check_matching_and_parsing(dataset_root: Path) -> dict[str, dict[str, int]]:
    """spec별로 이미지 대비 라벨 매칭 실패/파싱 실패/손상 이미지 건수를 센다."""
    report: dict[str, dict[str, int]] = {}

    for spec in dataset_specs(dataset_root):
        if not spec.images_root.exists():
            report[spec.source] = {"images_root_missing": 1}
            continue

        total_images = 0
        missing_label = 0
        unparseable_or_empty_label = 0
        corrupt_image = 0

        for image_path in spec.images_root.rglob("*"):
            if image_path.suffix.lower() not in spec.image_exts:
                continue
            total_images += 1

            relative = image_path.relative_to(spec.images_root)
            label_path = spec.labels_root / relative.with_suffix(spec.label_ext)
            if not label_path.exists():
                missing_label += 1
                continue

            try:
                polygons = spec.parser(label_path)
            except (json.JSONDecodeError, KeyError, ValueError, TypeError):
                unparseable_or_empty_label += 1
                polygons = None
            if polygons is not None and not polygons:
                unparseable_or_empty_label += 1

            try:
                with Image.open(image_path) as image:
                    image.verify()
            except (UnidentifiedImageError, OSError):
                corrupt_image += 1

        report[spec.source] = {
            "total_images": total_images,
            "missing_label": missing_label,
            "unparseable_or_empty_label": unparseable_or_empty_label,
            "corrupt_image": corrupt_image,
        }

    return report


def report_category_and_resolution_stats(dataset_root: Path) -> None:
    samples = collect_samples(dataset_root)
    print(f"수집된 (이미지, 라벨) 쌍 총합: {len(samples)}개\n")

    by_source: dict[str, list[Sample]] = defaultdict(list)
    for sample in samples:
        by_source[sample.source].append(sample)

    for source, source_samples in by_source.items():
        print(f"--- {source} ({len(source_samples)}장) ---")

        category_counter: Counter[str] = Counter()
        widths: list[int] = []
        heights: list[int] = []
        for sample in source_samples:
            for _, category in sample.polygons:
                category_counter[category] += 1
            try:
                with Image.open(sample.image_path) as image:
                    widths.append(image.width)
                    heights.append(image.height)
            except (UnidentifiedImageError, OSError):
                continue

        for category in CLASS_NAMES[1:]:
            print(f"  {category:8s}: 폴리곤 인스턴스 {category_counter.get(category, 0)}개")

        if widths:
            avg_w = sum(widths) / len(widths)
            avg_h = sum(heights) / len(heights)
            print(
                f"  해상도: width [{min(widths)}~{max(widths)}] "
                f"height [{min(heights)}~{max(heights)}] (평균 {avg_w:.0f}x{avg_h:.0f})"
            )
        print()


def main() -> None:
    print("=== 이미지-라벨 매칭 및 파싱 실패 점검 ===")
    for source, stats in check_matching_and_parsing(DATASET_ROOT).items():
        print(f"{source}: {stats}")
    print()

    print("=== 카테고리별 분포 및 해상도 통계 ===")
    report_category_and_resolution_stats(DATASET_ROOT)


if __name__ == "__main__":
    main()
