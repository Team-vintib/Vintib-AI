"""품질 검수 워커 — CLIPSeg/SAM3 겸용 오케스트레이션.

게이트웨이가 `POST /quality/inspections`로 받은 job을 폴링해 처리한다. 판정 로직은
`worker/models/{clipseg,sam3}/`에 있고, 이 파일은 **오케스트레이션만** 한다:
프롬프트 선택 → 세그멘테이션 → 하자 항목화 → 점수 → (선택) 오버레이 업로드.

**두 모델 패밀리를 동시에 지원한다.** SAM3는 CLIPSeg와 계약 모양이 근본적으로 달라(확률
히트맵이 아니라 인스턴스를 직접 냄) `worker/models/sam3/`에 완전히 분리된 패키지(방식 B —
네이티브 경로)로 구현됐다. `QUALITY_MODEL_FAMILY`로 어느 패키지의 코드를 로드할지 고르고,
그 패밀리 안에서 `QUALITY_BACKEND`로 세부 백엔드(mock/실모델)를 고른다.

**GPU 없이도 돌릴 수 있다.** 어느 패밀리든 `QUALITY_BACKEND=mock`이면 목업으로 확률
마스크·인스턴스를 합성하므로 전 경로(항목화·점수·오버레이)를 그대로 검증할 수 있다.

```bash
QUALITY_MODEL_FAMILY=clipseg QUALITY_BACKEND=mock python quality_check_worker_example.py
QUALITY_MODEL_FAMILY=clipseg QUALITY_BACKEND=clipseg_rd64_refined python quality_check_worker_example.py
QUALITY_MODEL_FAMILY=sam3    QUALITY_BACKEND=mock python quality_check_worker_example.py
QUALITY_MODEL_FAMILY=sam3    QUALITY_BACKEND=sam3_pcs python quality_check_worker_example.py
```

`QUALITY_MODEL_FAMILY` 기본값은 `clipseg`다 — **환경변수를 아무것도 안 주면 지금까지와
100% 같은 동작**이다(기존 배포와 호환).

**후처리까지 워커가 하는 이유**: 확률 마스크/인스턴스 마스크를 게이트웨이로 넘기려면 Redis에
실어야 하는데, 인프라 문서 §3.3이 큰 바이너리를 금지한다. 그래서 워커가 리포트 JSON만 만들어
반환하고, 오버레이 PNG는 업로드해 URL로 넘긴다.

설계: .claude/plans/ai/005-quality-inspection-prototype.md, .claude/plans/ai/CH006-sam3-quality-segmenter.md
BE 계약: .claude/requests/be/001-quality-inspection-async.md
"""

import os
import sys
import time

from base_worker import BaseWorker
from storage_utils import upload_image

# 어느 모델 패밀리의 코드(worker/models/<family>/)를 로드할지.
QUALITY_MODEL_FAMILY = os.getenv("QUALITY_MODEL_FAMILY", "clipseg")
if QUALITY_MODEL_FAMILY not in ("clipseg", "sam3"):
    raise SystemExit(
        f"알 수 없는 QUALITY_MODEL_FAMILY입니다: {QUALITY_MODEL_FAMILY!r} (clipseg 또는 sam3)"
    )

_MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")

# **패밀리마다 import 방식이 다르다 — 의도적이다.** `clipseg/`는 flat 패키지라
# (CatVTON의 `CATVTON_CODE_PATH`와 같은 방식) 그 디렉터리 자체를 sys.path에 넣고
# `import registry`로 바로 접근한다. `sam3/`는 `clipseg/`와 파일명이 완전히 같아서
# (contracts.py/registry.py/...) 똑같이 flat하게 두면 두 패밀리를 한 프로세스에서 같이 다룰
# 때(테스트 스위트 등) `sys.modules` 캐시가 충돌한다 — `AI/test/conftest.py`가
# `garment_measurement`에 쓰는 것과 같은 이유·같은 해법으로, `sam3/`는 서브패키지
# (`__init__.py` 보유)로 만들고 **부모 디렉터리**를 sys.path에 넣어 `sam3.xxx` 네임스페이스로만
# 접근한다.
if QUALITY_MODEL_FAMILY == "clipseg":
    _CODE_PATH = os.getenv("QUALITY_MODEL_CODE_PATH", os.path.join(_MODELS_DIR, "clipseg"))
    sys.path.insert(0, _CODE_PATH)

    import registry  # noqa: E402
    from contracts import BaseColor, GarmentCategory  # noqa: E402
    from findings import extract_findings  # noqa: E402
    from overlay import build_attention_maps as _build_attention_maps  # noqa: E402
    from prompts import select_prompt_set  # noqa: E402
    from scoring import build_notes, score_findings, summarize  # noqa: E402
    from segmenter import InspectionTarget, build_segmenter  # noqa: E402

    def _render_attention_maps(results, extracted, prompt_set, config):
        return _build_attention_maps(results, extracted.findings, prompt_set, config, upload_image)

    def _render_annotated_images(results, extracted, prompt_set, config):
        # CH007(넘버링 bbox 이미지)은 SAM3만 우선 구현한다 — clipseg는 당장 빈 리스트.
        del results, extracted, prompt_set, config
        return []

else:  # sam3
    sys.path.insert(0, os.getenv("QUALITY_MODEL_CODE_PATH", _MODELS_DIR))

    from sam3 import registry  # noqa: E402
    from sam3.contracts import BaseColor, GarmentCategory  # noqa: E402
    from sam3.findings import extract_findings  # noqa: E402
    from sam3.overlay import build_annotated_images as _build_annotated_images  # noqa: E402
    from sam3.overlay import build_attention_maps as _build_attention_maps  # noqa: E402
    from sam3.prompts import select_prompt_set  # noqa: E402
    from sam3.scoring import build_notes, score_findings, summarize  # noqa: E402
    from sam3.segmenter import InspectionTarget, build_segmenter  # noqa: E402

    def _render_attention_maps(results, extracted, prompt_set, config):
        # `overlay.build_attention_maps()`의 시그니처가 패밀리마다 다르다 — CLIPSeg는 연속
        # 히트맵을 `config`(defect_threshold 등)로 findings와 맞춰 자르고, SAM3는 이미 이산
        # 인스턴스라 `kept_instances_by_image`(필터를 통과한 인스턴스, findings.py 참고)를
        # 직접 받는다. 오케스트레이션 본문(`run_inference`)을 패밀리별로 분기하지 않도록
        # 여기서 어댑터로 감싼다.
        del prompt_set, config  # SAM3 쪽 build_attention_maps는 이 둘이 필요 없다
        return _build_attention_maps(
            results, extracted.kept_instances_by_image, extracted.findings, upload_image
        )

    def _render_annotated_images(results, extracted, prompt_set, config):
        # 넘버링 bbox 이미지(CH007)는 findings만 있으면 그려지므로 config/prompt_set이 필요 없다.
        del prompt_set, config
        return _build_annotated_images(results, extracted.findings, upload_image)


# 어떤 세그멘터로 돌릴지. registry.SEGMENTER_BACKENDS 의 키(패밀리 안에서만 유효).
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
        print(
            f"[{self.worker_id}] 세그멘터 로딩 중... "
            f"(family={QUALITY_MODEL_FAMILY}, backend={QUALITY_BACKEND})"
        )
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
            attention_maps = _render_attention_maps(results, extracted, prompt_set, self._config)

        # 넘버링 bbox 이미지(CH007)는 attention_maps와 달리 옵션이 아니다 — FE/BE에 넘길
        # 기본 산출물로 취급해 항상 만든다(플래그 없음, CH007 미결정 사항 참고).
        annotated_images = _render_annotated_images(results, extracted, prompt_set, self._config)

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
