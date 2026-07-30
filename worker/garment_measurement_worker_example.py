"""의류 실측(cm) 측정 워커 — 기준 물체 검출 + 원단 분할 + 랜드마크 검출 + cm 환산.

게이트웨이가 `POST /measurement/scans`로 받은 job을 폴링해 처리한다. 각 단계 로직은
`worker/models/garment_measurement/`에 있고, 이 파일은 **오케스트레이션만** 한다:
기준 물체 검출 → (실패 시 즉시 재촬영 사유 반환) → 원단 분할 → (실패 시 즉시 반환) →
랜드마크 검출 → cm 환산.

**이 fail-fast 순서 자체가 성능 설계다** — 원단 분할·랜드마크 검출(무거운 단계)은 기준 물체를
못 찾은 사진에는 아예 실행되지 않는다. 실시간 웹캠 프리뷰의 "카드/용지가 프레임에 들어왔는지"
체크는 이 워커와 무관한 FE 클라이언트 사이드 몫이다 — 이 워커는 최종 캡처 스냅샷 1장만 받는다.

**GPU 없이도 돌릴 수 있다.** 세 단계 전부 `mock`이 기본값이라, 실제 CV/모델 없이도 job 큐
왕복 전체를 검증할 수 있다.

```bash
python garment_measurement_worker_example.py                          # 전부 mock, GPU 불필요
REFERENCE_BACKEND=opencv_contour python garment_measurement_worker_example.py
```

설계: .claude/plans/ai/010-garment-measurement-scan.md
BE 계약: .claude/requests/be/004-garment-measurement-scan.md
"""

import os
import sys
import time

from base_worker import BaseWorker

# 처리 로직(worker/models/garment_measurement)을 import 할 수 있도록 경로 추가.
# **부모 디렉터리(worker/models)를 추가한다** — CatVTON의 `model.` 네임스페이스 방식과 같은
# 이유다. clipseg는 contracts.py/registry.py/scenarios.py/segmenter.py를 flat하게 sys.path
# 최상단에 두는데, garment_measurement도 같은 이름의 파일이 있어서(둘 다 같은 pytest 세션에서
# sys.path에 동시에 들어감) flat 삽입을 그대로 따라 하면 `import contracts`가 어느 쪽을
# 가져올지 꼬인다(먼저 import된 모듈이 캐시됨). 그래서 garment_measurement는 진짜 서브패키지로
# 만들고 `from garment_measurement.xxx import ...` 형태로만 접근한다.
MEASUREMENT_CODE_PATH = os.getenv(
    "MEASUREMENT_CODE_PATH",
    os.path.join(os.path.dirname(__file__), "models"),
)
sys.path.insert(0, MEASUREMENT_CODE_PATH)

from garment_measurement import cm_converter, registry  # noqa: E402
from garment_measurement.contracts import GarmentCategory, ModelInfo, RetakeReason  # noqa: E402
from garment_measurement.landmark_detector import build_landmark_detector  # noqa: E402
from garment_measurement.reference_detector import build_reference_detector  # noqa: E402
from garment_measurement.segmenter import build_segmenter  # noqa: E402

# 세 단계 전부 독립적으로 스왑 가능 — registry.*_BACKENDS 의 키.
REFERENCE_BACKEND = os.getenv("REFERENCE_BACKEND", registry.ACTIVE_REFERENCE_BACKEND)
SEGMENTATION_BACKEND = os.getenv("SEGMENTATION_BACKEND", registry.ACTIVE_SEGMENTATION_BACKEND)
LANDMARK_BACKEND = os.getenv("LANDMARK_BACKEND", registry.ACTIVE_LANDMARK_BACKEND)


class GarmentMeasurementWorker(BaseWorker):
    feature = "garment_measurement"

    def __init__(self):
        super().__init__()
        self._reference_detector = None
        self._segmenter = None
        self._landmark_detector = None

    def _ensure_loaded(self):
        """세 단계 구현체는 워커 프로세스당 한 번만 만든다."""
        if self._reference_detector is not None:
            return
        print(
            f"[{self.worker_id}] 로딩 중... "
            f"(reference={REFERENCE_BACKEND}, segmentation={SEGMENTATION_BACKEND}, "
            f"landmark={LANDMARK_BACKEND})"
        )
        self._reference_detector = build_reference_detector(REFERENCE_BACKEND)
        self._segmenter = build_segmenter(SEGMENTATION_BACKEND)
        self._landmark_detector = build_landmark_detector(LANDMARK_BACKEND)
        print(f"[{self.worker_id}] 준비 완료")

    def run_inference(self, payload: dict) -> dict:
        """
        payload (= `app/measurement/schemas.py`의 MeasurementScanRequest):
        {
            "product_id": 1042,
            "image_url": "https://.../scan.jpg",
            "category": "SHORT_SLEEVE_TOP",
            "reference_object": "A4_PAPER"
        }
        """
        self._ensure_loaded()
        started = time.perf_counter()

        product_id = int(payload["product_id"])
        image_url = payload["image_url"]
        category = GarmentCategory(payload["category"])

        model_info = ModelInfo(
            reference_backend=REFERENCE_BACKEND,
            segmentation_backend=SEGMENTATION_BACKEND,
            landmark_backend=LANDMARK_BACKEND,
        )

        reference = self._reference_detector.detect(image_url, product_id)
        if not reference.found:
            return self._retake_result(
                product_id, model_info, RetakeReason.reference_not_found, started
            )

        segmentation = self._segmenter.segment(image_url, product_id)
        if not segmentation.found:
            return self._retake_result(
                product_id,
                model_info,
                RetakeReason.garment_not_found,
                started,
                reference_object_found=True,
                pixel_to_cm_ratio=reference.pixel_to_cm_ratio,
            )

        landmarks = self._landmark_detector.detect(
            image_url, product_id, category, bbox=segmentation.bbox
        )
        measurements = cm_converter.convert(landmarks, reference.pixel_to_cm_ratio)

        overall_confidence = min((lm.confidence for lm in landmarks), default=0.0)
        notes = []
        retake_reason = None
        needs_retake = False
        if not landmarks:
            needs_retake = True
            retake_reason = RetakeReason.low_landmark_confidence
            notes.append("랜드마크를 하나도 찾지 못했습니다 — 다시 촬영해 주세요.")

        return {
            "measurement_id": f"scan_{product_id}_{self.worker_id}",
            "product_id": product_id,
            "model": model_info.to_dict(),
            "reference_object_found": True,
            "pixel_to_cm_ratio": reference.pixel_to_cm_ratio,
            "landmarks": [lm.to_dict() for lm in landmarks],
            "measurements": [m.to_dict() for m in measurements],
            "overall_confidence": overall_confidence,
            "needs_retake": needs_retake,
            "retake_reason": retake_reason.value if retake_reason else None,
            "notes": notes,
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
        }

    def _retake_result(
        self,
        product_id: int,
        model_info: ModelInfo,
        reason: RetakeReason,
        started: float,
        *,
        reference_object_found: bool = False,
        pixel_to_cm_ratio: float | None = None,
    ) -> dict:
        """기준 물체·원단을 못 찾았을 때 즉시 반환하는 결과 — 뒷 단계는 아예 실행하지 않는다."""
        return {
            "measurement_id": f"scan_{product_id}_{self.worker_id}",
            "product_id": product_id,
            "model": model_info.to_dict(),
            "reference_object_found": reference_object_found,
            "pixel_to_cm_ratio": pixel_to_cm_ratio,
            "landmarks": [],
            "measurements": [],
            "overall_confidence": 0.0,
            "needs_retake": True,
            "retake_reason": reason.value,
            "notes": [],
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
        }


if __name__ == "__main__":
    GarmentMeasurementWorker().loop()
