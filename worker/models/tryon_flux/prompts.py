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
    "background as the first reference photo -- do not zoom in, crop tighter, or "
    "recompose the shot in any way. Keep every other garment the person is "
    "already wearing (pants, shoes, etc.) exactly the same color, fabric, and "
    "fit as in the first reference photo -- change only the garment described "
    "above."
)

# CH027: FLUX.2가 image=[사람 사진, 옷 사진] 두 장을 함께 참조하므로, 두 번째 이미지를
# "이 옷의 진짜 모습(색상/로고/트림)"으로 명시해야 캡션 텍스트만 믿고 다른 색/디자인을
# 상상해버리는 걸 막을 수 있다(실측: 이 문구 없이는 로고·트림 색이 자주 어긋났다).
def build_multi_reference_prefix(garment_caption: str) -> str:
    return (
        f"The first reference image shows a person; the second reference image "
        f"shows a {garment_caption} on its own -- use the second image for the "
        f"garment's exact color, logo placement, trim, and fabric texture, do not "
        f"invent a different design. "
    )


# CH027: 오버핏을 마스크 팽창(폭을 넓힘)이 아니라 프롬프트 문구로 표현하게 됨에 따라,
# "몸통이 부푼 것처럼 보이면 안 된다"를 명시하지 않으면 diffusion이 실루엣 자체를
# 부풀리는 쪽으로 과잉 해석하는 경향이 실측으로 확인됐다(person3 실제 착용사진과 대조).
_SLEEK_FIT_CLAUSE = (
    " The garment has a sleek, streamlined silhouette that hugs the body's "
    "natural shape closely -- not baggy, bulky, or voluminous. The impression "
    "that it is a bigger, roomier garment should come from soft wrinkles and "
    "folds gathered at the torso and sleeves, not from the torso looking wider."
)


def build_dress_prompt(garment_caption: str, fit_phrase: str, needs_emphasis: bool) -> str:
    """§10.3에서 검증한 "원본 사진 참조 편집" 프롬프트 형태. `image=[사람 사진, 옷 사진]`과
    함께 쓰면 포즈/스케일/프레이밍은 첫 번째 참조 사진에서, 옷의 실제 모습은 두 번째 참조
    사진에서 상속된다."""
    if needs_emphasis:
        extremely = "skin-tight" if "small" in fit_phrase or "tight" in fit_phrase else "oversized and baggy"
        emphasis_lead = (
            f"IMPORTANT: the {garment_caption} must look extremely {extremely} -- "
            "NOT a fitted or regular cut. "
        )
    else:
        emphasis_lead = ""

    return (
        f"{emphasis_lead}{build_multi_reference_prefix(garment_caption)}"
        f"Dress the person from the first image in a "
        f"{garment_caption} that is {fit_phrase}.{_SLEEK_FIT_CLAUSE}{_PRESERVE_SUFFIX}"
    )


def build_regular_dress_prompt(garment_caption: str) -> str:
    """신체 치수 근사가 불가능하거나(키/몸무게 없음) 상품 사이즈표가 없을 때 쓰는 폴백 —
    핏 계산 없이 "이 옷을 그대로 입혀라"만 지시한다."""
    return (
        f"{build_multi_reference_prefix(garment_caption)}"
        f"Dress the person from the first image in the garment shown in the second "
        f"image, worn in a regular, true-to-size, well-fitting cut.{_PRESERVE_SUFFIX}"
    )


# CH027: 오버핏/후드/소매 디테일은 옷마다 다르므로(모든 옷이 후드가 있는 건 아님), 필요할
# 때만 선택적으로 붙이는 헬퍼로 분리한다(기존 run_dress_prompt들과 조합해서 쓴다).
_REF_SLEEVE_RATIO = 0.33  # 어깨~손목, 키 대비 경험적 비율(자료 없어 직접 근사)
_REF_LENGTH_RATIO = 0.38  # 상의/아우터 기본 기장, 키 대비 경험적 비율(직접 근사)


def sleeve_and_length_clause(sleeve_cm: float | None, length_cm: float | None, height_cm: float) -> str:
    """실측 소매길이/총장이 있으면 "손을 덮을 만큼 길다" 같은 구체적 문구를 만든다.
    길이(기장) 축은 `adaptive_fit.py`가 마스크 크롭에는 의도적으로 안 쓰지만(맨살 노출
    가드레일), 여기서는 마스크가 아니라 FLUX 텍스트 프롬프트만 바꾸는 것이라 그 제약과
    무관하다."""
    clauses = []
    if sleeve_cm is not None:
        ratio = sleeve_cm / (_REF_SLEEVE_RATIO * height_cm)
        if ratio >= 1.25:
            clauses.append(
                "the sleeves are extremely long, extending well past the wrists "
                "and fully covering the hands"
            )
        elif ratio >= 1.1:
            clauses.append("the sleeves are noticeably long, reaching past the wrists")
    if length_cm is not None:
        ratio = length_cm / (_REF_LENGTH_RATIO * height_cm)
        if ratio >= 1.15:
            clauses.append("the hem falls long, well past the hips")
        elif ratio >= 1.05:
            clauses.append("the hem falls slightly longer than a regular cut")
    return (" " + " and ".join(clauses) + ".") if clauses else ""


HOOD_CLAUSE = (
    " The hood is folded down naturally behind the neck -- the front view shows a "
    "relaxed, normal neckline with only soft folded fabric visible at the back of "
    "the neck/shoulders indicating the folded-down hood, not draped over the front "
    "of the neck or distorting the collar. Any drawstrings hang straight down "
    "naturally, pulled by gravity, not floating or stiff."
)
