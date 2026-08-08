# CH024 — 상품분류→가격책정 파이프라인, 실제 서버 흐름 연동 (설계 v2)

> 대상 티켓: 에픽 `S15P11A108-211 [PROD] 상품 등록·판매` 계열. 관련 스토리:
> `-338`(가격 책정 프로토타입) / `-494`(가격 검색 로직 고도화). `product_classifier`는 `CH012`.
>
> 선행: `CH012`(분류 파이프라인 설계) / `CH016`(내부 호가 매칭+헷지, DB 실데이터 0건이라 보류) /
> `CH020`(CLIP 유사도, 합성 코퍼스로 메커니즘만 검증) / `docs/requests/BE/034`(BE 회신 완료)
>
> 산출 범위: **설계 + 구현 완료(§6 1~7번).** §6 8번(시드 백필 실행)만 사용자 로컬 환경 필요.
>
> **구현 완료 상태(2026-08-07)** — §5 Q4/Q5/Q6 확인 후 §6 작업 순서 1~7번을 구현했다:
> `app/shared/be_client.py`(신규), `app/pricing/hedge.py`(신규), `app/pricing/comps.py`의
> `InternalCompsSource`(신규, `key="internal"`), `CompsSource.fetch()`에 `product_id` 파라미터
> 추가(`service.py` 배선 포함), `registry.py`에 `internal` 백엔드 등록(`ACTIVE_COMPS_SOURCE`는
> `mock` 유지), `app/gateway/router.py::_ingest_quality_embedding_result`의 category 불일치
> 수정(Q4), `scripts/backfill_garment_embeddings.py`도 같은 방식(BE categoryId 그대로)으로
> 통일. `ruff check . && black --check . && pytest -q` 전부 통과(1142 passed, 25 skipped).
> 남은 건 §6 8번(사용자가 로컬 torch/SAM3 환경에서 백필 스크립트 실행)뿐 — 이 세션 환경엔
> Python/torch 자체가 없어(§5 Q6) 실행 불가 확인함.
>
> **v2 변경 이유** — v1(§1~§7 초안)을 사용자에게 확인받는 과정에서, 이 저장소에 **이미 실제로
> 동작하는 실데이터 임베딩 파이프라인이 있다**는 사실이 드러났다(`app/recommend/similar/`,
> §2). v1은 CH016의 "DB 뷰 + 텍스트 매칭"만 보고 있었는데, 그 인프라를 그대로 재사용하면
> DB 뷰·읽기 전용 계정 없이도, 그리고 텍스트 매칭에 크게 투자하지 않고도 실데이터 기반 시세
> 비교를 이번 라운드에 완성할 수 있다는 게 확인됐다. 이 문서는 그 방향으로 전면 다시 쓴 것이다.

---

## 1. v1에서 확인한 것 (요약, 그대로 유효)

- `product_classifier`: 카테고리·색상 둘 다 mock뿐, 실백엔드 없음 — 이번 라운드 범위 아님.
- BE는 `product_classifier`/`pricing`/`quality` 셋 다 아직 실제 등록 흐름에서 호출하지
  않는다(`docs/requests/BE/041`, `002` 확인). BE 연동 자체는 AI 권한 밖.
- `product_classifier`(35종 Subcategory)와 `pricing.category`(6종 `GarmentCategory`)는
  다른 체계 — 직접 체이닝 불가, BE 폼이 중개하는 구조 그대로 둔다.
- `clip_embed.py` transformers 언랩 버그 수정은 이미 현재 브랜치에 머지돼 있음(할 일 없음).
- BE 뷰 + 읽기 전용 DB 계정은 여전히 프로비저닝 안 됨 — **하지만 §2가 이걸 우회한다.**

## 2. 새로 발견한 것 — 실데이터 CLIP 임베딩 파이프라인이 이미 살아 있다

`app/recommend/similar/`(유사 상품 추천, 지라 -193)를 위해 만들어진 인프라인데, 코드를 따라가
보니 **가격책정이 필요로 하는 것과 거의 똑같다.**

```
실제 품질검수 job (BE가 호출하면)
  → worker/quality_check_worker_example.py
      SAM3로 의류 크롭 → zero-shot fashion-clip(`sam3/garment_embedding.py`)로 임베딩
      → job result에 garment_embedding 실어 제출
  → app/gateway/router.py::_ingest_quality_embedding_result()
      임베딩이 있으면 조용히 pgvector에 upsert (실패해도 검수 job은 성공 처리)
  → app/recommend/personalize/embedding_store.py::ProductGarmentEmbedding
      (product_id UNIQUE, 상품당 최신 임베딩 1개, pgvector 코사인 검색)
```

그리고 **기존 상품(BE 시드 60건 포함) 백필 스크립트도 이미 있다** —
`AI/scripts/backfill_garment_embeddings.py`. 이 스크립트는:

- BE **DB가 아니라 공개 REST API**(`GET /api/products`, `GET /api/products/{id}`)로 실제
  상품 목록·이미지 URL을 가져온다 — **CH016이 막혀 있던 DB 뷰/읽기 전용 계정이 전혀 필요
  없다.**
- 같은 SAM3 크롭 + zero-shot CLIP 함수(`embed_garment()`)로 임베딩을 계산해 같은 pgvector
  테이블에 저장한다 — 신규 등록 상품이 겪는 경로와 **완전히 동일한 코드 경로**다.
- 로컬(torch/SAM3 있는 환경)에서 한 번 돌리면 끝나는 1회성 스크립트다.

**즉 사용자가 물었던 "시드 이미지를 임베딩해서 저장 → 그 뒤로는 등록 파이프라인이 알아서
쌓이게"는 이미 100% 구현돼 있다** — 시드는 백필 스크립트를 실행하면 되고, 이후 축적은
BE가 `/quality/inspections`를 실제로 호출하기 시작하는 순간 게이트웨이가 자동으로 처리한다
(추가 AI 코드 불필요).

또한 `GET /api/products/{id}`(`BE/.../ProductResponse.java` 확인)는 `brandId`/`title`/
`conditionGrade`/`saleType`/`saleStatus`/`price`/`createdAt`을 **이미 전부 응답으로 낸다**
— CH016 §3.1이 BE에 뷰로 요청했던 컬럼과 사실상 같은 목록이다. **DB 뷰 없이 공개 API로
같은 정보를 얻을 수 있다.**

### 2.1 다만 그대로 재사용은 안 되고 확장이 필요한 지점

- `embedding_store.find_similar(product_id, k)`는 **이미 임베딩이 저장된 상품**을 기준으로만
  검색한다(자기 임베딩을 자기 product_id로 먼저 조회). 가격책정 쪽은 "이 상품과 비슷한 걸
  찾아 가격을 매기는" 것이므로 이 함수를 그대로 쓸 수 있다 — **단, 가격을 매기려는 상품
  자신도 먼저 임베딩이 있어야 한다.** 이건 등록 흐름상 자연스럽다(품질검수가 가격책정보다
  먼저 끝나도록 CH012가 이미 설계해 뒀다 — 가격책정은 품질검수 결과값을 요청으로 받는
  구조다, `app/pricing/schemas.py`).
- `embedding_store`에는 가격·브랜드·판매상태가 없다(product_id + 임베딩 + category만). 후보
  product_id들의 실제 가격 비교 데이터는 BE 공개 API로 **추가 조회**해야 한다 — 새 경량
  클라이언트가 필요하다(`app/pricing/`에, `backfill_garment_embeddings.py`의
  `fetch_product_detail()`과 같은 방식, httpx만 사용).
- **`category` 필드 저장 방식이 두 경로에서 다르다(기존 버그, 이번에 발견)** —
  `_ingest_quality_embedding_result()`(실사용 경로)는 `garment_category`를 그대로 저장하는데
  이건 품질검수의 `GarmentCategory`(6종)다. 반면 `backfill_garment_embeddings.py`는
  `subcategory_value(category_id)`로 **`product_classifier`의 `Subcategory`(35종)** 문자열을
  저장한다. 같은 컬럼에 서로 다른 체계의 문자열이 섞여 있다는 뜻 — `category` 필터를 걸면
  두 출처가 서로 매치되지 않는다. 지금까지는 `find_similar(category=...)`를 실제로 호출하는
  곳이 없어서 드러나지 않았다. **이번 작업이 이 컬럼을 실제로 필터링에 쓰기 시작하면 문제가
  된다** — §5-Q4로 남긴다(고칠지, 이번엔 category 필터 없이 갈지).
- 가격책정 게이트웨이 컨테이너에는 torch가 없다(`docs/infra-architecture.md` §6, CH020이
  이미 명시). **쿼리 임베딩을 요청 시점에 새로 계산하지 않는다** — `product_id`로 이미 저장된
  임베딩을 조회하는 경로만 쓴다. 대상 상품에 임베딩이 아직 없으면(품질검수 미완료·워커가
  mock·옷 미검출) `internal` 백엔드는 `CompsUnavailable`이 아니라 **정상적인 빈 결과**로
  처리한다(`app/recommend/similar/service.py`가 "임베딩 없으면 `items=[]`, 에러 아님"으로
  다루는 것과 같은 원칙) — `reason_code`는 기존 `NO_IMAGE_PROVIDED`를 재사용하거나 새 코드가
  필요하다(§5-Q5).

## 3. 이번 라운드 스코프 (v1 대비 변경)

### 3.1 한다

- **시드 백필 실행** — `AI/scripts/backfill_garment_embeddings.py`를 로컬(torch/SAM3
  환경)에서 실제로 돌려 BE 시드 60건(그중 이미지 있는 것)의 임베딩을 `product_garment_embedding`
  에 채운다. **새 코드 없음, 기존 스크립트 실행뿐** — 다만 이건 실제 추론 실행이라
  `AI/CLAUDE.md` 하드 룰 대상은 아니지만(GMS 아님, torch 로컬 실행이라 과금 없음)
  **사용자가 직접 실행하는 편이 낫다**(로컬 GPU/torch 환경이 있는 쪽이 사용자 환경이라서 —
  이 세션 환경에 torch가 있는지도 확인 안 됨). AI는 스크립트가 이미 있다는 것만 확인하고,
  필요하면 스크립트를 조금 고친다(§3.2).
- `app/pricing/be_client.py`(신규, 이름 가안) — BE 공개 API(`GET /api/products/{id}`)로
  후보 상품의 가격·브랜드·판매상태·등록일시를 가져오는 경량 httpx 클라이언트.
  `backfill_garment_embeddings.py::fetch_product_detail()`과 같은 패턴, 실패 시 예외를
  던지지 않고 스킵(comps 소스이므로 `RetailSource`처럼 관대하게).
- `app/pricing/comps.py`에 `InternalCompsSource`(신규 백엔드 키, 예: `internal`) 추가:
  1. `product_id`로 `embedding_store.fetch_garment_embedding()` 조회 → 없으면 빈 결과
     (§5-Q5의 reason_code)
  2. 있으면 `embedding_store.find_similar(product_id, k)`로 코사인 top-K 후보 조회
  3. 후보 product_id들을 `be_client`로 조회 → `sale_type=DIRECT_SALE` 필터(CH016 §3.3) →
     `CompItem`으로 정규화
  4. CH016 §3.3(판매상태·최신성 가중) + §3.4~3.6(자릿수 게이트·구간 겹침·앵커 clamp·격리)을
     `app/pricing/hedge.py`(신규, 순수 함수)로 적용
- **`CompsSource.fetch()` 시그니처 확장** — `product_id: int | None = None` 추가 필요
  (`image_url`처럼 기존 mock/llm_web_search는 무시). `service.py`가 `request.product_id`를
  넘기도록 한 줄 수정.
- `app/pricing/registry.py`에 `internal` 백엔드 설정 추가. **`ACTIVE_COMPS_SOURCE`는 `mock`
  유지** — 스왑은 별도 승인(사용자 확정 사항).
- 테스트: `hedge.py`(순수 함수, 자릿수 게이트·겹침·clamp 경계) + `InternalCompsSource`를
  `embedding_store`/`be_client`를 monkeypatch해 CI에서 DB·네트워크 없이 검증
  (`test/pricing/test_pricing_comps.py`의 기존 관례 그대로).

### 3.2 CH020(합성 코퍼스) 처리

`internal_clip`(AI-Hub 합성 코퍼스, `clip_embed.py`+`internal_corpus.py`)은 **건드리지
않는다** — 별도 백엔드 키로 그대로 남긴다. 이번에 추가하는 `internal`은 실데이터용 새
백엔드다. 코드 삭제·통합은 이번 범위 밖(원하면 나중에 `internal_clip`을 폐기하고 `internal`로
일원화하는 정리 작업을 별도로 한다).

### 3.3 CH016의 텍스트 매칭(`matching.py`, 브랜드+모델번호)은 이번 라운드에서 최소화한다

이미지 임베딩(§2) + BE API의 `brandId` 정확 매칭만으로도 "같은 브랜드의 시각적으로 가장
비슷한 상품"까지는 잡힌다. 모델번호/품번 텍스트 파싱(CH016 §3.2)은 "완전히 동일한 품목"까지
좁히는 정밀도 향상 기법인데, 실제 BE 시드 타이틀을 보면(`"Maison Margiela 18FW PVC 패치
데님팬츠"`, `"리메이크 Levi's 데님"`) 표준화된 품번이 드물어 투자 대비 효과가 낮아 보인다.
→ **이번 라운드는 `brand_id` 정확매칭 + 이미지 유사도만 쓰고, `title` 파싱은 하지 않는다.**
정확도가 부족하면 다음 라운드에서 추가한다(CH016 §3.2 그대로 백로그에 남긴다).

## 4. 하지 않는 것 (v1과 동일)

- BE/FE 코드 수정, BE 뷰/읽기 전용 계정 재요청(이번엔 필요 자체가 없어짐)
- `ACTIVE_COMPS_SOURCE`/`ACTIVE_RETAIL_SOURCE` 기본값 전환, GMS/naver 실행
- `product_classifier` 실백엔드 구현
- `product_garment_embedding.category` 두 체계 불일치(§2.1) 수정 — Q4 결정 후 별도 처리

## 5. 사용자 결정 (확인 완료)

- **Q4 (category 불일치)** — *"BE(Spring Boot) 팀이 지정한 거에 맞춰야 해"* → 기준은
  **BE의 실제 `categoryId`다.** 백필 스크립트(`subcategory_value(category_id)`, BE
  categoryId를 `product_classifier.taxonomy`로 역산)가 맞는 쪽이고, 실사용 경로
  (`app/gateway/router.py::_ingest_quality_embedding_result`가 품질검수 자신의
  `GarmentCategory`를 저장하는 것)가 틀린 쪽이다 — 이건 BE 카테고리 체계가 아니라 SAM3
  하자-탐지 프롬프트 선택용 AI 내부 값이라 BE 지정과 무관하다. **이번 라운드에서 함께
  고친다**: 실사용 경로도 `product_id`로 BE 공개 API(`GET /api/products/{id}`)의
  `categoryId`를 조회해 같은 방식으로 역산한 값을 저장하도록 바꾼다. `categoryId` 역산
  로직(`_ID_TO_SUBCATEGORY_VALUE`)은 지금 백필 스크립트에만 있는데, 배포 이미지(`app/`)는
  `worker/models/`를 import할 수 없으므로(`AI/CLAUDE.md`: 추론 코드는 `AI/`에 두지 않는다,
  배포 이미지에 `worker/`가 없다) `app/pricing/schemas.py`가 `app/quality/schemas.py`의
  enum을 재선언하는 것과 같은 방식으로 **작은 역산 표만 `app/` 쪽에 값 복제**한다.
- **Q5 (임베딩 없음 reason_code)** — 기존 `ReasonCode.no_image_provided` 재사용. BE
  계약(enum) 변경 없음.
- **Q6 (백필 실행 환경)** — 이 세션 환경 확인 결과 **torch/SAM3 실행 불가**(Python 자체가
  없음 — Windows Store 스텁만 있고 venv도 없음). **백필 스크립트 실행은 사용자가 로컬
  GPU/torch 환경에서 직접 진행**한다. 이 라운드는 백필 스크립트 자체를 고치지 않으므로
  (§3.1에 이미 "새 코드 없음, 기존 스크립트 실행뿐"로 명시) 실행 시점은 사용자 재량이고,
  아래 작업 순서 중 코드 작업(2~7번)은 백필 완료 여부와 무관하게 먼저 진행 가능하다 —
  `InternalCompsSource`는 임베딩이 아직 없는 상품에 대해 `NO_IMAGE_PROVIDED`로 정상
  동작해야 하므로(Q5) 백필 전에도 테스트 가능하다.

## 6. 작업 순서

1. `app/gateway/router.py::_ingest_quality_embedding_result` — BE `categoryId` 조회 후
   역산해 저장하도록 수정(Q4). 역산 표는 `app/` 쪽에 값 복제.
2. `app/pricing/be_client.py` — BE 공개 API 클라이언트 (httpx, 예외 삼킴, `categoryId`
   조회도 1번이 재사용)
3. `app/pricing/hedge.py` — 자릿수 게이트·겹침·감쇠·앵커 clamp (순수 함수) + 테스트
4. `comps.py`의 `CompsSource.fetch()`에 `product_id` 파라미터 추가, `service.py` 배선
5. `comps.py`에 `InternalCompsSource` 추가 (embedding_store 조회 → be_client 조회 →
   hedge 적용) + 테스트(monkeypatch)
6. `registry.py`에 `internal` 백엔드 등록 (`ACTIVE_COMPS_SOURCE`는 `mock` 유지)
7. `ruff check . && black --check . && pytest -q`
8. (사용자) 로컬 torch/SAM3 환경에서 `backfill_garment_embeddings.py` 실행 — 시드 임베딩
   확보. 코드 작업과 독립적으로 아무 때나 진행 가능.
9. 필요 시 `docs/requests/BE/034` 갱신(진행 상황 반영, 뷰/계정 요청 철회 — 공개 API로
   충분해짐)

## 7. 참고

- `app/recommend/personalize/embedding_store.py`, `app/recommend/similar/` — 재사용하는
  실데이터 임베딩 인프라
- `worker/models/sam3/garment_embedding.py`, `worker/quality_check_worker_example.py`,
  `app/gateway/router.py::_ingest_quality_embedding_result` — 임베딩 계산·자동 적재 경로
- `AI/scripts/backfill_garment_embeddings.py` — 시드 백필 스크립트(기존)
- `BE/src/main/java/.../product/dto/response/ProductResponse.java` — 공개 API 응답 필드
- `docs/plans/AI/CH016-internal-comps-hedge.md` — 헷지 로직(§3.3~3.6) 원본
- `docs/plans/AI/CH020-internal-clip-price-comps.md` — 합성 코퍼스 버전(그대로 유지)
