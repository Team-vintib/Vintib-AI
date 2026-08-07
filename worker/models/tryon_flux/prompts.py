"""핏 묘사 문구 생성 — `AI/validation/TRYON/AI_tryon/CatVTON/generate_worn_reference_
top_fitaware.py`(§10.1)에서 검증한 티어를 그대로 승격했다. 원래는 몸 축(가슴/허리/어깨/
소매)별로 4개 함수가 있었는데, 지금 실제로 확보되는 데이터는 축 하나뿐이라(예: 바지는
`body_waist_cm` ↔ `garment_measurements["WAIST_WIDTH"]`) 범용 단일 축 함수로 단순화했다.
다른 축(가슴/어깨 등) 데이터가 생기면 같은 함수를 그 축에도 그대로 재사용할 수 있다.
"""

# (상한 ratio, 문구, 강조 재배치 필요 여부) -- ratio 오름차순.
# 강조 재배치(needs_emphasis=True)는 극단(아주 타이트/아주 루즈) 구간에서만 켠다 -- FLUX.2의
# 텍스트 인코더(AutoModelForCausalLM)가 문장 앞쪽 내용에 더 강하게 반응해서, 실루엣 묘사를
# 맨 앞으로 옮기고 "아닌 것"도 명시해야 학습된 기본 편향(평범한 핏)을 상쇄할 수 있다
# (AI/docs/tryon-advancement-strategy.md §9/§10.1에서 확립).
_TIGHT_TABLE: list[tuple[float, str, bool]] = [
    (0.65, "crushed impossibly tight, the fabric stretched to tearing point, a "
           "second-skin silhouette with zero slack fabric anywhere", True),
    (0.72, "stretched to its absolute limit, clinging tightly to the exact contour "
           "like a compression garment, a second-skin silhouette instead of the "
           "garment's normal relaxed cut", True),
    (0.79, "clinging tightly to the contour with very little slack fabric, a "
           "noticeably fitted, skin-tight silhouette instead of the garment's "
           "normal relaxed cut", True),
    (0.85, "clinging closely to the contour with little slack fabric, a noticeably "
           "more fitted silhouette than the garment's normal relaxed cut", False),
    (0.90, "fitting close with only a little slack fabric, slightly more fitted "
           "than the garment's normal relaxed cut", False),
    (0.95, "worn snugly, fitting close and slightly tight", False),
]
_LOOSE_TABLE: list[tuple[float, str, bool]] = [
    (1.10, "worn in a relaxed, very slightly loose fit", False),
    (1.16, "worn in a noticeably loose fit with visible extra room", False),
    (1.23, "worn in a loose, roomy fit with clearly visible extra fabric", False),
    (1.30, "worn in a baggy fit with excess room", False),
    (1.40, "worn in a very baggy fit that visibly drapes away from the body", True),
    (1.55, "worn in an oversized fit, swimming in excess fabric that drapes far "
           "away from the body", True),
    (float("inf"), "worn in an extremely oversized fit, engulfed in excess fabric "
                   "that drapes far away from the body, like wearing a garment "
                   "several sizes too large", True),
]


def fit_descriptor(ratio: float) -> tuple[str, bool]:
    """ratio = garment_measurement_cm / body_measurement_cm (1.0 근처가 중립).

    반환값: (핏 묘사 절 + 실제 % 수치, 강조 재배치 필요 여부).
    """
    pct = abs(ratio - 1.0) * 100
    if 0.95 <= ratio <= 1.05:
        return "fitting comfortably in a regular fit", False
    table = _TIGHT_TABLE if ratio < 0.95 else _LOOSE_TABLE
    direction = "too small" if ratio < 0.95 else "too big"
    for upper, base, emphasize in table:
        if ratio <= upper:
            return f"{base}, about {pct:.0f}% {direction}", emphasize
    base, emphasize = table[-1][1], table[-1][2]
    return f"{base}, about {pct:.0f}% {direction}", emphasize


# 두 프롬프트가 공유하는 보존 지시문. §10.3(아우터 확대 프레이밍 버그)의 프레이밍 문구를
# "확대/재구성 금지"까지 명시하도록 강화하고, §10.5 "다음 단계"에 남아있던 "하의 색상
# 유지 문구"를 실제로 추가했다 — 둘 다 프롬프트만으로 강제하는 소프트 제약이라 100%
# 보장은 아니지만(실측 검증 필요), 모델이 지금 참조하는 유일한 신호이므로 명시할수록
# 지켜질 확률이 올라간다.
_PRESERVE_SUFFIX = (
    " Keep the exact same person, face, pose, camera distance, framing, and "
    "background as the reference photo -- do not zoom in, crop tighter, or "
    "recompose the shot in any way. Keep every other garment the person is "
    "already wearing (pants, shoes, etc.) exactly the same color, fabric, and "
    "fit as in the reference photo -- change only the garment described above."
)


def build_dress_prompt(garment_caption: str, fit_phrase: str, needs_emphasis: bool) -> str:
    """§10.3에서 검증한 "원본 사진 참조 편집" 프롬프트 형태. `image=[고객 사진]`과 함께
    쓰면 포즈/스케일/프레이밍은 참조 사진에서 그대로 상속되고 옷만 바뀐다."""
    if needs_emphasis:
        extremely = "skin-tight" if "small" in fit_phrase or "tight" in fit_phrase else "oversized and baggy"
        emphasis_lead = (
            f"IMPORTANT: the {garment_caption} must look extremely {extremely} -- "
            "NOT a fitted or regular cut. "
        )
    else:
        emphasis_lead = ""

    return (
        f"{emphasis_lead}dress the person in the reference photo in a "
        f"{garment_caption} that is {fit_phrase}.{_PRESERVE_SUFFIX}"
    )


def build_regular_dress_prompt(garment_caption: str) -> str:
    """신체 치수 근사가 불가능하거나(키/몸무게 없음) 상품 사이즈표가 없을 때 쓰는 폴백 —
    핏 계산 없이 "이 옷을 그대로 입혀라"만 지시한다."""
    return (
        f"dress the person in the reference photo in a {garment_caption}, worn in "
        f"a regular, well-fitting cut.{_PRESERVE_SUFFIX}"
    )
