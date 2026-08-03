"""게이트웨이 스키마 ↔ 워커 계약 사본의 일치 검증.

분류 처리는 워커(`worker/models/product_classifier/`)가 하고, 그 결과 JSON을 BE가 받는다.
워커는 게이트웨이와 배포 단위가 달라(팀원 노트북에서 git clone으로 실행) `app/` 코드를
import할 수 없어서, 계약을 `worker/models/product_classifier/contracts.py`에 **복제**해
두었다(`test_measurement_contract.py`와 같은 이유·같은 기법).

**복제본은 조용히 어긋난다.** 한쪽에서 필드를 추가하거나 이름을 바꾸면 BE가 받는 JSON이
말없이 달라지고, 그걸 알아채는 건 통합 시점이다. 이 파일이 그걸 막는 유일한 장치다.
"""

import ast
from pathlib import Path

import pytest
from product_classifier import contracts

from app.product_classifier import schemas

# (게이트웨이 pydantic 모델, to_dict() 샘플을 만드는 팩토리) 쌍. `garment_measurement/
# contracts.py`의 dataclass 필드명은 게이트웨이 스키마와 1:1이라 `__dataclass_fields__`를
# 바로 비교할 수 있지만, 여기 dataclass(`CategoryPrediction`/`ColorFieldPrediction`)는
# `subcategory`/`major`/`path` -> `value`/`path`처럼 **`to_dict()`가 이름을 바꾼다** — 그래서
# 실제 BE로 나가는 경계인 `to_dict()` 출력 키를 비교 대상으로 삼는다.
_MODEL_PAIRS = [
    pytest.param(
        schemas.CategoryField,
        lambda: contracts.build_category_prediction(
            subcategory=contracts.Subcategory.cardigan,
            score=0.5,
            action="none",
            candidates=[],
        ).to_dict(),
        id="CategoryField",
    ),
    pytest.param(
        schemas.ColorField,
        lambda: contracts.ColorFieldPrediction(
            code="NAVY", hex="#22304A", score=0.5, action="none", candidates=[]
        ).to_dict(),
        id="ColorField",
    ),
]


@pytest.mark.parametrize(("gateway_model", "to_dict_factory"), _MODEL_PAIRS)
def test_model_field_names_match(gateway_model, to_dict_factory):
    """필드 이름 집합이 같아야 한다 — `to_dict()`가 만든 dict가 곧 BE가 받는 JSON이다."""
    gateway_fields = set(gateway_model.model_fields)
    worker_fields = set(to_dict_factory())
    assert gateway_fields == worker_fields


def test_category_prediction_serializes_to_plain_json_types():
    """`to_dict()`가 enum을 남기지 않아야 한다 — 그대로 job result에 실린다."""
    prediction = contracts.build_category_prediction(
        subcategory=contracts.Subcategory.cardigan,
        score=0.83,
        action="autofill",
        candidates=[
            contracts.CategoryCandidate(subcategory=contracts.Subcategory.cardigan, score=0.83)
        ],
    )
    dumped = prediction.to_dict()

    assert dumped["value"] == "CARDIGAN"
    assert dumped["path"] == ["아우터", "가디건"]
    assert all(not isinstance(v, contracts.Subcategory) for v in dumped.values())


def test_worker_category_output_validates_against_gateway_schema():
    """워커가 만든 dict가 게이트웨이 pydantic 모델을 그대로 통과해야 한다."""
    prediction = contracts.build_category_prediction(
        subcategory=contracts.Subcategory.denim,
        score=0.9,
        action="autofill",
        candidates=[
            contracts.CategoryCandidate(subcategory=contracts.Subcategory.denim, score=0.9)
        ],
    )

    validated = schemas.CategoryField(**prediction.to_dict())
    assert validated.value == "DENIM"
    assert validated.action == schemas.Action.autofill


def test_worker_color_output_validates_against_gateway_schema():
    color = contracts.ColorFieldPrediction(
        code="NAVY",
        hex="#22304A",
        score=0.6,
        action="suggest",
        candidates=[contracts.ColorCandidate(code="NAVY", score=0.6)],
    )

    validated = schemas.ColorField(**color.to_dict())
    assert validated.value == "NAVY"
    assert validated.action == schemas.Action.suggest


def test_worker_contract_imports_stay_lightweight():
    """워커 의존성을 가볍게 유지하려는 결정 — 계약 사본이 pydantic 등을 끌어오면 안 된다.

    문자열 검색이 아니라 AST로 **실제 import 문**만 본다(docstring에 라이브러리 이름이
    나오는 건 정상이다).
    """
    source_path = contracts.__file__
    assert source_path, "contracts 모듈 경로를 찾을 수 없습니다"

    tree = ast.parse(Path(source_path).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.level > 0:  # 상대 import(.taxonomy)는 같은 패키지 안이라 대상 아님
                continue
            imported.add(node.module.split(".")[0])

    # 표준 라이브러리만 쓴다.
    assert imported <= {"dataclasses", "typing", "__future__"}, f"예상 밖 의존성: {imported}"
