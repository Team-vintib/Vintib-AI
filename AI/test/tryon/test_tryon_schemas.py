"""`TryOnOptions`의 적응형 마스킹 입력 필드(전부 선택) 계약 검증.

라우터/서비스가 아직 없는 도메인이라(`app/tryon/schemas.py` 참고) 여기서는 스키마 계약만
본다 — 온보딩을 건너뛴 회원·실측 안 된 상품처럼 값이 없는 게 정상인 케이스가 기본값만으로
문제없이 구성되는지가 핵심이다.
"""

from app.tryon.schemas import TryOnOptions


def test_defaults_have_no_adaptive_masking_inputs():
    """body/garment 측정값을 안 넘기면 전부 None이어야 한다 — 적응형 마스킹이 꺼진 상태."""
    options = TryOnOptions()

    assert options.body_height_cm is None
    assert options.body_weight_kg is None
    assert options.body_chest_cm is None
    assert options.body_waist_cm is None
    assert options.body_hip_cm is None
    assert options.garment_measurements is None


def test_accepts_confirmed_body_fields_and_garment_measurements():
    """지금 BE에 실제 확정된 건 height/weight뿐이지만, 스키마는 나머지도 받을 수 있어야
    나중에 BE가 컬럼을 추가했을 때 AI 쪽 스키마 변경 없이 바로 흘려보낼 수 있다."""
    options = TryOnOptions(
        body_height_cm=172.0,
        body_weight_kg=65.0,
        garment_measurements={"TOTAL_LENGTH": 68.0, "WAIST_WIDTH": 42.0},
    )

    assert options.body_height_cm == 172.0
    assert options.garment_measurements == {"TOTAL_LENGTH": 68.0, "WAIST_WIDTH": 42.0}
    assert options.body_chest_cm is None  # 아직 BE가 못 보내는 값
