"""상품 정보 분류(카테고리+색상) 백엔드 — 서브패키지로 감싸는 이유.

`worker/models/sam3/__init__.py`, `worker/models/quality_vlm/__init__.py`와 같은 이유다 —
여러 워커 패키지가 같은 이름의 모듈(`registry.py`/`classifier.py`/`color.py`)을 가진 채
한 프로세스에 flat하게 로드되면 `sys.modules` 캐시가 충돌한다.

그래서 이 패키지도 **부모 디렉터리(`worker/models/`)를 sys.path에 넣고**
`from product_classifier.xxx import ...` 형태로만 접근한다. 내부 모듈끼리는 상대 import
(`from . import registry` 등)를 쓴다. 런타임 진입점은
`worker/product_classifier_worker_example.py`다.

**아직 mock 백엔드만 있다.** 실제 카테고리(CLIP 파인튜닝 예정)·색상(방식 미정, CLIP
임베딩+분류 헤드 검증 중) 백엔드는 `AI/validation/CLASS/product-info-check/`에서 검증이
끝난 뒤에 여기 꽂는다 — 검증 안 된 걸 프로덕션에 먼저 심지 않는다(2026-08-02 판단).

설계: `.claude/plans/ai/CH012-~2.MD`
"""
