# SY042 상품 상세 "동일 상품" 시세 데이터 (PROD-006/PROD-010)

## 배경/목표

`docs/requests/BE/025-product-same-price-chart.md`. 상품 상세 가격 그래프를 "유사 상품 가격대"
(카테고리+브랜드 기준, `similarProducts` — SY038에서 이미 반영 완료)에서 KREAM처럼 **"같은 상품이
지금 얼마에 팔리고 있는지"**로 바꾸려 한다. "유사 상품" 목록 자체는 이미 있으므로, 이번에 새로
만들 것은 **동일 상품 판정 + 그 시세 데이터**뿐이다.

## 작업 내용

### 동일 상품 판정 기준 (BE 결정)

카탈로그 개념이 없는 C2C 등록이라 상품마다 "모델 ID" 같은 고유 식별자가 없다. 현재 스키마에서
가장 신뢰할 수 있는 조합은 **`brandId` 일치 + `title` 정규화 일치**(trim, 연속 공백 축소, 대소문자
무시)다 — 같은 판매자든 다른 판매자든 "브랜드명 + 정확히 같은 상품명"으로 올렸다면 사실상 동일
품목으로 본다. `categoryId`까지는 요구하지 않는다(브랜드+제목이 같으면 카테고리 오분류 쪽이 이미
이상치다).

- `brandId`가 `null`(미지정 상품)이면 비교 불가 — 빈 결과를 낸다(브랜드 없이 제목만으로 묶으면
  오탐이 너무 많다).
- 자기 자신은 제외.
- `DRAFT`(비공개)·`SOLD`(판매 완료)는 제외 — "지금 얼마에 팔리고 있는지"이므로 **현재 활성
  리스팅**만 본다. 경매 상품(`AUCTION_SCHEDULED`/`AUCTION_IN_PROGRESS`)은 `price`가 아직 없거나
  최종가가 아니라 자연히 제외된다(= 사실상 `ON_SALE`만 남는다).
- 표본 상한 50개(`SIMILAR_PRODUCT_LIMIT=20`과 같은 취지 — 그래프용 표본이면 충분, 상세 조회
  왕복마다 전수 스캔 방지).

### 엔드포인트

`GET /api/products/{id}/market-price` — 요청 문서가 제안한 경로 그대로 채택. `similarProducts`와
달리 상세 응답(`ProductDetailResponse`)에 묶지 않고 **별도 엔드포인트**로 둔다:
가격 그래프 탭을 열 때만 필요한 부가 데이터라, 상세 조회 1회에 항상 끼워 넣으면 그래프를 안 보는
사용자에게도 매번 추가 쿼리가 나간다.

- 인증 불필요(상품 상세와 동일하게 공개).
- 상품이 없거나 `DRAFT`(본인 제외)면 `PRODUCT_NOT_FOUND` 404 — 상세 조회와 동일 규칙.
- 매칭되는 동일 상품이 없으면 에러가 아니라 **빈 배열**로 200 응답(그래프가 "표본 없음"을 그리면
  됨 — `similarProducts` 패턴과 동일).

### 응답 DTO — `MarketPriceResponse`

- `currentPrice: Long?` — 현재 상품의 가격. 경매 예정 등 가격이 아직 없으면 `null`.
- `prices: List<Long>` — 동일 상품으로 판정된 다른 활성 리스팅들의 가격 목록(히스토그램/분포용).
- 요청 문서가 명시한 최소 요건("가격 값 목록 + 현재 상품 가격 표시용 기준값")만 담고, 그 이상
  (판매자 정보 등)은 넣지 않는다 — 필요해지면 그때 요청받는다.

### 구현 계획

- `ProductRepository`에 조회 쿼리 추가: `brandId` 일치 + `title` 정규화 일치(`TRIM`/`LOWER`,
  공백은 우선 단순 `TRIM`만 — 다중 공백 정규화는 DB 함수 대신 저장 시점 정책 문제라 이번 범위에서
  제외하고 필요해지면 별도로 다룬다) + 제외 조건 + limit.
- `ProductService`에 `getMarketPrice(Long productId)` 추가 — 상품 조회·DRAFT 가드는
  `getProductDetail`과 같은 헬퍼를 재사용.
- `ProductController`에 `GET /{id}/market-price` 추가, Swagger 어노테이션 포함.

## 구현 목록

- [ ] `ProductRepository`에 동일 상품(브랜드+제목 정규화 일치) 조회 쿼리 추가
- [ ] `MarketPriceResponse` DTO 추가
- [ ] `ProductService.getMarketPrice` 추가(브랜드 null/상품 없음/DRAFT 케이스 처리)
- [ ] `ProductController`에 `GET /api/products/{id}/market-price` 추가 + Swagger
- [ ] 테스트: 동일 상품 매칭(브랜드+제목 일치), 브랜드 null 제외, DRAFT/SOLD 제외, 매칭 없음 시
      빈 배열

## 확인이 필요한 미결정 사항

- 제목 정규화 수준(대소문자·공백 정도)이 실제 등록 데이터 기준으로 너무 느슨/빡빡하지 않은지 —
  일단 trim + 대소문자 무시로 시작하고 실사용 데이터로 조정.
- 표본 상한 50이 적절한지.
