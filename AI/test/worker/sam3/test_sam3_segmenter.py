"""`worker/models/sam3/segmenter.py`의 `SegmentationResult.garment_crop` 필드 검증.

`Sam3PcsSegmenter`(실 모델)는 torch가 필요해 여기서 못 돈다 — `MockSegmenter`가 항상
`garment_crop=None`을 내는지만 확인한다(유사 상품 추천용 임베딩은 실 backend에서만 계산돼야
한다, mock에는 진짜 크롭이 없어서다).
"""

from sam3.contracts import BaseColor, GarmentCategory
from sam3.prompts import select_prompt_set
from sam3.segmenter import InspectionTarget, MockSegmenter


def test_mock_segmenter_never_produces_a_garment_crop():
    prompt_set = select_prompt_set(GarmentCategory.top_knit, BaseColor.light)
    target = InspectionTarget(
        product_id=1, image_urls=("https://x/front.jpg",), prompt_set=prompt_set
    )

    result = MockSegmenter().segment(target, image_index=0)

    assert result.garment_crop is None
