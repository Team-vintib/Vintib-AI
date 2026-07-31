"""게이트웨이 스키마 ↔ 워커 계약 사본의 일치 검증.

품질 검수 판정은 워커가 하고, 그 결과 JSON을 BE가 받는다. 워커는 게이트웨이와 배포 단위가
달라(팀원 노트북에서 git clone으로 실행) `app/` 코드를 import할 수 없어서, 계약을
`worker/models/{clipseg,sam3}/contracts.py`에 **각자 복제**해 두었다(CH006 — 방식 B, 두
백엔드는 완전히 분리된 패키지다).

**복제본은 조용히 어긋난다.** 한쪽에서 enum 값을 바꾸거나 필드를 추가하면 BE가 받는 JSON이
말없이 달라지고, 그걸 알아채는 건 통합 시점이다. 이 파일이 그걸 막는 유일한 장치다 — clipseg/
sam3 두 사본 모두 게이트웨이 스키마와 대조한다.

여기서 실패하면 **모든 관련 사본을 함께 고쳐야 한다** — 어느 쪽이 맞는지는 BE 계약 문서
(`.claude/requests/be/001-quality-inspection-async.md`)를 기준으로 판단한다.
"""

import ast
from pathlib import Path

import contracts
import pytest
from sam3 import contracts as sam3_contracts

from app.quality import schemas

# 워커 계약 사본들 — 이름표를 붙여 실패 메시지에서 어느 백엔드가 어긋났는지 바로 알 수 있게 한다.
_WORKER_CONTRACTS = {"clipseg": contracts, "sam3": sam3_contracts}

# (게이트웨이 스키마 필드명, 워커 계약 모듈의 동명 속성) enum 쌍. 이름이 같아도 자동으로
# 짝지어지지 않게 명시한다.
_ENUM_NAMES = (
    "GarmentCategory",
    "BaseColor",
    "DefectType",
    "FindingStatus",
    "Severity",
    "ConditionGrade",
    "GarmentSection",
)

# 게이트웨이 pydantic 모델 이름 ↔ 워커 dataclass 동명 속성.
_MODEL_NAMES = ("Finding", "SectionScore", "AttentionMap", "AnnotatedImage")

_ENUM_CASES = [
    (worker_label, enum_name) for worker_label in _WORKER_CONTRACTS for enum_name in _ENUM_NAMES
]
_MODEL_CASES = [
    (worker_label, model_name) for worker_label in _WORKER_CONTRACTS for model_name in _MODEL_NAMES
]


@pytest.mark.parametrize(
    ("worker_label", "enum_name"), _ENUM_CASES, ids=[f"{w}-{n}" for w, n in _ENUM_CASES]
)
def test_enum_values_match(worker_label, enum_name):
    """enum **값**(BE가 문자열로 비교하는 그 값)이 게이트웨이·워커 양쪽에서 같아야 한다."""
    gateway_enum = getattr(schemas, enum_name)
    worker_enum = getattr(_WORKER_CONTRACTS[worker_label], enum_name)
    assert {m.value for m in gateway_enum} == {m.value for m in worker_enum}


@pytest.mark.parametrize(
    ("worker_label", "model_name"), _MODEL_CASES, ids=[f"{w}-{n}" for w, n in _MODEL_CASES]
)
def test_model_field_names_match(worker_label, model_name):
    """필드 이름 집합이 같아야 한다 — 워커가 만든 dict가 곧 BE가 받는 JSON이다."""
    gateway_model = getattr(schemas, model_name)
    worker_model = getattr(_WORKER_CONTRACTS[worker_label], model_name)
    gateway_fields = set(gateway_model.model_fields)
    worker_fields = set(worker_model.__dataclass_fields__)
    assert gateway_fields == worker_fields


@pytest.mark.parametrize("worker_label", _WORKER_CONTRACTS, ids=list(_WORKER_CONTRACTS))
def test_worker_dataclasses_serialize_to_plain_json_types(worker_label):
    """`to_dict()`가 enum·튜플을 남기지 않아야 한다 — 그대로 job result에 실린다."""
    worker = _WORKER_CONTRACTS[worker_label]
    finding = worker.Finding(
        key="stain_0_5_1",
        defect_type=worker.DefectType.stain,
        status=worker.FindingStatus.detected,
        image_index=0,
        section_no=5,
        section=worker.GarmentSection.chest_center,
        confidence=0.81,
        area_ratio=0.031,
        bbox=(0.42, 0.35, 0.55, 0.47),
        severity=worker.Severity.moderate,
        matched_prompt="a stain on fabric",
        statement_required=True,
        needs_seller_review=False,
    )
    dumped = finding.to_dict()

    assert dumped["defect_type"] == "STAIN"
    assert dumped["status"] == "DETECTED"
    assert dumped["severity"] == "MODERATE"
    assert dumped["section"] == "CHEST_CENTER"
    assert dumped["bbox"] == [0.42, 0.35, 0.55, 0.47]  # 튜플이 아니라 리스트
    assert all(not isinstance(v, tuple) for v in dumped.values())
    # CH007 필드 — 안 채운 백엔드는 None이어도 스키마를 통과해야 한다(둘 다 optional).
    assert dumped["no"] is None
    assert dumped["label"] is None
    assert dumped["description"] is None


@pytest.mark.parametrize("worker_label", _WORKER_CONTRACTS, ids=list(_WORKER_CONTRACTS))
def test_worker_output_validates_against_gateway_schema(worker_label):
    """워커가 만든 dict가 게이트웨이 pydantic 모델을 그대로 통과해야 한다.

    필드 이름만 같고 값 형태가 다르면(예: enum 대신 인덱스) 여기서 걸린다.
    """
    worker = _WORKER_CONTRACTS[worker_label]
    section = worker.SectionScore(
        section_no=5, section=worker.GarmentSection.chest_center, score=0.81
    )
    attention = worker.AttentionMap(
        image_index=0, defect_type=worker.DefectType.stain, url="https://x/y.png"
    )
    annotated = worker.AnnotatedImage(image_index=0, url="https://x/annotated.png")
    finding = worker.Finding(
        key="stain_0_5_1",
        defect_type=worker.DefectType.stain,
        status=worker.FindingStatus.detected,
        image_index=0,
        section_no=5,
        section=worker.GarmentSection.chest_center,
        confidence=0.81,
        area_ratio=0.031,
        bbox=(0.42, 0.35, 0.55, 0.47),
        severity=worker.Severity.moderate,
        matched_prompt="a stain on fabric",
        statement_required=True,
        needs_seller_review=False,
        no=1,
        label="오염",
        description=None,
    )

    assert schemas.SectionScore(**section.to_dict()).section is schemas.GarmentSection.chest_center
    assert schemas.AttentionMap(**attention.to_dict()).defect_type is schemas.DefectType.stain
    assert schemas.AnnotatedImage(**annotated.to_dict()).image_index == 0
    gateway_finding = schemas.Finding(**finding.to_dict())
    assert gateway_finding.no == 1
    assert gateway_finding.label == "오염"


@pytest.mark.parametrize("worker_label", _WORKER_CONTRACTS, ids=list(_WORKER_CONTRACTS))
def test_worker_contract_imports_stay_lightweight(worker_label):
    """워커 의존성을 가볍게 유지하려는 결정 — 계약 사본이 pydantic 등을 끌어오면 안 된다.

    문자열 검색이 아니라 AST로 **실제 import 문**만 본다(docstring에 라이브러리 이름이 나오는
    건 정상이다).
    """
    source_path = _WORKER_CONTRACTS[worker_label].__file__
    assert source_path, f"{worker_label}: contracts 모듈 경로를 찾을 수 없습니다"

    tree = ast.parse(Path(source_path).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])

    # 표준 라이브러리만 쓴다. numpy/Pillow조차 필요 없는 순수 계약 파일이다.
    assert imported <= {
        "dataclasses",
        "enum",
        "__future__",
    }, f"{worker_label}: 예상 밖 의존성: {imported}"
