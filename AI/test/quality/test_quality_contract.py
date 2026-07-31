"""게이트웨이 스키마 ↔ 워커 계약 사본의 일치 검증.

품질 검수 판정은 워커(`worker/models/sam3/`)가 하고, 그 결과 JSON을 BE가 받는다. 워커는
게이트웨이와 배포 단위가 달라(팀원 노트북에서 git clone으로 실행) `app/` 코드를 import할 수
없어서, 계약을 `worker/models/sam3/contracts.py`에 **복제**해 두었다.

**복제본은 조용히 어긋난다.** 한쪽에서 enum 값을 바꾸거나 필드를 추가하면 BE가 받는 JSON이
말없이 달라지고, 그걸 알아채는 건 통합 시점이다. 이 파일이 그걸 막는 유일한 장치다.

여기서 실패하면 **양쪽을 함께 고쳐야 한다** — 어느 쪽이 맞는지는 BE 계약 문서
(`.claude/requests/be/001-quality-inspection-async.md`)를 기준으로 판단한다.
"""

import ast
from pathlib import Path

import pytest
from sam3 import contracts

from app.quality import schemas

# (게이트웨이 스키마, 워커 사본) enum 쌍. 이름이 같아도 자동으로 짝지어지지 않게 명시한다.
_ENUM_PAIRS = [
    (schemas.GarmentCategory, contracts.GarmentCategory),
    (schemas.BaseColor, contracts.BaseColor),
    (schemas.DefectType, contracts.DefectType),
    (schemas.FindingStatus, contracts.FindingStatus),
    (schemas.Severity, contracts.Severity),
    (schemas.ConditionGrade, contracts.ConditionGrade),
    (schemas.GarmentSection, contracts.GarmentSection),
]

# (게이트웨이 pydantic 모델, 워커 dataclass) 쌍.
_MODEL_PAIRS = [
    (schemas.Finding, contracts.Finding),
    (schemas.SectionScore, contracts.SectionScore),
    (schemas.AttentionMap, contracts.AttentionMap),
    (schemas.AnnotatedImage, contracts.AnnotatedImage),
]


@pytest.mark.parametrize(("gateway_enum", "worker_enum"), _ENUM_PAIRS, ids=lambda e: e.__name__)
def test_enum_values_match(gateway_enum, worker_enum):
    """enum **값**(BE가 문자열로 비교하는 그 값)이 양쪽에서 같아야 한다."""
    assert {m.value for m in gateway_enum} == {m.value for m in worker_enum}


@pytest.mark.parametrize(("gateway_model", "worker_model"), _MODEL_PAIRS, ids=lambda m: m.__name__)
def test_model_field_names_match(gateway_model, worker_model):
    """필드 이름 집합이 같아야 한다 — 워커가 만든 dict가 곧 BE가 받는 JSON이다."""
    gateway_fields = set(gateway_model.model_fields)
    worker_fields = set(worker_model.__dataclass_fields__)
    assert gateway_fields == worker_fields


def test_worker_dataclasses_serialize_to_plain_json_types():
    """`to_dict()`가 enum·튜플을 남기지 않아야 한다 — 그대로 job result에 실린다."""
    finding = contracts.Finding(
        key="stain_0_5_1",
        defect_type=contracts.DefectType.stain,
        status=contracts.FindingStatus.detected,
        image_index=0,
        section_no=5,
        section=contracts.GarmentSection.chest_center,
        confidence=0.81,
        area_ratio=0.031,
        bbox=(0.42, 0.35, 0.55, 0.47),
        severity=contracts.Severity.moderate,
        matched_prompt="a stain on fabric",
        statement_required=True,
        needs_seller_review=False,
        no=1,
        label="오염",
    )
    dumped = finding.to_dict()

    assert dumped["defect_type"] == "STAIN"
    assert dumped["status"] == "DETECTED"
    assert dumped["severity"] == "MODERATE"
    assert dumped["section"] == "CHEST_CENTER"
    assert dumped["bbox"] == [0.42, 0.35, 0.55, 0.47]  # 튜플이 아니라 리스트
    assert dumped["no"] == 1
    assert dumped["label"] == "오염"
    assert dumped["description"] is None  # sVLM 미연동 상태의 기본값
    assert all(not isinstance(v, tuple) for v in dumped.values())


def test_worker_output_validates_against_gateway_schema():
    """워커가 만든 dict가 게이트웨이 pydantic 모델을 그대로 통과해야 한다.

    필드 이름만 같고 값 형태가 다르면(예: enum 대신 인덱스) 여기서 걸린다.
    """
    section = contracts.SectionScore(
        section_no=5, section=contracts.GarmentSection.chest_center, score=0.81
    )
    attention = contracts.AttentionMap(
        image_index=0, defect_type=contracts.DefectType.stain, url="https://x/y.png"
    )
    annotated = contracts.AnnotatedImage(image_index=0, url="https://x/annotated.png")
    finding = contracts.Finding(
        key="stain_0_5_1",
        defect_type=contracts.DefectType.stain,
        status=contracts.FindingStatus.detected,
        image_index=0,
        section_no=5,
        section=contracts.GarmentSection.chest_center,
        confidence=0.81,
        area_ratio=0.031,
        bbox=(0.42, 0.35, 0.55, 0.47),
        severity=contracts.Severity.moderate,
        matched_prompt="a stain on fabric",
        statement_required=True,
        needs_seller_review=False,
        no=1,
        label="오염",
    )

    assert schemas.SectionScore(**section.to_dict()).section is schemas.GarmentSection.chest_center
    assert schemas.AttentionMap(**attention.to_dict()).defect_type is schemas.DefectType.stain
    assert schemas.AnnotatedImage(**annotated.to_dict()).image_index == 0
    gateway_finding = schemas.Finding(**finding.to_dict())
    assert gateway_finding.no == 1
    assert gateway_finding.label == "오염"


def test_worker_contract_imports_stay_lightweight():
    """워커 의존성을 가볍게 유지하려는 결정 — 계약 사본이 pydantic 등을 끌어오면 안 된다.

    문자열 검색이 아니라 AST로 **실제 import 문**만 본다(docstring에 라이브러리 이름이 나오는
    건 정상이다).
    """
    source_path = contracts.__file__
    assert source_path, "contracts 모듈 경로를 찾을 수 없습니다"

    tree = ast.parse(Path(source_path).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])

    # 표준 라이브러리만 쓴다. numpy/Pillow조차 필요 없는 순수 계약 파일이다.
    assert imported <= {"dataclasses", "enum", "__future__"}, f"예상 밖 의존성: {imported}"
