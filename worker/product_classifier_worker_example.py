"""상품 정보 분류(카테고리+색상) 워커 — 오케스트레이션만 한다.

게이트웨이가 `POST /product-classifier/classify`로 받은 job을 폴링해 처리한다. 판정 로직은
`worker/models/product_classifier/`에 있고, 이 파일은 **오케스트레이션만** 한다:
이미지 다운로드 → 카테고리 분류 → 색상 추출 → 결과 조립.

**GPU도, 무거운 의존성도 없이 돌릴 수 있다.** 두 백엔드 다 기본값이 `mock`이라 torch 없이
전 경로(다운로드·분류·조립·업로드)를 그대로 검증할 수 있다 — `quality_check_worker_example.py`
와 같은 mock-우선 관례.

```bash
python product_classifier_worker_example.py  # 기본값: 둘 다 mock
PRODUCT_CLASSIFIER_CATEGORY_BACKEND=mock PRODUCT_CLASSIFIER_COLOR_BACKEND=mock \\
    python product_classifier_worker_example.py
```

**실백엔드가 아직 없다.** 카테고리(CLIP 파인튜닝)·색상(방식 미정)은
`AI/validation/CLASS/product-info-check/`에서 검증이 끝난 뒤
`worker/models/product_classifier/registry.py`에 추가된다(2026-08-02 판단 — 검증 안 된 걸
프로덕션에 먼저 심지 않는다). 그 전까지 이 워커는 mock 결과만 반환한다(`score=0.0`,
`action="none"` — 폼에 아무것도 자동 채워지지 않는다).

**실패 격리**: 카테고리·색상은 서로 독립적으로 실패할 수 있다 — 하나가 실패해도 다른 필드는
채워서 `success`로 반환한다. **둘 다 실패하면 예외를 그대로 올려 job을 `failed`로 만든다**
(CH012 §6.1 — 전 필드가 null인 success는 의미가 없다).

설계: `.claude/plans/ai/CH012-~2.MD`
"""

import os
import sys
import time

from base_worker import BaseWorker
from storage_utils import download_image

# `product_classifier/`는 `worker/models/garment_measurement/`와 같은 이유로 진짜
# 서브패키지(`__init__.py` 보유)다 — 여러 워커 패키지가 한 프로세스에 동시에 로드될 때 같은
# 이름의 파일(registry.py/classifier.py/color.py)이 flat하게 sys.path에 들어가면
# `sys.modules` 캐시가 충돌한다. 그래서 **부모 디렉터리**(`worker/models/`)를 sys.path에
# 넣고 `product_classifier.xxx` 네임스페이스로만 접근한다.
_MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
sys.path.insert(0, os.getenv("PRODUCT_CLASSIFIER_MODEL_CODE_PATH", _MODELS_DIR))

from product_classifier import registry  # noqa: E402
from product_classifier.classifier import build_classifier  # noqa: E402
from product_classifier.color import build_color_extractor  # noqa: E402
from product_classifier.taxonomy import TAXONOMY_VERSION  # noqa: E402

# 카테고리 분류를 어떤 백엔드로 돌릴지. registry.CATEGORY_BACKENDS의 키.
PRODUCT_CLASSIFIER_CATEGORY_BACKEND = os.getenv(
    "PRODUCT_CLASSIFIER_CATEGORY_BACKEND", registry.ACTIVE_CATEGORY_BACKEND
)
# 색상 추출을 어떤 백엔드로 돌릴지. registry.COLOR_BACKENDS의 키.
PRODUCT_CLASSIFIER_COLOR_BACKEND = os.getenv(
    "PRODUCT_CLASSIFIER_COLOR_BACKEND", registry.ACTIVE_COLOR_BACKEND
)


class ProductClassifierWorker(BaseWorker):
    feature = "product_classifier"

    def __init__(self):
        super().__init__()
        self._classifier = None
        self._color_extractor = None

    def _ensure_loaded(self):
        """분류기·색상 추출기는 워커 프로세스당 한 번만 만든다(모델 재로딩 방지)."""
        if self._classifier is None:
            print(
                f"[{self.worker_id}] 카테고리 분류기 로딩 중... "
                f"(backend={PRODUCT_CLASSIFIER_CATEGORY_BACKEND})"
            )
            self._classifier = build_classifier(PRODUCT_CLASSIFIER_CATEGORY_BACKEND)
        if self._color_extractor is None:
            print(
                f"[{self.worker_id}] 색상 추출기 로딩 중... "
                f"(backend={PRODUCT_CLASSIFIER_COLOR_BACKEND})"
            )
            self._color_extractor = build_color_extractor(PRODUCT_CLASSIFIER_COLOR_BACKEND)

    def run_inference(self, payload: dict) -> dict:
        """
        payload (= `app/product_classifier/schemas.py`의 `ProductClassifyRequest`):
        {
            "product_id": 1042,
            "image_url": "https://.../front.jpg",
            "taxonomy_version": "v1"
        }
        """
        self._ensure_loaded()
        started = time.perf_counter()

        product_id = int(payload["product_id"])
        image = download_image(payload["image_url"])

        # 키는 항상 셋 다 채운다(성공하면 값, 실패하면 None) — `app/product_classifier/schemas.py`의
        # `ProductClassifyFields`가 "키는 항상 있고 값만 nullable"을 전제로 한다. 실패했다고
        # 키 자체를 빼면 BE/FE가 매번 `.get()`으로 방어해야 한다.
        fields: dict = {"category": None, "color_primary": None, "color_secondary": None}
        category_error: str | None = None
        color_error: str | None = None

        try:
            category = self._classifier.classify(image)
            fields["category"] = category.to_dict()
        except Exception as exc:  # noqa: BLE001 — 실패 격리: 색상만이라도 채워서 반환
            category_error = str(exc)
            print(f"[{self.worker_id}] 카테고리 분류 실패: {exc}")

        try:
            color = self._color_extractor.extract(image)
            fields["color_primary"] = color.primary.to_dict()
            fields["color_secondary"] = color.secondary.to_dict() if color.secondary else None
        except Exception as exc:  # noqa: BLE001 — 실패 격리: 카테고리만이라도 채워서 반환
            color_error = str(exc)
            print(f"[{self.worker_id}] 색상 추출 실패: {exc}")

        if category_error and color_error:
            # 전 필드가 null인 success는 의미가 없다(CH012 §6.1) — 예외를 올려 job을
            # failed로 만든다. BaseWorker._process()가 이걸 잡아 error로 제출한다.
            raise RuntimeError(
                f"카테고리·색상 모두 실패: category={category_error}, color={color_error}"
            )

        return {
            "product_id": product_id,
            "fields": fields,
            "model": {
                "category_backend": PRODUCT_CLASSIFIER_CATEGORY_BACKEND,
                "color_backend": PRODUCT_CLASSIFIER_COLOR_BACKEND,
            },
            "taxonomy_version": payload.get("taxonomy_version", TAXONOMY_VERSION),
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
        }


if __name__ == "__main__":
    ProductClassifierWorker().loop()
