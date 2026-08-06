"""`worker/models/catvton/model/fit_summary.py` 순수 계산 검증.

`test_adaptive_fit.py`와 같은 이유로 cv2/torch 의존성이 없어 mock/실 백엔드 구분 없이
항상 실제 구현을 그대로 테스트한다.
"""

from model.fit_summary import fit_summary_ko

# --- None 폴백 --------------------------------------------------------------


def test_returns_none_when_ratio_is_none():
    """측정값 없음(ratio=None)이면 문구 자체를 노출하지 않는다 — 부정확한 추측 대신 침묵."""
    assert fit_summary_ko(None, "waist") is None
    assert fit_summary_ko(None, "chest") is None


# --- 레귤러 구간(0.95~1.05) ---------------------------------------------------


def test_regular_fit_at_neutral_ratio():
    result = fit_summary_ko(1.0, "waist")
    assert result["title"] == "선택하신 사이즈가 적당해요."
    assert "허리" in result["description"]


def test_regular_fit_boundary_inclusive():
    # 경계값(0.95, 1.05)은 레귤러 쪽에 포함된다.
    assert fit_summary_ko(0.95, "waist")["title"] == "선택하신 사이즈가 적당해요."
    assert fit_summary_ko(1.05, "waist")["title"] == "선택하신 사이즈가 적당해요."


# --- 타이트 구간(ratio < 0.95) ------------------------------------------------


def test_slightly_tight_between_085_and_095():
    result = fit_summary_ko(0.90, "waist")
    assert result["title"] == "선택하신 사이즈가 살짝 타이트해요."
    assert "10%" in result["description"]


def test_definitely_tight_at_or_below_085():
    result = fit_summary_ko(0.727, "waist")  # 둘리 청바지 M 실측값
    assert result["title"] == "선택하신 사이즈가 타이트할 수 있어요."
    assert "27%" in result["description"]


# --- 루즈 구간(ratio > 1.05) --------------------------------------------------


def test_slightly_loose_between_105_and_115():
    result = fit_summary_ko(1.111, "waist")  # 마이콜 청바지 M 실측값
    assert result["title"] == "선택하신 사이즈가 살짝 여유있어요."
    assert "11%" in result["description"]


def test_loose_between_115_and_130():
    result = fit_summary_ko(1.217, "chest")  # 희동이 상의 M 실측값
    assert result["title"] == "선택하신 사이즈가 여유있게 맞아요."
    assert "22%" in result["description"]


def test_oversized_at_or_above_130():
    result = fit_summary_ko(1.380, "chest")  # 희동이 상의 XXL 실측값
    assert result["title"] == "선택하신 사이즈가 넉넉한 오버사이즈예요."
    assert "38%" in result["description"]


# --- part별 문구 분기 ---------------------------------------------------------


def test_waist_and_chest_use_different_area_labels():
    waist_result = fit_summary_ko(1.20, "waist")
    chest_result = fit_summary_ko(1.20, "chest")
    assert "허리" in waist_result["description"]
    assert "가슴과 어깨" in chest_result["description"]
    assert waist_result["description"] != chest_result["description"]
