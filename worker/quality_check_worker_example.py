"""품질 검수 워커 — SAM3 오케스트레이션.

게이트웨이가 `POST /quality/inspections`로 받은 job을 폴링해 처리한다. 판정 로직은
`worker/models/sam3/`에 있고, 이 파일은 **오케스트레이션만** 한다:
프롬프트 선택 → 세그멘테이션 → 하자 항목화 → 점수 → 넘버링 bbox 이미지 → (선택) 히트맵 업로드.

**GPU 없이도 돌릴 수 있다.** `QUALITY_BACKEND=mock`이면 목업으로 인스턴스를 합성하므로
전 경로(항목화·점수·오버레이)를 그대로 검증할 수 있다.

```bash
QUALITY_BACKEND=mock python quality_check_worker_example.py
QUALITY_BACKEND=sam3_pcs python quality_check_worker_example.py
```

**후처리까지 워커가 하는 이유**: 확률 마스크/인스턴스 마스크를 게이트웨이로 넘기려면 Redis에
실어야 하는데, 인프라 문서 §3.3이 큰 바이너리를 금지한다. 그래서 워커가 리포트 JSON만 만들어
반환하고, 오버레이 PNG는 업로드해 URL로 넘긴다.

설계: .claude/plans/ai/005-quality-inspection-prototype.md, .claude/plans/ai/CH006-sam3-quality-segmenter.md,
.claude/plans/ai/CH007-quality-bbox-bullets.md
BE 계약: .claude/requests/be/001-quality-inspection-async.md
"""

import os
import sys
import time

from base_worker import BaseWorker
from storage_utils import upload_image

# `sam3/`는 `worker/models/garment_measurement/`와 같은 이유로 진짜 서브패키지(`__init__.py`
# 보유)다 — 여러 워커 패키지가 한 프로세스(테스트 스위트 등)에 동시에 로드될 때 같은 이름의
# 파일(contracts.py/registry.py/...)이 flat하게 sys.path에 들어가면 `sys.modules` 캐시가
# 충돌한다(`AI/test/conftest.py` 참고). 그래서 **부모 디렉터리**(`worker/models/`)를
# sys.path에 넣고 `sam3.xxx` 네임스페이스로만 접근한다.
_MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
sys.path.insert(0, os.getenv("QUALITY_MODEL_CODE_PATH", _MODELS_DIR))

from sam3 import registry  # noqa: E402
from sam3.contracts import BaseColor, GarmentCategory  # noqa: E402
from sam3.findings import extract_findings  # noqa: E402
from sam3.overlay import build_annotated_images, build_attention_maps  # noqa: E402
from sam3.prompts import select_prompt_set  # noqa: E402
from sam3.scoring import build_notes, score_findings, summarize  # noqa: E402
from sam3.segmenter import InspectionTarget, build_segmenter  # noqa: E402

# 어떤 세그멘터로 돌릴지. registry.SEGMENTER_BACKENDS 의 키.
QUALITY_BACKEND = os.getenv("QUALITY_BACKEND", registry.ACTIVE_SEGMENTER)


class QualityCheckWorker(BaseWorker):
    feature = "quality_check"

    def __init__(self):
        super().__init__()
        self._segmenter = None
        self._config = registry.segmenter_config(QUALITY_BACKEND)

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

    def run_inference(self, payload: dict) -> dict:
        """
        payload (= `app/quality/schemas.py`의 InspectionRequest):
        {
            "product_id": 1042,
            "image_urls": ["https://.../front.jpg", "..."],
            "category": "TOP_KNIT",
            "base_color": "LIGHT",
            "include_attention_maps": false
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

        return {
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
            "findings": [f.to_dict() for f in extracted.findings],
            "section_scores": [s.to_dict() for s in extracted.section_scores],
            "attention_maps": [m.to_dict() for m in attention_maps],
            "annotated_images": [m.to_dict() for m in annotated_images],
            "notes": notes,
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
        }


if __name__ == "__main__":
    QualityCheckWorker().loop()
