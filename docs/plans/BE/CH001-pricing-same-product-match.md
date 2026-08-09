# CH001 동일 상품 매칭 — BE 구현 (docs/requests/BE/047 반영)

## 배경 / 목표

AI 쪽(`AI/app/pricing/`)에 이미지 임베딩 없이 상품명·브랜드·카테고리 텍스트로 "동일 상품"을
판정하는 `internal_text` comps 백엔드가 이미 구현돼 있다(CH030). 이 결과를 실제로 쓰려면 BE가
`docs/requests/BE/047-pricing-same-product-match.md`가 요청한 3가지를 반영해야 한다.

핵심 흐름: FE가 등록 마지막(가격) 스텝에서 `GET /ai/jobs/{job_id}`를 직접 폴링해 AI의
`PricingResult.product_match_key`를 받아두고, 상품 저장 API 호출 시 `matchKey` 필드로 BE에
전달한다 — BE가 AI를 직접 호출하지 않는다.

## 작업 내용

1. **스키마**: `product.match_key VARCHAR(300)` nullable 컬럼 추가.
2. **엔티티/DTO**: `Product.java`에 `matchKey` 필드 추가, 기존 `update()`(partial-update
   메서드)에 같이 반영. `ProductUpdateRequest`에 `matchKey`(nullable, null=변경 없음) 추가
   — 가격 확정 API가 아니라 이 엔드포인트에 넣는 이유는 직접판매·경매 둘 다 필요하기
   때문(가격 확정은 직접판매에만 있음). `ProductResponse`에도 노출.
3. **완료거래가 배치 조회**: `OrderRepository`에 상품 id 목록으로 완료거래를 배치 조회하는
   메서드 추가(`REFUNDED`/`CANCELED` 제외, `AuctionRepository.findByProductIdIn` 패턴 재사용).
   `Order.auction == null`이면 `SOLD_DIRECT`, 아니면 `SOLD_AUCTION`으로 태그.
4. **신규 엔드포인트** `GET /api/products/{id}/market-price` (025가 제안한 이름, 비회원도
   조회 가능):
   - 대상 상품의 `match_key`가 없으면 빈 결과(404 아님).
   - `ProductRepository.findByMatchKeyAndIdNot(matchKey, excludeId, Pageable)`(신규,
     `findSimilarProducts`와 같은 형태)로 후보를 찾고, `saleStatus`/완료거래 배치 조회로
     `priceKind` 계산(`ASKING`/`SOLD_DIRECT`/`SOLD_AUCTION`).
   - 대상 상품 자신의 현재가도 기준값으로 같이 낸다.
   - **`GET /api/products` 목록 응답은 건드리지 않는다** — 047이 요청했지만, 목록은 가벼운
     단일 쿼리 경로라 완료거래 배치조회를 얹으면 무관한 대부분의 조회에도 비용이 붙는다.
     이 신규 엔드포인트에만 계산을 얹는다.
5. **문서 정리**: 반영 완료 후 `docs/requests/BE/025-product-same-price-chart.md`,
   `docs/requests/BE/047-pricing-same-product-match.md` 삭제.
6. **FE 후속 요청 문서**(`docs/requests/FE/`): (a) `estimateRegistrationPrice` 호출에
   `productId`(이미 `draft.draftProductId`로 있음) 포함, (b) 폴링해서 받은
   `product_match_key`를 `PATCH /products/{id}` 호출 시 `matchKey` 필드로 포함.

## 구현 목록

- [ ] `schema.sql`/`comments.sql`에 `product.match_key VARCHAR(300)` 추가
- [ ] `Product.java`: `matchKey` 필드 + `update()`에 반영 + getter
- [ ] `ProductUpdateRequest`에 `matchKey` 추가, `ProductService.updateProduct()`가 전달
- [ ] `ProductResponse`에 `matchKey` 추가
- [ ] `OrderRepository`: 상품 id 목록으로 완료거래 배치 조회 메서드 추가
- [ ] `ProductRepository`: `findByMatchKeyAndIdNot` 추가
- [ ] 신규 컨트롤러/서비스 메서드: `GET /api/products/{id}/market-price` + 전용 응답 DTO
- [ ] `025`/`047` 요청 문서 삭제(반영 완료 후)
- [ ] `docs/requests/FE/` 신규 문서 작성

## 확인이 필요한 미결정 사항

- `match_key`가 없는(구) 상품 백필은 이번 범위 밖.
- `market-price` 응답 매물 수 상한(기존 유사상품 조회 20건 cap과 동일 기준 적용).
- `regen.sh`/`export-erd.sh`(데이터 딕셔너리·ERD 재생성)는 로컬 DB 필요해 사용자가 직접 실행.
