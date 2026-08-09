# CH034 유사 상품 추천 — AI 구현 현황 정리 + BE 통합 계약 설계

## 배경/목표

"유사 상품 추천 로직 점검 + FashionCLIP 이미지 임베딩 기반 설계" 요청으로 AI/BE/FE 전체를
조사한 결과, **AI 쪽 파이프라인은 이미 다 구현돼 있었다**(이번 세션 이전에 품질검수 임베딩
작업의 일부로 만들어졌고, `docs/plans/AI/`에 정식 계획 문서로 남지 않은 채였다). 이 문서는
①기존 구현 현황을 뒤늦게 문서화하고 ②BE가 이걸 실제로 붙일 때 따라야 할 통합 계약을
정의한다.

**v2 개정 — 동기 호출 대신 배치 사전계산 + BE DB 캐시로 확정.** 상품 상세 페이지가 AI 서버
성능/가동 여부에 전혀 영향받지 않아야 한다는 요구사항에 따라, BE가 매 요청마다 AI를 부르는
대신 **주기적 배치가 결과를 BE 자체 테이블에 미리 채워두고, 서빙은 그 캐시만 읽는다.**
AI측 코드 변경은 하나 있다 — 임베딩 백필 스크립트를 주기 실행에 맞게 최적화(아래 참고).

관련: `docs/requests/BE/006-be-request-index.md`의 "2026-08-06 정리 (023 삭제)" 항목 —
"AI가 유사 판정 자체를 맡는다"까지는 이미 결정됐고, 통합 방식만 "별도 논의"로 남아 있던 것을
이번에 정한다.

## 기존 구현 (AI, 이미 완료)

- **임베딩 계산**: `worker/models/sam3/garment_embedding.py` — zero-shot
  `patrickjohncyh/fashion-clip`(파인튜닝 안 함 — 실측상 파인튜닝이 카테고리 간 유사도를
  오히려 파괴함, intra/inter-category cosine gap 0.066→0.553). SAM3가 품질검수용으로 이미
  만든 배경 제거 크롭을 그대로 재사용, 512차원 L2 정규화 벡터.
- **주입 경로**: `worker/quality_check_worker_example.py`가 품질검수 job 처리 중 임베딩도
  같이 계산해 결과에 실어 보냄 → `app/gateway/router.py::_ingest_quality_embedding_result()`가
  pgvector에 저장(카테고리는 BE의 실제 categoryId를 `_resolve_be_category()`로 조회해서 씀).
- **저장**: `app/recommend/personalize/embedding_store.py` — `product_garment_embedding`
  테이블(pgvector, 512차원), 상품당 최신 임베딩 1개만 유지(upsert). `find_similar()`가
  코사인 거리(`<=>`) 조회, 자기 자신 제외, `category` 파라미터로 후보 좁히기 지원.
- **서빙**: `app/recommend/similar/{router,service,schemas}.py` —
  `GET /recommend/products/{id}/similar?k=&category=`. 응답은 `{product_id, items:
  [{product_id, score}]}`뿐 — 카드 메타(제목/가격/썸네일)는 의도적으로 안 채운다(BE가 그
  id로 채우는 걸 전제로 설계됨, `schemas.py` 주석 참고).

## 확인된 한계 (코드 버그 아님, 통합 설계에 반영해야 하는 것들)

1. **판매상태 필터가 없다** — `find_similar()`는 `product_garment_embedding`에 있는 모든
   상품을 후보로 본다. 이 테이블엔 판매상태(DRAFT/SOLD 등)가 없다 — AI는 그 데이터를
   갖고 있지 않다. **BE가 AI 응답을 받은 뒤 필터링해야 한다.**
2. **임베딩 커버리지가 들쭉날쭉하다** — `worker/`는 배포된 서비스가 아니라 팀원이 개인 GPU
   노트북에서 수동으로 돌리는 스크립트(`AI/docs/infra-architecture.md` §3.2/§6). 품질검수가
   그 워커가 켜져 있을 때 처리된 상품만 임베딩이 생긴다. 대상 상품에 임베딩이 없으면
   `items=[]`(에러 아님, 정상 응답) — **BE는 이 경우를 대비한 폴백이 필요하다.**
   기존(시드) 상품처럼 품질검수 큐를 거치지 않은 데이터는 `AI/scripts/backfill_garment_embeddings.py`
   (이미 구현·테스트됨, `--dry-run` 지원)로 한 번 채울 수 있다 — BE 상품 목록을 페이지네이션해
   가져와 SAM3+zero-shot CLIP으로 동일하게 임베딩해 pgvector에 저장한다. torch/SAM3 의존성이
   있는 환경(로컬 GPU)에서 사용자가 직접 실행해야 한다.
3. ~~동기 호출 전제~~ **(v2에서 폐기)** — 처음엔 pgvector 조회 한 번뿐이라 지연이 크지
   않으니 BE가 매 요청마다 동기 호출해도 된다고 봤다. 하지만 "AI 서버 성능이 안 좋거나
   워커가 안 돌아도 상품 상세 페이지는 영향받으면 안 된다"는 요구사항이 나와서, **서빙
   경로에서 AI 호출을 아예 없앤다** — 아래 v2 아키텍처 참고.

## v2 — 배치 사전계산 + BE DB 캐시 아키텍처

**핵심: 상품 상세 조회(서빙 경로)는 AI를 절대 호출하지 않는다.** 대신 주기적 배치가 결과를
BE 자체 테이블에 미리 채워두고, 서빙은 그 캐시만 읽는다.

1. **신규 엔드포인트**: BE `GET /api/products/{id}/similar`(가칭) — DB 캐시 기반, 카드
   전체 메타(제목/가격/브랜드/썸네일/등급/판매유형 등) 포함해서 응답. FE 캐러셀이 그대로
   쓸 수 있는 형태로 BE가 설계.
2. **배치(BE 스케줄러, 주기는 BE 재량 — 야간 권장)**: 노출 대상 상품별로 AI
   `GET /recommend/products/{id}/similar?k=20`을 호출해 결과를 BE 자체 캐시 테이블에
   upsert(이전 값 대체). `k=20`을 권장하는 이유 — 기존 SQL 폴백 상한
   (`ProductService.SIMILAR_PRODUCT_LIMIT=20`)과 맞춘 것이고, pgvector 조회 하나라 20개
   요청해도 비용 차이가 거의 없다(배치라 지연시간도 문제 안 됨). 서빙 시점에 판매상태
   필터링으로 줄어들 걸 감안한 여유분이기도 하다.
3. **서빙 로직**: 캐시 테이블에서 후보를 점수순으로 읽고, **그 자리에서 실시간 판매상태
   필터링**(배치 계산 이후 품절된 상품 배제) → 남은 개수가 **2개 이하면 캐시를 버리고
   기존 `findSimilarProducts` SQL로 전체 폴백** → 3개 이상이면 부족분만 SQL로 보충(dedup)
   → 목표는 캐러셀 한 슬라이드(5개) 기준 **4~5개 확보**.
4. **임베딩 커버리지**: 신규 등록 상품은 품질검수 워커가 켜져 있으면 실시간으로 임베딩이
   채워진다. 워커가 그 시점에 안 돌고 있었던 상품은 `backfill_garment_embeddings.py`를
   주기적으로(예: 매일 밤, GPU 있는 환경에서) 돌려서 채운다 — 이 스크립트를 반복 실행할
   전제라 아래 AI측 구현이 필요하다.
5. 이 구조에서 AI 서버가 죽어 있거나 느려도 **상품 상세 페이지는 전혀 영향받지 않는다**
   (배치가 그 사이 실패하면 다음 배치 때 재시도, 서빙은 항상 캐시+SQL 폴백만 봄).

## AI측 신규 구현

- `AI/scripts/backfill_garment_embeddings.py`가 지금은 대상 상품 전체를 매번 재처리한다
  (`eligible_products()`가 판매상태만 거르고 이미 임베딩 있는지는 안 본다). 주기 실행
  전제가 되면 이미 처리된 상품까지 매번 GPU로 재추론하는 낭비가 생긴다 — **이미
  `product_garment_embedding`에 있는 상품은 기본적으로 스킵**하고, 강제 재처리가 필요하면
  `--force` 플래그로 켤 수 있게 한다.

## 구현 목록

- [x] 기존 AI 구현 현황 문서화(이 파일)
- [x] 한계 정리(판매상태 필터 부재/커버리지) + 동기 호출 전제 폐기
- [x] v2 배치+캐시 아키텍처 확정(k=20, 폴백 기준 2개 이하 전체폴백, 목표 4~5개)
- [x] BE 통합 계약을 `docs/requests/BE/042-similar-product-recommendation-integration.md`에
      v2로 재작성
- [x] `backfill_garment_embeddings.py`에 "이미 임베딩 있으면 스킵" 옵션 추가(+ `--force`)
      + 테스트 갱신, `ruff`/`black`/`pytest` 전부 통과 확인

## BE 구현 (2026-08-09, 사용자 승인 하에 이 세션에서 예외적으로 직접 진행)

CLAUDE.md의 파트 분리 규율(AI가 BE 코드를 직접 수정하지 않는다)에 대한 예외로, 사용자
승인을 받아 이 세션에서 BE 쪽까지 구현했다. 완료 항목:

- [x] `AiClient.getSimilarProducts()` + `SimilarProductAiResponse` DTO
- [x] `SimilarProductCandidate` 엔티티 + `SimilarProductCandidateRepository`(캐시 테이블)
- [x] `SimilarProductCacheService`(배치 갱신, AI 실패 시 예외 없이 로그만) +
      `SimilarProductCacheScheduler`(매일 새벽 3시 cron)
- [x] `SimilarProductQueryService`(서빙 — 캐시 읽기 → 실시간 판매상태 필터 → 2개 이하 전체
      SQL 폴백 / 그 이상은 슬라이드 목표 5개까지 SQL 보충) + `GET /api/products/{id}/similar`
- [x] 단위 테스트 10건(캐시 서비스/스케줄러/서빙 로직) + `./gradlew compileJava`/`test` 확인
      (통합 테스트 176건은 이 환경에 Postgres가 없어 실패 — 기존에도 동일했던 환경 한계,
      이번 변경과 무관함을 개별 확인함)
- [x] `docs/requests/BE/042-...md` 반영 완료로 삭제, `006-be-request-index.md`에 기록

## FE 구현 (2026-08-09, 사용자 승인 하에 이 세션에서 예외적으로 직접 진행)

- [x] `productApi.ts::getSimilarProducts()` — `GET /products/{id}/similar` 실연동으로 교체.
      `categoryId`/`brand` 파라미터 제거(BE가 상품 자신의 값으로 알아서 판단하니 FE가 몰라도
      됨), 클라이언트 정렬 로직도 제거(BE가 이미 유사도 순으로 정렬해 옴).
- [x] `ProductSimilarRecommendation.vue` — `categoryId`/`brand` props 제거, `productId`만 받음.
- [x] `ProductDetailView.vue` — 호출부에서 제거된 props 전달 정리.
- [x] `npm run type-check`/`npm run lint` 통과 확인.
- FE 유닛 테스트는 이 리포에 아직 관례가 없어(전체 0건) 추가하지 않음 — 기존 관례 그대로.
- 실제 브라우저 클릭스루는 이 환경에 BE/AI 전체 스택(Postgres 등)이 떠 있지 않아 못 함 —
  type-check/lint만 확인됨. 실제 렌더링 확인은 배포 환경에서 필요.

## 확인이 필요한 미결정 사항

- 캐시 테이블 스키마는 정규화 테이블(product_id, similar_product_id, score, rank)로 구현—
  필요시 BE가 나중에 재검토 가능.
- 캐시 배치 수동 트리거(당일 시연용) 필요 여부는 사용자 확인 대기 중.
- FE `toProductListItem()`의 브랜드 매핑(`product.brandName`/`brandId`)이 BE의 현재 응답
  필드(`brand: string`, c07ed500 이후)와 안 맞아 브랜드가 항상 빈 값으로 보이는 기존 버그를
  발견함(이번 작업 범위 밖, 이 유사 상품 카드에도 그대로 영향 — 별도로 다룰지 확인 필요).
