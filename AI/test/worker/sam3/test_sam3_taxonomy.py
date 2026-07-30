"""SAM3 레지스트리의 하자 분류 체계 검증 — LAB-12/LAB-46 실측 결론이 코드에 남아 있는지 지킨다.

`worker/models/clipseg/registry.py`용 테스트(`test_clipseg_taxonomy.py`)와 같은 목적이다.
값 자체는 clipseg 레지스트리와 같아야 한다(정책은 모델이 아니라 하자 유형에 대한 것 —
`AI/test/quality/test_quality_contract.py`가 이 값이 갈라지지 않는지 별도로 대조한다).
"""

import pytest

from sam3 import registry
from sam3.contracts import DefectType

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
    evidence = registry.defect_policy(defect_type)["evidence"]
    assert evidence, f"{defect_type}: 취급 근거가 비어 있습니다"
    assert "LAB-12" in evidence or "LAB-46" in evidence or "미검증" in evidence


@pytest.mark.parametrize("defect_type", list(DefectType))
def test_untrusted_types_always_need_seller_review(defect_type):
    policy = registry.defect_policy(defect_type)
    if not policy["trusted"]:
        assert policy["needs_seller_review"] is True


def test_only_stain_family_is_trusted():
    trusted = {t for t, p in registry.DEFECT_TAXONOMY.items() if p["trusted"]}
    assert trusted == {DefectType.stain, DefectType.dirt_mark}


def test_hole_tear_is_untrusted_and_cites_the_sam3_specific_false_positive():
    """찢어짐은 LAB-46이 SAM3 기준으로 재검증해 구조적 개구부 오탐을 확인한 유형이다."""
    policy = registry.defect_policy(DefectType.hole_tear)
    assert policy["trusted"] is False
    assert policy["needs_seller_review"] is True
    assert "LAB-46" in policy["evidence"]


@pytest.mark.parametrize("defect_type", list(DefectType))
def test_every_defect_costs_something(defect_type):
    assert registry.defect_policy(defect_type)["weight"] > 0.0


def test_hole_tear_is_the_heaviest_defect():
    weights = {t: p["weight"] for t, p in registry.DEFECT_TAXONOMY.items()}
    assert weights[DefectType.hole_tear] == max(weights.values())


def test_stain_outweighs_a_dirty_mark():
    assert registry.defect_policy(DefectType.stain)["weight"] > (
        registry.defect_policy(DefectType.dirt_mark)["weight"]
    )


def test_pilling_is_the_only_defect_exempt_from_a_seller_statement():
    exempt = {t for t, p in registry.DEFECT_TAXONOMY.items() if not p["statement_required"]}
    assert exempt == {DefectType.pilling}


def test_taxonomy_policy_values_match_clipseg_registry():
    """정책은 모델이 아니라 하자 유형 자체에 대한 것 — 두 백엔드 레지스트리가 갈라지면 안 된다.

    `evidence`(백엔드별 검증 근거 서술)만 예외다 — SAM3 쪽은 LAB-46 실측을 별도로 인용하므로
    문구 자체가 다르다. 판정에 실제로 쓰이는 필드(trusted/needs_seller_review/
    statement_required/weight)만 값 일치를 지킨다.
    """
    import registry as clipseg_registry

    assert set(registry.DEFECT_TAXONOMY) == set(clipseg_registry.DEFECT_TAXONOMY)
    for defect_type, sam3_policy in registry.DEFECT_TAXONOMY.items():
        clipseg_policy = clipseg_registry.DEFECT_TAXONOMY[defect_type]
        for field in ("trusted", "needs_seller_review", "statement_required", "weight"):
            assert (
                sam3_policy[field] == clipseg_policy[field]
            ), f"{defect_type}.{field} 이 clipseg 레지스트리와 어긋납니다"
