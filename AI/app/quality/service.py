"""품질 검수 파이프라인 오케스트레이션.

5단을 순서대로 엮는다: **프롬프트 선택 → 세그멘테이션 → 하자 항목화 → 점수 → (선택) 오버레이.**
각 단계의 판단은 전부 다른 모듈에 있고, 여기는 순서와 실패 처리만 책임진다.

**동기 REST인 이유**: 상품 등록은 판매자가 화면에서 기다리는 인터랙티브 흐름이라 job 폴링을
끼우면 UX가 나빠진다. 목업·CLIPSeg 모두 즉시 응답이 가능하다. GPU 워커 경유가 불가피해지면
`registry.ACTIVE_SEGMENTER = "remote_worker"` 한 줄로 넘어가고 **API 계약과 downstream은
그대로 유지된다.**

**AI는 판정만 하고 저장·집행은 BE가 한다** — 판매자 소명 본문은 여기 오지 않고, finding `key`와
`statement_required` 플래그까지만 제공한다(003 "판정 위임" 선례와 같은 경계).

`get_quality_service()`의 조립부가 **유일한 구현 스왑 지점**이다.

설계: .claude/plans/ai/005-quality-inspection-prototype.md
"""

from __future__ import annotations

import logging
import time
import uuid
from functools import lru_cache

from app.quality import registry
from app.quality.findings import extract_findings
from app.quality.overlay import build_attention_maps
from app.quality.prompts import SECTION_LABELS, select_prompt_set
from app.quality.scenarios import get_scenarios
from app.quality.schemas import (
    BackendView,
    BaseColor,
    DefectPolicyView,
    GarmentCategory,
    InspectionRequest,
    InspectionResponse,
    ModelInfo,
    PromptSetView,
    QualityConfigResponse,
)
from app.quality.scoring import DEFECT_LABELS, build_notes, score_findings, summarize
from app.quality.segmenter import (
    DefectSegmenter,
    ImageFetchFailed,
    InspectionTarget,
    SegmentationResult,
    SegmenterNotReady,
    build_segmenter,
)
from app.quality.store import (
    InspectionNotFound,
    InspectionStore,
    build_inspection_store,
)

# 라우터가 import하기 쉽도록 재노출(503/502/404 매핑용).
__all__ = [
    "QualityInspectionService",
    "SegmenterNotReady",
    "ImageFetchFailed",
    "InspectionNotFound",
    "get_quality_service",
]

_OVERLAY_FAILED_NOTE = "히트맵 이미지를 생성하지 못했습니다 — 검수 결과 자체는 정상입니다."

_UNVERIFIED_NOTICE = (
    "임계치·점수 가중치·등급 경계는 라벨링된 검증셋이 없어 아직 확정되지 않은 임의값입니다. "
    "clean_margin(대조 정규화)도 CLIPSeg 기준 미검증입니다."
)

logger = logging.getLogger(__name__)


class QualityInspectionService:
    """상품 이미지 → 하자 항목 리스트 + 컨디션 점수 + (선택) Attention Map."""

    def __init__(
        self,
        segmenter: DefectSegmenter,
        store: InspectionStore,
        *,
        backend: str | None = None,
    ) -> None:
        self._segmenter = segmenter
        self._store = store
        self._backend = backend or registry.ACTIVE_SEGMENTER
        self._config = registry.segmenter_config(self._backend)

    # -- 검수 ------------------------------------------------------------
    def inspect(self, request: InspectionRequest) -> InspectionResponse:
        """동기 검수 1건. 세그멘터가 준비 안 됐으면 `SegmenterNotReady`,
        이미지를 못 읽으면 `ImageFetchFailed`가 그대로 올라간다(라우터가 503/502로 매핑)."""
        started = time.perf_counter()
        prompt_set = select_prompt_set(request.category, request.base_color)
        target = InspectionTarget(
            product_id=request.product_id,
            image_urls=tuple(request.image_urls),
            prompt_set=prompt_set,
        )

        results: list[SegmentationResult] = [
            self._segmenter.segment(target, index) for index in range(len(request.image_urls))
        ]

        extracted = extract_findings(results, prompt_set, self._config)
        score, grade = score_findings(extracted.findings)
        notes = build_notes(extracted.findings, extracted.unreliable_prompts)

        inspection_id = f"insp_{request.product_id}_{uuid.uuid4().hex[:6]}"
        attention_maps = []
        if request.include_attention_maps:
            attention_maps, overlay_note = self._render_overlays(
                inspection_id, results, extracted.findings, prompt_set
            )
            if overlay_note:
                notes.append(overlay_note)

        response = InspectionResponse(
            inspection_id=inspection_id,
            product_id=request.product_id,
            model=ModelInfo(
                backend=self._backend,
                model_id=self._config["model_id"],
                prompt_set=prompt_set.key,
            ),
            condition_score=score,
            condition_grade=grade,
            summary=summarize(extracted.findings),
            findings=extracted.findings,
            section_scores=extracted.section_scores,
            attention_maps=attention_maps,
            notes=notes,
            latency_ms=round((time.perf_counter() - started) * 1000, 3),
        )
        self._store.save(response)
        return response

    def _render_overlays(self, inspection_id, results, findings, prompt_set):
        """오버레이 생성 실패가 **검수 자체를 실패시키지 않게** 감싼다.

        히트맵은 부가 산출물이다. 디스크가 가득 찼다고 해서 이미 계산이 끝난 하자 항목과 점수를
        버리고 500을 돌려주는 건 손해다 — 대신 notes로 드러낸다.
        """
        try:
            return (
                build_attention_maps(inspection_id, results, findings, prompt_set, self._config),
                None,
            )
        except OSError as exc:
            logger.warning("오버레이 생성 실패 (inspection=%s): %s", inspection_id, exc)
            return [], _OVERLAY_FAILED_NOTE

    # -- 재조회 ----------------------------------------------------------
    def get_inspection(self, inspection_id: str) -> InspectionResponse:
        """없거나 TTL이 지났으면 `InspectionNotFound`."""
        return self._store.get(inspection_id)

    # -- 활성 설정 노출 ----------------------------------------------------
    def describe_config(self) -> QualityConfigResponse:
        """현재 백엔드·임계치·프롬프트·분류 체계를 그대로 돌려준다.

        임계치와 점수 가중치가 전부 미확정 임의값인 단계라, **무엇이 확정되지 않았는지도 함께**
        노출한다. 이 값을 소비하는 쪽(가격책정 등)이 확정치로 착각하지 않게 하려는 것이다.
        """
        return QualityConfigResponse(
            active_segmenter=self._backend,
            backends=[
                BackendView(
                    backend=key,
                    active=key == self._backend,
                    model_id=config["model_id"],
                    description=config["description"],
                    mask_size=config["mask_size"],
                    defect_threshold=config["defect_threshold"],
                    confident_threshold=config["confident_threshold"],
                    clean_margin=config["clean_margin"],
                    min_area_ratio=config["min_area_ratio"],
                )
                for key, config in registry.SEGMENTER_BACKENDS.items()
            ],
            taxonomy=[
                DefectPolicyView(
                    defect_type=defect_type,
                    label=DEFECT_LABELS.get(defect_type, defect_type.value),
                    trusted=policy["trusted"],
                    needs_seller_review=policy["needs_seller_review"],
                    statement_required=policy["statement_required"],
                    weight=policy["weight"],
                    evidence=policy["evidence"],
                )
                for defect_type, policy in registry.DEFECT_TAXONOMY.items()
            ],
            prompt_sets=[
                PromptSetView(
                    key=prompt_set.key,
                    category=category,
                    base_color=base_color,
                    clean_prompt=prompt_set.clean_prompt,
                    defect_prompts=dict(prompt_set.defect_prompts),
                    sections=list(SECTION_LABELS[category]),
                )
                for category in GarmentCategory
                for base_color in BaseColor
                for prompt_set in [select_prompt_set(category, base_color)]
            ],
            mock_product_ids=list(get_scenarios().registered_product_ids()),
            unverified_notice=_UNVERIFIED_NOTICE,
        )


@lru_cache
def get_quality_service() -> QualityInspectionService:
    """FastAPI 의존성 주입용 서비스 프로바이더(싱글턴).

    **여기가 유일한 스왑 지점이다.** 실모델로 갈아끼울 때는 `registry.ACTIVE_SEGMENTER` 키만
    바꾸면 되고, 이 함수는 그대로 둔다.

    세그멘터를 싱글턴으로 잡는 이유: CLIPSeg는 첫 호출에서 체크포인트를 로드해 인스턴스에
    들고 있는다. 요청마다 새로 만들면 매번 모델을 다시 읽는다.
    """
    return QualityInspectionService(
        segmenter=build_segmenter(),
        store=build_inspection_store(),
    )
