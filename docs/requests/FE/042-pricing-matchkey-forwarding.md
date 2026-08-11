# 042 시세 조회 — 동일 상품 시세 엔드포인트 표시

- **요청자 파트**: BE (+ AI)
- **대상 파트**: FE

## 배경/이유

시세 조회를 외부 GMS 웹검색 대신 내부 데이터(상품명·브랜드·카테고리 텍스트 매칭)로 판정하는
작업(CH030, CH001)을 AI/BE 쪽에서 마쳤다. 이 중 `estimateRegistrationPrice` productId 포함,
matchKey 전달(원래 1·2번)은 FE `CH001-pricing-registration-real-connect.md`로 반영 완료돼
이 문서에서 정리했다. **남은 건 상품 상세 화면의 "동일 상품 시세" 표시뿐이다.**

## 요청 내용

**신규 엔드포인트 `GET /api/products/{id}/market-price`**: 상품 상세 화면에 "동일 상품
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
- `docs/plans/FE/CH001-pricing-registration-real-connect.md`(반영 완료된 1·2번)
- `FE/src/domains/product/components/ProductPriceDistribution.vue`(기존 "유사 상품 가격대" —
  구분 참고용, 이번 요청과 별개)
- `BE/src/main/java/com/ssafy/backend/product/controller/ProductController.java`
  (`getMarketPrice`), `ProductResponse`/`ProductUpdateRequest`(`matchKey` 필드)
