"""하자 분류 체계 검증 — LAB-12 실측 결론이 코드에 남아 있는지 지킨다.

이 파일의 요점은 **모델이 못 하는 걸 잘하는 척하지 않는 상태를 고정**하는 것이다. 프롬프트를
추가하다 보면 검증하지 않은 유형을 `trusted=True`로 열어버리기 쉽고, 그러면 신뢰도 없는 판정이
`DETECTED`로 판매자·구매자에게 그대로 노출된다.
"""

import pytest

import registry
from contracts import DefectType

_POLICY_FIELDS = ("trusted", "needs_seller_review", "statement_required", "weight", "evidence")


def test_taxonomy_covers_every_defect_type():
    assert set(registry.DEFECT_TAXONOMY) == set(DefectType)


@pytest.mark.parametrize("defect_type", list(DefectType))
def test_every_policy_declares_all_fields(defect_type):
    policy = registry.defect_policy(defect_type)
    for field in _POLICY_FIELDS:
        assert field in policy, f"{defect_type}: {field} 정책이 없습니다"


@pytest.mark.parametrize("defect_type", list(DefectType))
def test_every_policy_records_why_it_is_trusted_or_not(defect_type):
    # 근거 없이 신뢰 여부를 바꾸는 걸 막는다 — 나중에 이 문자열이 검증 기록의 유일한 흔적이다.
    evidence = registry.defect_policy(defect_type)["evidence"]
    assert evidence, f"{defect_type}: 취급 근거가 비어 있습니다"
    assert "LAB-12" in evidence or "미검증" in evidence


@pytest.mark.parametrize("defect_type", list(DefectType))
def test_untrusted_types_always_need_seller_review(defect_type):
    # LAB-12에서 약점이 확인됐거나 미검증인 유형은 판매자 확인 없이 노출하면 안 된다.
    policy = registry.defect_policy(defect_type)
    if not policy["trusted"]:
        assert policy["needs_seller_review"] is True


def test_only_stain_family_is_trusted():
    # LAB-12 실측에서 양호했던 건 오염 계열뿐이다. 여기가 늘어나면 실측 근거가 필요하다.
    trusted = {t for t, p in registry.DEFECT_TAXONOMY.items() if p["trusted"]}
    assert trusted == {DefectType.stain, DefectType.dirt_mark}


def test_hole_tear_is_untrusted_despite_being_a_verified_prompt():
    """찢어짐은 LAB-12가 실제로 테스트했지만 '잘 판단하지 못함'으로 결론난 유형이다."""
    policy = registry.defect_policy(DefectType.hole_tear)
    assert policy["trusted"] is False
    assert policy["needs_seller_review"] is True
    assert "약함" in policy["evidence"]


@pytest.mark.parametrize("defect_type", list(DefectType))
def test_every_defect_costs_something(defect_type):
    assert registry.defect_policy(defect_type)["weight"] > 0.0


def test_hole_tear_is_the_heaviest_defect():
    weights = {t: p["weight"] for t, p in registry.DEFECT_TAXONOMY.items()}
    assert weights[DefectType.hole_tear] == max(weights.values())


def test_stain_outweighs_a_dirty_mark():
    # 오염(고착)이 단순 얼룩보다 상태에 더 영향을 준다는 순서만 담고 있다.
    assert registry.defect_policy(DefectType.stain)["weight"] > (
        registry.defect_policy(DefectType.dirt_mark)["weight"]
    )


def test_pilling_is_the_only_defect_exempt_from_a_seller_statement():
    exempt = {t for t, p in registry.DEFECT_TAXONOMY.items() if not p["statement_required"]}
    assert exempt == {DefectType.pilling}
