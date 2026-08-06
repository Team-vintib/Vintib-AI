"""시착 결과 "한 줄 핏 예상" 텍스트 — 순수 계산.

설계: `docs/plans/AI/CH020-tryon-fit-summary-text.md`

`adaptive_fit.compute_width_adjustment()`가 이미 계산하는 비율(ratio)을 그대로 입력받아
고객이 보는 화면용 한국어 한 줄로 바꾼다 — FE `LiveTryOnMockResult`(`fitTitle`/
`fitDescription`, `FE/src/domains/tryon/constants/liveTryOnMockData.ts`) 계약과 형태를
맞춘다.

임계값은 `AI/validation/TRYON/AI_tryon/CatVTON/generate_worn_reference_{jeans,top,
outer}_fitaware.py`의 `fit_descriptor()`가 이미 실측으로 검증한 구간(0.95~1.05 레귤러,
0.85·1.15·1.30 경계)을 그대로 재사용한다 — 다만 그쪽은 FLUX 이미지 생성용 영어 시각
묘사(과장된 톤, "second-skin" 등)이고, 이건 고객 안내용 담백한 한국어라는 점이 다르다.

**입력이 없으면(`None`) 결과도 `None`이다** — `adaptive_fit.py`와 같은 원칙. 호출부가
`None`을 보면 문구 자체를 노출하지 않는다(부정확한 추측을 보여주는 대신 침묵한다).
"""

from __future__ import annotations

from typing import Literal

PartName = Literal["waist", "chest"]

_AREA_LABEL: dict[PartName, str] = {
    "waist": "허리",
    "chest": "가슴과 어깨",
}


def fit_summary_ko(ratio: float | None, part: PartName) -> dict[str, str] | None:
    """비율(ratio, `garment_flat_width_cm / (body_circumference_cm / 2.0)`, 1.0 근처가
    레귤러)을 고객용 한 줄 핏 예상으로 바꾼다.

    반환: `{"title": str, "description": str}` 또는 `ratio`가 `None`이면 `None`.
    """
    if ratio is None:
        return None

    area = _AREA_LABEL[part]
    pct = round(abs(ratio - 1.0) * 100)

    if 0.95 <= ratio <= 1.05:
        return {
            "title": "선택하신 사이즈가 적당해요.",
            "description": f"{area} 부분이 몸에 잘 맞는 기본 핏으로 예상돼요.",
        }
    if ratio < 0.95:
        if ratio <= 0.85:
            return {
                "title": "선택하신 사이즈가 타이트할 수 있어요.",
                "description": f"{area} 부분이 몸에 붙는 타이트한 핏으로 예상돼요 (기준보다 약 {pct}% 작아요).",
            }
        return {
            "title": "선택하신 사이즈가 살짝 타이트해요.",
            "description": f"{area} 부분이 살짝 붙는 느낌으로 예상돼요 (기준보다 약 {pct}% 작아요).",
        }
    if ratio >= 1.30:
        return {
            "title": "선택하신 사이즈가 넉넉한 오버사이즈예요.",
            "description": f"{area} 부분에 여유가 많은 오버사이즈 핏으로 예상돼요 (기준보다 약 {pct}% 커요).",
        }
    if ratio >= 1.15:
        return {
            "title": "선택하신 사이즈가 여유있게 맞아요.",
            "description": f"{area} 부분에 여유가 있는 루즈한 핏으로 예상돼요 (기준보다 약 {pct}% 커요).",
        }
    return {
        "title": "선택하신 사이즈가 살짝 여유있어요.",
        "description": f"{area} 부분이 약간 넉넉한 편안한 핏으로 예상돼요 (기준보다 약 {pct}% 커요).",
    }
