# CH020 — 내부 데이터 CLIP 이미지 유사도 기반 시세 조회 (1차, 합성 코퍼스)

> 관련 티켓: 미정(사용자 요청으로 착수, 별도 지라 티켓 없음).
>
> 선행: `CH016`(내부 호가 비교 — 정확 매칭 기법, BE 실데이터 0건이라 보류 중) /
> `CH017`(가격 검색 저비용 개선, 관측 로그 적재 구현) / `CH014`(분류기 파인튜닝,
> last-N=4 카테고리 체크포인트 산출)
>
> 산출 범위: **설계 + 구현.** 실제 코퍼스 시딩(GPU/torch 필요)과 EC2 프로덕션 배포는
> 범위 밖 — 아래 "범위 밖" 참고.
>
> **2026-08-06 추가 결론 — CH020의 위치 재확인.** 시세 조회는 본질적으로 "동일 상품"을
> 찾는 문제이고, 그 판별에는 CLIP 이미지 유사도보다 브랜드·상품명(텍스트) 매칭이 훨씬
> 정확한 신호다(CH016이 원래 그 방식이었던 이유). 게다가 이 라운드의 코퍼스 소스인
> AI-Hub 데이터엔 브랜드·상품명 라벨이 아예 없어 — 카테고리·색상 연구용 라벨만 있는
> 데이터라, 지금 코퍼스로는 애초에 "동일 상품" 판별이 불가능하고 "비슷한 카테고리·색상"
> 까지만 된다. **결론: CH020은 이번 라운드에서 메커니즘(임베딩→코퍼스→검색) 자체가
> 도는지만 확인하는 것으로 마친다.** 브랜드·상품명 기반 동일상품 매칭(CH016 방향)은
> BE 실데이터(brand_id 있는 상품)가 충분해지면 별도로 착수하고, CLIP 유사도는 그때
> 기껏해야 보조 신호로만 결합을 검토한다 — 지금 이 문서의 설계를 그대로 프로덕션
> 1순위 시세 로직으로 승격하지 않는다.

---

## 배경

지금 시세(가격) 조회는 `LlmWebSearchCompsSource`로 Gemini(GMS 경유) 웹검색만 쓴다.
사용자 요청: 이걸 **내부 데이터 기반 CLIP 이미지 유사도 검색**으로 먼저 시도해보고,
성능이 안 나오거나 막히는 지점이 생기면 그때 외부 API로 전환한다. 외부 검색은 완전히
빼되(코드는 그대로 둠), 이미 오늘도 `registry.ACTIVE_COMPS_SOURCE = "mock"`이 커밋된
기본값이라(`AI/CLAUDE.md` 하드 룰) 새 백엔드도 "만들어두되 기본은 안 켠다"가 자연스럽게
맞아떨어진다.

CH016과 대상은 같다(내부 데이터를 시세 근거로 쓴다)— 기법이 다르다. CH016은 브랜드
FK + 모델명 파싱으로 **동일 상품**을 정확 매칭하는 접근이고, 이번(CH020)은 CLIP 임베딩
코사인 유사도로 **비슷한 상품**을 찾는 접근이다. CH016은 §5에서 "유사상품 추천·임베딩
검색·pgvector 활용은 이번 범위가 아니다"라고 명시적으로 미뤄둔 부분을 이번에 다른
트랙으로 채우는 셈이다.

## 확인된 제약 두 가지

**1) (이미지, 실제가격) 쌍 데이터가 지금 어디에도 없다.** BE 상품 시드 60건(`origin/main`,
`BE/src/main/resources/db/product-seed.sql`) 중 `brand_id`가 있는 건 8건뿐이고, 참조하는
MinIO 이미지 키(`products/N.jpg`)에 실제 바이트가 있는지도 미확인이다. GMS 관찰 로그
(`pricing_search_observation`, CH017)는 텍스트/URL만 있고 이미지가 없다. AI→BE 실데이터
읽기 경로(뷰/API)도 없다 — CH016이 같은 이유(실사용 데이터 0건)로 멈춰 있는 상태 그대로다.

**결정**: AI-Hub 분류기 학습 이미지(`AI/validation/CLASS/`) + 카테고리별 임의 기준가로
코퍼스를 만들어 메커니즘부터 검증한다. 가격 숫자 자체는 검증 전까지 무의미하다 — 코퍼스
항목마다 `data_source="synthetic_aihub"`을 남겨 실데이터와 절대 안 섞이게 한다.

**2) `ai` 게이트웨이 컨테이너엔 GPU도 torch도 없다** (`docs/infra-architecture.md` §6:
"EC2 `ai` 컨테이너에는 GPU가 없고 torch도 없다(`mem_limit: 1g`)"). 다른 torch 필요 기능
(품질검수·시착·분류)은 전부 Redis 큐 + 노트북 워커 구조를 쓰는데, 가격책정만 컨테이너
내부에서 동기 처리한다 — `llm_web_search`가 `httpx` 아웃바운드만 필요했기 때문에
가능했던 예외다. CLIP 임베딩은 torch가 필요하므로, **이번 작업은 메커니즘을 로컬/개발
환경에서 만들고 검증 가능하게 하는 것까지가 범위**다. EC2에서 실제로 켜려면 품질검수
처럼 큐+워커로 재배선해야 한다 — 별도 후속 작업.

## 설계

### 1. 인터페이스 확장 — `comps.py`

`CompsSource.fetch()`가 텍스트 쿼리만 받았는데, CLIP 유사도 검색은 이미지가 필요하다.
ABC 시그니처를 키워드 인자로 확장했다: `fetch(self, query: str, *, image_url: str | None
= None) -> CompsFetch`. 기존 `MockCompsSource`/`LlmWebSearchCompsSource`는 시그니처에
`image_url`만 추가하고 무시한다 — `service.py` 호출부는 분기 없이 한 줄
(`fetch(query, image_url=request.image_url)`).

새 `InternalClipCompsSource(key="internal_clip")`: `image_url` 없으면
`reason=NO_IMAGE_PROVIDED`. 있으면 `clip_embed.embed_image_from_url()` → 임베딩 →
`internal_corpus.query_similar()`로 top-K 유사 코퍼스 항목 → `CompItem`으로 변환
(`source="internal_clip"`, `is_used=None` — AI-Hub 출처라 중고 여부 판별 불가).
`ClipEmbedNotReady`/`CorpusNotReady`는 `CompsUnavailable`로 승격한다.

### 2. 임베딩 모듈 — `app/pricing/clip_embed.py`

무거운 의존성(torch/transformers/httpx)은 함수 내부 지연 import — mock/llm_web_search만
쓸 땐 이 모듈이 로드돼도 아무 것도 안 당겨온다. 체크포인트 로딩은
`aihub_finetune_vit.py`의 `--init-checkpoint` 경로(`backbone_state_dict` +
shape 불일치 키 필터링)와 같은 판단을 복사했다(`validation/`을 프로덕션에서 import하지
않는 기존 규약 유지). `@lru_cache`로 프로세스당 1회 로드
(`worker/models/quality_vlm/loader.py`의 지연-싱글턴과 같은 철학).

### 3. 코퍼스 저장 — flat-file, pgvector 아님

`app/pricing/internal_corpus.py`가 `app/recommend/personalize/catalog.py`의
`get_catalog()` 패턴(`@lru_cache`로 `.npy`+`.json`을 프로세스당 1회 읽어 메모리 유지)을
그대로 따른다. **pgvector 대신 flat-file을 고른 이유**:

- `app/chat/rag_store.py`가 pgvector 테이블 패턴을 갖고 있지만, 코드베이스 전체에 `<=>`
  코사인 쿼리가 **단 한 줄도 없다**(작성만 되고 검색엔 안 쓰임, 테스트도 없음) — 전례
  없는 첫 벡터 쿼리를 "메커니즘 검증"이 목적인 이번 라운드에서 새로 떠안을 이유가 없다.
- `test_pricing_store.py`의 in-memory SQLite 테스트 트릭은 `Vector` 컬럼이 없어야
  성립한다 — pgvector 테이블을 추가하면 이 패턴이 깨지고, 대체할 라이브-Postgres 테스트
  전례가 이 저장소에 아직 없다.
- 합성 코퍼스는 크기가 통제되고(`--max-per-category`), 실데이터로 교체할 때도 시딩
  스크립트를 다시 돌려 파일을 갈아끼우면 되니 마이그레이션이 필요 없다.

파일은 `app/pricing/data/internal_clip_vectors.npy` + `internal_clip_meta.json` —
`embed_catalog.py` 산출물처럼 재생성 가능한 빌드 아티팩트라 커밋하지 않는다
(`.gitignore` 추가 완료).

### 4. 스키마 — `schemas.py`

`PricingRequest.image_url: str | None = None`(optional — mock/llm_web_search는 안 보내도
됨), `CompsSourceKey.internal_clip`, `ReasonCode.no_image_provided` 추가.

### 5. 레지스트리 — `registry.py`

`COMPS_BACKENDS["internal_clip"]` 추가(`min_comps_for_pricing=3`, `max_comps=8` — 코퍼스를
직접 통제하니 `llm_web_search`의 응급 최저치(1)보다 `mock` 수준 기준을 쓴다).
`ACTIVE_COMPS_SOURCE`는 `"mock"` 유지(`test_committed_defaults_are_mock`). 체크포인트
경로·코퍼스 경로·유사도 하한은 별도 `InternalClipConfig`/`INTERNAL_CLIP_CONFIG`로 분리.

### 6. 서비스 연결 — `service.py`

`estimate()`가 `image_url`을 `fetch()`로 전달. `_log_observation()` 스킵 조건을
`{"mock", "internal_clip"}`로 확장 — 합성 코퍼스 매치가 `pricing_search_observation`
(실제 GMS 관측 원장)에 섞이면 안 된다.

### 7. 코퍼스 시딩 스크립트

`AI/validation/CLASS/product-info-finetune/aihub_seed_pricing_corpus.py` — AI-Hub 카테고리
매핑(`aihub_dataset.py`)과 파인튜닝 체크포인트 둘 다 validation 도메인 자산이라 여기 둔다.
`aihub_finetune_vit.py`(체크포인트 로딩)·`aihub_embed.py`(이미지 경로 해석)를 재사용한다.
카테고리별 임의 기준가 + `MockCompsSource`와 같은 방식의 sha256 결정론적 가격 배정
(`hash()` 아님 — 재현 가능해야 함).

## 범위 밖(명시적으로 하지 않음)

- 실제 BE 상품 데이터 연동 — 이번 코퍼스는 100% `data_source="synthetic_aihub"`.
- CH016의 자동 외부-내부 hedge(매그니튜드 게이트·IQR 겹침·신뢰도 감쇠) — 이번엔 기존과
  같은 단순 수동 `ACTIVE_COMPS_SOURCE` 스왑만 한다.
- `internal_clip`의 EC2 프로덕션 배포 — torch 필요, 큐+워커 재배선은 별도 후속 작업.
- 코퍼스 아티팩트(`*.npy`/`*.json`) 커밋 — 로컬에서 시딩 스크립트를 한 번 돌려야 하는
  전제 조건으로 문서화만 한다.

## 검증

- CI 안전 범위(순수 로직 + monkeypatch): `internal_corpus.query_similar()`,
  `InternalClipCompsSource.fetch()`의 이미지 없음/로드 실패/매치 없음/정상 네 경로,
  `service.estimate()`가 `image_url`을 전달하는지, `aihub_seed_pricing_corpus.py`의
  `synthetic_price()` 결정론성 — 전부 torch 없이 통과해야 한다.
- torch/실제 임베딩 필요한 부분(CI 불가, `Qwen3VlDescriber`와 같은 성격의 부채): 실제
  체크포인트로 코퍼스 시딩 → `registry.ACTIVE_COMPS_SOURCE`를 로컬에서 임시로
  `"internal_clip"`으로 바꿔(커밋 금지) `PricingService.estimate()`를 이미지 URL 포함
  요청으로 직접 호출 → `priced=True` 확인.
