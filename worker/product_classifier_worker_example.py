"""상품 정보 분류(카테고리+색상) 워커 — 오케스트레이션만 한다.

게이트웨이가 `POST /product-classifier/classify`로 받은 job을 폴링해 처리한다. 판정 로직은
`worker/models/product_classifier/`에 있고, 이 파일은 **오케스트레이션만** 한다:
이미지 다운로드 → 카테고리 분류 → 색상 추출 → 결과 조립.

**GPU도, 무거운 의존성도 없이 돌릴 수 있다.** 두 백엔드 다 기본값이 `mock`이라 torch 없이
전 경로(다운로드·분류·조립·업로드)를 그대로 검증할 수 있다 — `quality_check_worker_example.py`
와 같은 mock-우선 관례.

```bash
python product_classifier_worker_example.py  # 기본값: 둘 다 mock
PRODUCT_CLASSIFIER_CATEGORY_BACKEND=clip_finetuned PRODUCT_CLASSIFIER_COLOR_BACKEND=clip_finetuned \\
    python product_classifier_worker_example.py  # 실백엔드(파인튜닝된 CLIP)로 돌리려면
```

**실백엔드(`clip_finetuned`)가 `registry.py`에 등록돼 있지만 커밋된 기본값은 여전히
`mock`이다** — 위 명령처럼 환경변수로 켜야 실제로 분류가 돈다. 꺼둔 채로 실행하면 이 워커는
mock 결과만 반환한다(`score=0.0`, `action="none"` — 폼에 아무것도 자동 채워지지 않는다).
**전처리 미연결**: 체크포인트가 AI-Hub 정답 polygon으로 배경을 제거한 크롭(`variant="masked"`)
으로 학습됐는데, 이 워커는 `download_image()`가 받아온 원본 사진을 크롭/마스킹 없이 그대로
분류기에 넣는다 — 하자검수(`quality_check`)의 SAM3 크롭을 재사용하도록 연결하는 작업은 아직
안 됐다(별도 설계 필요, 보류 중).

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
            "product_id": 1042,  // 사전업로드(상품 생성 전) 트리거면 None일 수 있다
            "image_url": "https://.../front.jpg",
            "taxonomy_version": "v2-be-seed-2026-08-03"
        }
        """
        self._ensure_loaded()
        started = time.perf_counter()

        raw_product_id = payload.get("product_id")
        product_id = int(raw_product_id) if raw_product_id is not None else None
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
            # 요청값을 에코하지 않는다 — 워커는 taxonomy 버전을 선택할 수 없고(taxonomy.py
            # 하나뿐) 항상 이 값으로 분류하므로, 요청이 뭐라고 보냈든 실제로 쓴 버전을
            # 그대로 낸다. 예전엔 payload.get("taxonomy_version", TAXONOMY_VERSION)로 요청
            # 기본값을 그대로 돌려줘서, 실제로는 다른 버전으로 분류해놓고 응답만 옛 버전으로
            # 잘못 표시하는 버그가 있었다.
            "taxonomy_version": TAXONOMY_VERSION,
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
        }


if __name__ == "__main__":
    ProductClassifierWorker().loop()
