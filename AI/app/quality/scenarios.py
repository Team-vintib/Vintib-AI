"""목업 검수 시나리오 로더 (프로토타입의 데이터 입력부).

`MockSegmenter`가 이 정의를 읽어 **실제 확률 마스크를 합성**한다 — 하드코딩된 응답이 아니라서
findings/scoring/overlay 전 경로가 목업에서도 그대로 실행되고, 실모델로 갈아끼웠을 때
downstream이 이미 검증된 상태가 된다. 실데이터 전환 시 바뀌는 건 세그멘터뿐이고 이 모듈은
목업 백엔드 전용으로 남는다.

**시나리오 선택 키는 `product_id`다.** 요청 스키마에 목업 전용 필드를 넣지 않기 위한 선택이며,
등록되지 않은 `product_id`는 시드 기반 폴백 시나리오로 결정적으로 합성된다(데모에서 아무 상품
id를 넣어도 동작한다). 결정성 방식은 `app/recommend/personalize/catalog.py`의
`_seeded_vector()`와 같다: sha256 → `np.random.default_rng`.

blob 필드 의미:

- `center` / `radius` — 정규화 좌표. 가우시안은 `exp(-2 * (d / radius) ** 2)`로, 거리 `radius`
  지점에서 약 0.135까지 떨어진다.
- `peak` — blob 중심에서 해당 하자 프롬프트의 확률.
- `clean_overlap` — **같은 자리에서 `clean` 프롬프트가 갖는 확률.** 진짜 오염은 낮고(정상 천이
  아니므로), 프린트·솔기 같은 정상 복잡 영역은 높다. 대조 정규화
  `p_defect - clean_margin * p_clean`이 후자만 상쇄하는 근거가 이 값이다.
- `cross_talk` — 이 blob이 **다른 하자 프롬프트에도 번지는 비율**(`peak` 대비). 실제 CLIPSeg는
  하나의 오염에 "a stain" / "a dirty mark"가 함께 반응하므로, 프롬프트 간 blob 병합 로직을
  목업에서도 태우기 위해 둔다.

설계: .claude/plans/ai/005-quality-inspection-prototype.md
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np

from app.quality.schemas import (
    BaseColor,
    ConditionGrade,
    DefectType,
    FindingStatus,
    GarmentCategory,
    GarmentSection,
)

_DATA_DIR = Path(__file__).resolve().parent / "data"
_MOCK_INSPECTIONS_FILE = _DATA_DIR / "mock_inspections.json"

# 폴백(미등록 product_id) 시나리오 합성 파라미터.
_FALLBACK_MAX_BLOBS = 2
_FALLBACK_DEFECT_TYPES = (DefectType.stain, DefectType.dirt_mark, DefectType.hole_tear)
_FALLBACK_BACKGROUND_DEFECT = 0.06
_FALLBACK_BACKGROUND_CLEAN = 0.55


class ScenarioNotReady(Exception):
    """목업 시나리오 정의를 읽지 못함(파일 손상·필드 누락·범위 위반)."""


@dataclass(frozen=True)
class MockBlob:
    """합성할 하자 영역 1개."""

    image_index: int
    defect_type: DefectType
    center: tuple[float, float]
    radius: float
    peak: float
    clean_overlap: float
    cross_talk: float


@dataclass(frozen=True)
class MockExpectation:
    """시나리오의 기대 결과. E2E 테스트가 이 값을 검증한다.

    점수 가중치·등급 경계가 근거 없는 임의값이라 **등급은 findings 0건 케이스만 고정**하고
    나머지는 개수/유형/상태로 느슨하게 고정한다 — 가중치를 튜닝해도 테스트가 깨지지 않게.
    """

    finding_count_min: int
    finding_count_max: int
    must_include: tuple[tuple[DefectType, FindingStatus], ...]
    must_not_include: tuple[DefectType, ...]
    sections: tuple[GarmentSection, ...]
    any_needs_seller_review: bool
    grade: ConditionGrade | None


@dataclass(frozen=True)
class MockScenario:
    """목업 검수 시나리오 1건."""

    scenario: str
    note: str
    product_id: int
    category: GarmentCategory
    base_color: BaseColor
    image_count: int
    background_defect: float  # 하자 프롬프트의 배경 확률(blob 밖)
    background_clean: float  # clean 프롬프트의 배경 확률(blob 밖)
    blobs: tuple[MockBlob, ...]
    expected: MockExpectation | None  # 폴백 시나리오는 기대치가 없다

    def blobs_for(self, image_index: int) -> tuple[MockBlob, ...]:
        """해당 이미지에 속한 blob만 돌려준다(요청 이미지 수가 더 적으면 남는 blob은 무시)."""
        return tuple(blob for blob in self.blobs if blob.image_index == image_index)


@dataclass(frozen=True)
class ScenarioLibrary:
    """로드된 시나리오 묶음 + `product_id` 인덱스."""

    scenarios: tuple[MockScenario, ...]
    _by_product_id: dict[int, MockScenario]

    def by_name(self, scenario: str) -> MockScenario:
        for candidate in self.scenarios:
            if candidate.scenario == scenario:
                return candidate
        raise ScenarioNotReady(f"등록되지 않은 시나리오입니다: {scenario!r}")

    def registered_product_ids(self) -> tuple[int, ...]:
        return tuple(sorted(self._by_product_id))

    def for_product(
        self,
        product_id: int,
        category: GarmentCategory,
        base_color: BaseColor,
    ) -> MockScenario:
        """`product_id`로 시나리오를 찾고, 없으면 결정적 폴백을 합성한다.

        찾은 시나리오의 `category`/`base_color`는 **기대치 문서화용**이다. 프롬프트 세트와 부위
        라벨은 요청 값을 따르므로(서비스 책임), 여기서 요청 값으로 덮지 않는다.
        """
        found = self._by_product_id.get(product_id)
        if found is not None:
            return found
        return _fallback_scenario(product_id, category, base_color)


# --- 파싱 ------------------------------------------------------------------


def _require(row: dict, field: str, where: str):
    try:
        return row[field]
    except KeyError as exc:
        raise ScenarioNotReady(f"{where}: 필수 필드가 없습니다: {field!r}") from exc


def _unit(value, field: str, where: str) -> float:
    """[0, 1] 범위 실수로 변환한다. 확률·정규화 좌표는 전부 이 범위여야 한다."""
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ScenarioNotReady(f"{where}: {field!r}가 숫자가 아닙니다: {value!r}") from exc
    if not 0.0 <= number <= 1.0:
        raise ScenarioNotReady(f"{where}: {field!r}가 [0,1] 범위를 벗어났습니다: {number}")
    return number


def _enum(enum_cls, value, field: str, where: str):
    try:
        return enum_cls(value)
    except ValueError as exc:
        raise ScenarioNotReady(f"{where}: {field!r} 값이 유효하지 않습니다: {value!r}") from exc


def _parse_blob(row: dict, where: str, image_count: int) -> MockBlob:
    center = _require(row, "center", where)
    if not isinstance(center, list) or len(center) != 2:
        raise ScenarioNotReady(f"{where}: 'center'는 [x, y] 두 값이어야 합니다: {center!r}")

    image_index = int(_require(row, "image_index", where))
    if not 0 <= image_index < image_count:
        raise ScenarioNotReady(
            f"{where}: 'image_index'({image_index})가 image_count({image_count}) 범위를 벗어났습니다"
        )

    radius = _unit(_require(row, "radius", where), "radius", where)
    if radius <= 0.0:
        raise ScenarioNotReady(f"{where}: 'radius'는 0보다 커야 합니다: {radius}")

    return MockBlob(
        image_index=image_index,
        defect_type=_enum(DefectType, _require(row, "defect_type", where), "defect_type", where),
        center=(
            _unit(center[0], "center[0]", where),
            _unit(center[1], "center[1]", where),
        ),
        radius=radius,
        peak=_unit(_require(row, "peak", where), "peak", where),
        clean_overlap=_unit(_require(row, "clean_overlap", where), "clean_overlap", where),
        cross_talk=_unit(row.get("cross_talk", 0.0), "cross_talk", where),
    )


def _parse_expectation(row: dict | None, where: str) -> MockExpectation | None:
    if row is None:
        return None

    count_min = int(_require(row, "finding_count_min", where))
    count_max = int(_require(row, "finding_count_max", where))
    if not 0 <= count_min <= count_max:
        raise ScenarioNotReady(
            f"{where}: finding_count_min({count_min}) <= finding_count_max({count_max}) 여야 합니다"
        )

    must_include = tuple(
        (
            _enum(DefectType, _require(item, "defect_type", where), "defect_type", where),
            _enum(FindingStatus, _require(item, "status", where), "status", where),
        )
        for item in row.get("must_include", [])
    )
    if must_include and count_max < len(set(t for t, _ in must_include)):
        raise ScenarioNotReady(
            f"{where}: must_include 항목 수가 finding_count_max({count_max})보다 많습니다"
        )

    grade_value = row.get("grade")
    return MockExpectation(
        finding_count_min=count_min,
        finding_count_max=count_max,
        must_include=must_include,
        must_not_include=tuple(
            _enum(DefectType, value, "must_not_include", where)
            for value in row.get("must_not_include", [])
        ),
        sections=tuple(
            _enum(GarmentSection, value, "sections", where) for value in row.get("sections", [])
        ),
        any_needs_seller_review=bool(row.get("any_needs_seller_review", False)),
        grade=(None if grade_value is None else _enum(ConditionGrade, grade_value, "grade", where)),
    )


def _parse_scenario(row: dict, index: int) -> MockScenario:
    name = row.get("scenario", f"#{index}")
    where = f"시나리오 {name!r}"

    image_count = int(_require(row, "image_count", where))
    if image_count < 1:
        raise ScenarioNotReady(f"{where}: 'image_count'는 1 이상이어야 합니다: {image_count}")

    return MockScenario(
        scenario=str(_require(row, "scenario", where)),
        note=str(row.get("note", "")),
        product_id=int(_require(row, "product_id", where)),
        category=_enum(GarmentCategory, _require(row, "category", where), "category", where),
        base_color=_enum(BaseColor, _require(row, "base_color", where), "base_color", where),
        image_count=image_count,
        background_defect=_unit(
            _require(row, "background_defect", where), "background_defect", where
        ),
        background_clean=_unit(_require(row, "background_clean", where), "background_clean", where),
        blobs=tuple(
            _parse_blob(blob, f"{where} blob #{i}", image_count)
            for i, blob in enumerate(_require(row, "blobs", where))
        ),
        expected=_parse_expectation(row.get("expected"), where),
    )


def load_mock_scenarios(path: Path = _MOCK_INSPECTIONS_FILE) -> ScenarioLibrary:
    """목업 시나리오 JSON을 읽어 검증까지 마친 라이브러리를 만든다."""
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ScenarioNotReady(f"목업 시나리오를 읽을 수 없습니다: {path}") from exc
    if not isinstance(rows, list) or not rows:
        raise ScenarioNotReady(f"목업 시나리오가 비어 있습니다: {path}")

    scenarios = tuple(_parse_scenario(row, i) for i, row in enumerate(rows))

    names = [s.scenario for s in scenarios]
    if len(set(names)) != len(names):
        raise ScenarioNotReady(f"시나리오 이름이 중복됩니다: {names}")

    by_product_id: dict[int, MockScenario] = {}
    for scenario in scenarios:
        if scenario.product_id in by_product_id:
            raise ScenarioNotReady(f"product_id가 중복됩니다: {scenario.product_id}")
        by_product_id[scenario.product_id] = scenario

    return ScenarioLibrary(scenarios=scenarios, _by_product_id=by_product_id)


@lru_cache
def get_scenarios() -> ScenarioLibrary:
    """서비스가 공유하는 시나리오 라이브러리 싱글턴(로드 결과 캐시)."""
    return load_mock_scenarios()


# --- 폴백 합성 -------------------------------------------------------------


def _seed_from(key: str) -> int:
    """키를 시드로 바꾼다. 같은 키는 항상 같은 시드를 준다."""
    return int.from_bytes(hashlib.sha256(key.encode("utf-8")).digest()[:8], "little")


def _fallback_scenario(
    product_id: int,
    category: GarmentCategory,
    base_color: BaseColor,
) -> MockScenario:
    """미등록 `product_id`용 결정적 시나리오.

    데모에서 아무 상품 id를 넣어도 그럴듯한 결과가 나오게 하되, 같은 id는 항상 같은 결과를
    준다(CI 재현성). 기대치(`expected`)는 없다 — 회귀 테스트 대상이 아니기 때문이다.
    """
    rng = np.random.default_rng(_seed_from(f"quality:scenario:{product_id}"))
    blob_count = int(rng.integers(0, _FALLBACK_MAX_BLOBS + 1))

    blobs = tuple(
        MockBlob(
            image_index=0,
            defect_type=_FALLBACK_DEFECT_TYPES[int(rng.integers(0, len(_FALLBACK_DEFECT_TYPES)))],
            center=(float(rng.uniform(0.2, 0.8)), float(rng.uniform(0.2, 0.8))),
            radius=float(rng.uniform(0.09, 0.16)),
            peak=float(rng.uniform(0.45, 0.9)),
            clean_overlap=float(rng.uniform(0.03, 0.12)),
            cross_talk=0.0,
        )
        for _ in range(blob_count)
    )

    return MockScenario(
        scenario=f"generated_{product_id}",
        note="미등록 product_id — 시드 기반으로 합성된 시나리오입니다(회귀 테스트 대상 아님).",
        product_id=product_id,
        category=category,
        base_color=base_color,
        image_count=1,
        background_defect=_FALLBACK_BACKGROUND_DEFECT,
        background_clean=_FALLBACK_BACKGROUND_CLEAN,
        blobs=blobs,
        expected=None,
    )
