"""품질 검수 워커 — SAM3 오케스트레이션.

게이트웨이가 `POST /quality/inspections`로 받은 job을 폴링해 처리한다. 판정 로직은
`worker/models/sam3/`에 있고, 이 파일은 **오케스트레이션만** 한다:
프롬프트 선택 → 세그멘테이션 → 하자 항목화 → 점수 → 넘버링 bbox 이미지 → (선택) 히트맵 업로드
→ (선택) 하자 한 줄 설명(sVLM) → 판단 근거 로컬 로그.

**GPU 없이도 돌릴 수 있다.** `QUALITY_BACKEND=mock`이면 목업으로 인스턴스를 합성하므로
전 경로(항목화·점수·오버레이)를 그대로 검증할 수 있다. 하자 설명도 `QUALITY_VLM_BACKEND=mock`
(기본값)이면 정적 문구로 채워 같은 방식으로 torch 없이 전 경로를 검증할 수 있다.

```bash
QUALITY_BACKEND=mock python quality_check_worker_example.py
QUALITY_BACKEND=sam3_pcs QUALITY_VLM_BACKEND=qwen3_vl python quality_check_worker_example.py
```

**후처리까지 워커가 하는 이유**: 확률 마스크/인스턴스 마스크를 게이트웨이로 넘기려면 Redis에
실어야 하는데, 인프라 문서 §3.3이 큰 바이너리를 금지한다. 그래서 워커가 리포트 JSON만 만들어
반환하고, 오버레이 PNG는 업로드해 URL로 넘긴다.

설계: .claude/plans/ai/005-quality-inspection-prototype.md, .claude/plans/ai/CH006-sam3-quality-segmenter.md,
.claude/plans/ai/CH007-quality-bbox-bullets.md, .claude/plans/ai/CH008-quality-judgment-log.md,
.claude/plans/ai/CH011-quality-vlm-production-wiring.md
BE 계약: .claude/requests/be/001-quality-inspection-async.md, .claude/requests/be/002-quality-inspection-descriptions.md
"""

import os
import sys
import time

from base_worker import BaseWorker
from inspection_logger import log_inspection_result
from storage_utils import upload_image

# `sam3/`는 `worker/models/garment_measurement/`와 같은 이유로 진짜 서브패키지(`__init__.py`
# 보유)다 — 여러 워커 패키지가 한 프로세스(테스트 스위트 등)에 동시에 로드될 때 같은 이름의
# 파일(contracts.py/registry.py/...)이 flat하게 sys.path에 들어가면 `sys.modules` 캐시가
# 충돌한다(`AI/test/conftest.py` 참고). 그래서 **부모 디렉터리**(`worker/models/`)를
# sys.path에 넣고 `sam3.xxx` 네임스페이스로만 접근한다.
_MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
sys.path.insert(0, os.getenv("QUALITY_MODEL_CODE_PATH", _MODELS_DIR))

from quality_vlm import registry as vlm_registry  # noqa: E402
from quality_vlm.describer import attach_descriptions, build_describer  # noqa: E402
from sam3 import registry  # noqa: E402
from sam3.contracts import BaseColor, GarmentCategory  # noqa: E402
from sam3.findings import extract_findings  # noqa: E402
from sam3.garment_embedding import (  # noqa: E402
    EMBEDDING_MODEL_ID,
    GarmentEmbeddingNotReady,
    embed_garment,
)
from sam3.overlay import build_annotated_images, build_attention_maps  # noqa: E402
from sam3.prompts import select_prompt_set  # noqa: E402
from sam3.scoring import build_notes, score_findings, summarize, summarize_by_image  # noqa: E402
from sam3.segmenter import InspectionTarget, build_segmenter  # noqa: E402

# 어떤 세그멘터로 돌릴지. registry.SEGMENTER_BACKENDS 의 키.
QUALITY_BACKEND = os.getenv("QUALITY_BACKEND", registry.ACTIVE_SEGMENTER)
# 하자 설명(sVLM)을 어떤 백엔드로 돌릴지. vlm_registry.VLM_BACKENDS 의 키(CH011).
QUALITY_VLM_BACKEND = os.getenv("QUALITY_VLM_BACKEND", vlm_registry.ACTIVE_VLM_BACKEND)


class QualityCheckWorker(BaseWorker):
    feature = "quality_check"

    def __init__(self):
        super().__init__()
        self._segmenter = None
        self._config = registry.segmenter_config(QUALITY_BACKEND)
        self._describer = None

    def _ensure_loaded(self):
        """세그멘터는 워커 프로세스당 한 번만 만든다.

        실모델 백엔드는 첫 호출에서 체크포인트를 내려받아 인스턴스에 들고 있으므로, job마다
        새로 만들면 매번 모델을 다시 읽는다. 목업은 비용이 없지만 같은 경로를 쓴다.
        """
        if self._segmenter is not None:
            return
        print(f"[{self.worker_id}] 세그멘터 로딩 중... (backend={QUALITY_BACKEND})")
        self._segmenter = build_segmenter(QUALITY_BACKEND)
        print(f"[{self.worker_id}] 세그멘터 준비 완료")

    def _ensure_vlm_loaded(self):
        """describer도 프로세스당 한 번만 만든다(CH011).

        로드 실패(라이브러리 미설치·OOM 등)는 `"mock"`으로 폴백한다 — 하자 설명 하나
        때문에 검수 전체(`run_inference`)가 실패해 결과 자체를 잃으면 안 된다.
        """
        if self._describer is not None:
            return
        print(f"[{self.worker_id}] VLM describer 로딩 중... (backend={QUALITY_VLM_BACKEND})")
        try:
            self._describer = build_describer(QUALITY_VLM_BACKEND)
        except Exception as exc:
            print(f"[{self.worker_id}] VLM describer 로드 실패, mock으로 대체: {exc}")
            self._describer = build_describer("mock")
        print(f"[{self.worker_id}] VLM describer 준비 완료")

    @staticmethod
    def _embed_first_garment(results) -> list[float] | None:
        """여러 장 중 의류를 찾은 첫 이미지의 크롭으로 임베딩한다(상품당 벡터는 1개면
        충분 — 추천은 상품 단위지 이미지 단위가 아니다). 못 찾았거나(mock 포함) 계산이
        실패하면 None — `run_inference()`가 그 경우 결과 dict에 키 자체를 안 넣는다."""
        for r in results:
            if r.garment_crop is None:
                continue
            try:
                return embed_garment(r.garment_crop)
            except GarmentEmbeddingNotReady as exc:
                print(f"[garment_embedding] 준비 안 됨, 건너뜀: {exc}")
                return None
            except Exception as exc:  # noqa: BLE001 — 임베딩 실패가 검수를 막으면 안 된다
                print(f"[garment_embedding] 계산 실패, 건너뜀: {exc}")
                return None
        return None

    def run_inference(self, payload: dict) -> dict:
        """
        payload (= `app/quality/schemas.py`의 InspectionRequest):
        {
            "product_id": 1042,
            "image_urls": ["https://.../front.jpg", "..."],
            "category": "TOP_KNIT",
            "base_color": "LIGHT",
            "include_attention_maps": false,
            "include_descriptions": false
        }
        """
        self._ensure_loaded()
        started = time.perf_counter()

        product_id = int(payload["product_id"])
        image_urls = tuple(payload["image_urls"])
        category = GarmentCategory(payload["category"])
        base_color = BaseColor(payload.get("base_color", BaseColor.light.value))

        prompt_set = select_prompt_set(category, base_color)
        target = InspectionTarget(
            product_id=product_id, image_urls=image_urls, prompt_set=prompt_set
        )

        results = [self._segmenter.segment(target, i) for i in range(len(image_urls))]
        extracted = extract_findings(results, prompt_set, self._config)
        score, grade = score_findings(extracted.findings)
        notes = build_notes(extracted.findings, extracted.unreliable_prompts)

        attention_maps = []
        if payload.get("include_attention_maps"):
            attention_maps = build_attention_maps(
                results, extracted.kept_instances_by_image, extracted.findings, upload_image
            )

        # 넘버링 bbox 이미지(CH007)는 attention_maps와 달리 옵션이 아니다 — FE/BE에 넘길
        # 기본 산출물로 취급해 항상 만든다(플래그 없음, CH007 미결정 사항 참고).
        annotated_images = build_annotated_images(results, extracted.findings, upload_image)

        # 하자 한 줄 설명(sVLM, CH011) — 지연시간이 커서(finding당 수 초, 이미지당 수십 건
        # 가능) include_attention_maps와 같은 방식의 옵트인 플래그로 뒀다. bbox 오버레이
        # (필수 산출물)가 VLM 실패로 절대 막히면 안 되므로 그 뒤에 둔다.
        findings = extracted.findings
        if payload.get("include_descriptions"):
            self._ensure_vlm_loaded()
            findings = attach_descriptions(results, extracted.findings, self._describer)

        result = {
            "inspection_id": f"insp_{product_id}_{self.worker_id}",
            "product_id": product_id,
            "model": {
                "backend": QUALITY_BACKEND,
                "model_id": self._config["model_id"],
                "prompt_set": prompt_set.key,
            },
            "condition_score": score,
            "condition_grade": grade.value,
            "summary": summarize(extracted.findings),
            "image_summaries": [
                s.to_dict() for s in summarize_by_image(extracted.findings, len(image_urls))
            ],
            "findings": [f.to_dict() for f in findings],
            "section_scores": [s.to_dict() for s in extracted.section_scores],
            "attention_maps": [m.to_dict() for m in attention_maps],
            "annotated_images": [m.to_dict() for m in annotated_images],
            "notes": notes,
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
        }

        # 유사 상품 추천용 임베딩(범위: 계산+저장까지만) — SAM3가 하자 탐지 전에 이미 만든
        # 의류 크롭을 재사용한다(새 세그멘테이션 없음). 실패해도 검수 결과 자체는 그대로
        # 나가야 한다 — mock 백엔드는 garment_crop이 전부 None이라 자연히 건너뛴다.
        garment_embedding = self._embed_first_garment(results)
        if garment_embedding is not None:
            result["garment_embedding"] = garment_embedding
            result["garment_embedding_model_id"] = EMBEDDING_MODEL_ID

        # 판단 근거 로컬 로그(CH008) — Redis job result는 1시간 뒤 사라지고 BE는 finding.key/
        # statement_required만 저장한다. best-effort라 실패해도 검수 응답은 그대로 나간다.
        log_inspection_result(payload, result)

        return result


if __name__ == "__main__":
    QualityCheckWorker().loop()
