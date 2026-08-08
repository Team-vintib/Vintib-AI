# 042 시세 조회 — productId 포함 + matchKey 전달 + 동일 상품 시세 엔드포인트

- **요청자 파트**: BE (+ AI)
- **대상 파트**: FE

## 배경/이유

시세 조회를 외부 GMS 웹검색 대신 내부 데이터(상품명·브랜드·카테고리 텍스트 매칭)로 판정하는
작업(CH030, CH001)을 AI/BE 쪽에서 마쳤다. FE 쪽 두 가지가 반영돼야 실제로 동작한다.

## 요청 내용

1. **`estimateRegistrationPrice` 호출에 `productId` 포함**: 지금 `ProductAiPriceEstimateInput`
   (`productAiApi.ts`)이 `productName`/`category`/`brand`만 보내는데, AI의
   `POST /pricing/estimates`는 `product_id`가 필수다. 등록 흐름에서 이 시점엔 이미
   `draft.draftProductId`가 있으니(condition 스텝에서 생성됨) 그대로 실어 보내면 된다.
2. **폴링 결과의 `matchKey`를 상품 저장 시 전달**: `GET /ai/jobs/{jobId}` 폴링 응답
   (`PricingResult`)에 `product_match_key` 필드가 새로 생겼다. 이 값을 등록 제출 시
   `PATCH /products/{id}` 호출(`ProductUpdateRequest`)의 `matchKey` 필드로 같이 보내주면
   BE가 `product.match_key` 컬럼에 저장한다. 4개 등급(S/A/B/C) 호출 모두 같은
   `product_match_key`를 반환하니(등급과 무관하게 브랜드+제목+카테고리로만 계산됨) 아무
   응답에서나 가져다 쓰면 된다. **BE는 AI를 직접 호출하지 않는다** — 이 값의 유일한
   경로가 FE 경유다.
3. **신규 엔드포인트 `GET /api/products/{id}/market-price`**: 상품 상세 화면에 "동일 상품
   지금 얼마에 팔리는지"를 보여줄 수 있다. 기존 `ProductPriceDistribution.vue`("유사 상품
   가격대")와는 다른 데이터다 — 그쪽은 카테고리 기준 유사 상품, 이건 `matchKey` 기준 동일
   상품이다. 응답 형태:
   ```jsonc
   {
     "productId": 42,
     "matchKey": "1:501-리바이스:97",     // 아직 계산 전이면 null
     "currentProduct": { "productId": 42, "title": "...", "price": 45000, "priceKind": "ASKING" }, // null 가능
     "listings": [
       { "productId": 17, "title": "...", "price": 40000, "priceKind": "SOLD_DIRECT" },
       { "productId": 23, "title": "...", "price": 42000, "priceKind": "SOLD_AUCTION" }
     ]
   }
   ```
   `priceKind`: `ASKING`(호가) / `SOLD_DIRECT`(직접판매 완료) / `SOLD_AUCTION`(경매 낙찰).
   `matchKey`가 없거나 매칭되는 상품이 없으면 `listings`가 빈 배열로 온다(404 아님) — UI에서
   "아직 시세 정보 없음"으로 처리하면 된다.

## 관련 자료

- `docs/plans/AI/CH030-pricing-text-match.md`, `docs/plans/BE/CH001-pricing-same-product-match.md`
- `FE/src/domains/product/api/productAiApi.ts`(`ProductAiPriceEstimateInput`,
  `estimateRegistrationPrice`)
- `FE/src/domains/product/api/productApi.ts`(`submitProduct`, `ProductUpdateRequest`)
- `FE/src/domains/product/components/ProductPriceDistribution.vue`(기존 "유사 상품 가격대" —
  구분 참고용, 이번 요청과 별개)
- `BE/src/main/java/com/ssafy/backend/product/controller/ProductController.java`
  (`getMarketPrice`), `ProductResponse`/`ProductUpdateRequest`(`matchKey` 필드)
