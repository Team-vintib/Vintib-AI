# 047 시세 조회 — "동일 상품" 텍스트 매칭에 필요한 BE 확장 3가지

- **요청자 파트**: AI
- **대상 파트**: BE

## 배경/이유

시세 조회(`AI/app/pricing/`)를 외부 GMS 웹검색 대신 내부 데이터로 판정하는 작업(CH030,
`docs/plans/AI/CH030-pricing-text-match.md`)을 진행 중입니다. `docs/requests/BE/
025-product-same-price-chart.md`(FE→BE, "같은 상품 판정 기준은 BE가 정함", 아직 미답변)와
같은 문제를 다루는데, 이번엔 AI가 상품명·브랜드·카테고리 텍스트만으로 "동일 상품" 판정
기준(`match_key`)을 직접 만들어 넘기는 쪽으로 설계했습니다 — 025가 BE에 미뤄둔 판정 로직을
AI가 대신 만든 셈입니다. 이미지 임베딩은 쓰지 않습니다(CH024의 `internal` 백엔드와는 다른
축이며, 그건 그대로 둡니다).

AI 쪽 매칭 로직·자체 코퍼스(`app/pricing/product_match.py`, `app/pricing/product_corpus.py`)는
이미 구현했고, 기존 공개 API(`GET /api/products`, `GET /api/brands`)만으로 동작합니다 — **새
검색 API는 필요 없습니다.** 다만 아래 3가지는 AI가 자체 해결할 수 없어 BE 작업이 필요합니다.

## 요청 내용

1. **`GET /api/products` 응답에 완료거래가 노출**: 지금 `price` 필드는 호가(광고가)뿐이라
   `SOLD` 상품의 실제 거래가를 알 수 없습니다. 아래 두 필드 추가를 요청합니다.
   - `finalPrice`: `SOLD`면 직접판매는 `orders.order_price`, 경매낙찰은 `auction.final_price`.
     아니면 `null`.
   - `priceKind`: `"ASKING"`(`ON_SALE`) / `"SOLD_DIRECT"` / `"SOLD_AUCTION"` — 호가와
     완료거래를 화면에서 구분해 보여주기 위한 태그입니다(사용자 결정: 완료거래 실데이터가
     당장 거의 없어 호가도 같이 노출).
2. **`product` 테이블에 `match_key` 컬럼 추가** (nullable 문자열): 값의 출처는 AI가 아니라
   **FE**입니다 — `044`(가격 추정 트리거)와 같은 구조로, FE가 등록 마지막(가격) 스텝에서
   `GET /ai/jobs/{job_id}`를 직접 폴링해 `PricingResult.product_match_key`를 이미 받아둔
   상태입니다. BE가 AI 응답을 직접 조회할 필요 없이, **FE가 상품 등록/수정 API 호출 시
   `matchKey` 필드로 같이 보내는 값을 그대로 이 컬럼에 저장**해주시면 됩니다(FE와 그 필드명
   협의 필요). AI가 두 번 계산하지 않고 가격 책정 시점에 한 번 계산한 값을 그대로
   재사용하는 구조입니다.
3. **구매자 상세 화면의 "동일 상품 시세"를 `match_key` 기준 DB 쿼리로 구현**: 025가
   요청한 "같은 상품 지금 시세" 데이터를, AI 호출 없이 `SELECT ... FROM product WHERE
   match_key = :key AND sale_status IN ('ON_SALE', 'SOLD')` 형태의 순수 DB 쿼리로 제공할
   수 있습니다 — RAG/AI가 매 조회마다 개입하지 않습니다. 025는 이 문서로 답이 된 것으로
   보셔도 됩니다(엔드포인트 이름·응답 형태는 025 그대로 `GET /api/products/{id}/
   market-price` 등 BE 판단).

## 참고

- 기존 상품(등록 시점에 `match_key`가 없던 상품)은 이번 요청 범위 밖입니다 — 필요하면
  별도 백필 작업으로 논의해주세요.
- `043`/`044`(FE, 등록 화면 "AI 가격 추천")는 이 요청과 별개로 이미 외부 시세 추정으로
  당장 채워지는 경로라 이 문서와 충돌하지 않습니다.

## 관련 자료

- `docs/plans/AI/CH030-pricing-text-match.md` (이번 설계 전체)
- `docs/plans/AI/CH016-internal-comps-hedge.md`, `docs/plans/AI/CH024-classifier-pricing-real-integration.md`
- `docs/requests/BE/025-product-same-price-chart.md` (이 문서로 답변)
- `docs/requests/BE/044-pricing-estimate-trigger.md` (FE가 `GET /ai/jobs/{job_id}`를 직접
  폴링하는 것과 같은 패턴 — `match_key`도 같은 경로로 FE가 받아 BE에 전달)
- `AI/app/pricing/product_match.py`, `AI/app/pricing/product_corpus.py`, `AI/app/pricing/comps.py`(`InternalTextCompsSource`)
