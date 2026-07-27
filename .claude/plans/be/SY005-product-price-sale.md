# 006 - 판매 가격 설정 및 상시 판매 등록 API

## 배경/목표

`005-product-basic-info-save.md`에서 만든 `DRAFT` 상태 상품에 가격을 설정해 `ON_SALE`(상시 판매)로 전환한다(PROD-002). `docs/db/erd.md`의 상태 전이(`DRAFT --> ON_SALE : 상시 판매 등록`)와 일치한다.

`APIs.md`의 `PATCH /products/{id}/status`는 PROD-002~005, PROD-014를 묶어 하나의 엔드포인트로 정의해 두었지만, 이번 계획은 **PROD-002(DRAFT → ON_SALE)만** 다룬다. 경매 전환(PROD-004), 미낙찰 재설정(PROD-005) 등 다른 전이는 각각 별도 계획으로 진행한다.

## 작업 내용

- **`PATCH /api/products/{id}/status`**
  - 인증 필요(JWT), `PROD-001`과 동일하게 `(Long) authentication.getPrincipal()`로 `sellerId` 추출.
  - Request(`ProductStatusUpdateRequest`): `price`(`@NotNull @Positive`)만 받는다. 이번 API는 "상시 판매 등록"만 지원하므로 별도의 액션 필드는 두지 않는다 — 경매 전환 등 다른 전이가 실제로 필요해지는 시점에 이 DTO/로직을 확장한다(지금 미리 설계하지 않음).
  - 검증 순서: 상품 존재 확인(없으면 404) → 요청자가 판매자 본인인지 확인(아니면 403) → 상품이 현재 `DRAFT` 상태인지 확인(아니면 400, 다른 상태에서의 전이는 이번 API 범위 아님).
  - 통과하면 `Product`에 `registerDirectSale(Long price)` 도메인 메서드를 추가해 `saleType=DIRECT_SALE`, `price=요청값`, `saleStatus=ON_SALE`로 갱신(JPA 변경 감지로 반영, 명시적 `save` 불필요).
  - Response: 기존 `ProductResponse`에 `price` 필드를 추가해 재사용(PROD-001 응답에는 항상 `null`이었던 필드가 이제 채워짐 — 하위 호환 깨지지 않는 추가 변경).
  - 200 OK.
- **신규 `ErrorCode`** (`[상품]` 구분, `P` 프리픽스로 신설 — 기존 카테고리와 겹치지 않음)
  - `PRODUCT_NOT_FOUND`(404, `P001`) — 상품 없음
  - `NOT_PRODUCT_OWNER`(403, `P002`) — 본인 상품이 아님
  - `INVALID_PRODUCT_STATE`(400, `P003`) — `DRAFT` 상태가 아닌데 상시 판매 등록을 시도함
- Swagger 어노테이션(`@Operation`/`@ApiResponses`) 추가.
- `ProductServiceTest`에 케이스 추가: 정상 전환(가격 설정 + `ON_SALE`) / 상품 없음(404) / 본인 상품 아님(403) / `DRAFT`가 아닌 상품에 시도(400).

## 구현 목록

- [x] `ErrorCode`에 `PRODUCT_NOT_FOUND`, `NOT_PRODUCT_OWNER`, `INVALID_PRODUCT_STATE` 추가
- [x] `Product`에 `registerDirectSale(Long price)` 도메인 메서드 추가
- [x] `ProductResponse`에 `price` 필드 추가
- [x] `ProductStatusUpdateRequest` (`price` 단일 필드, `@NotNull @Positive`)
- [x] `ProductService.registerDirectSale(Long sellerId, Long productId, ProductStatusUpdateRequest request)`
- [x] `ProductController` — `PATCH /api/products/{id}/status` (Swagger 포함)
- [x] `ProductServiceTest` 케이스 4건 추가
- [x] `.claude/skills/verify` 기준 빌드/테스트 통과 확인

## 확인이 필요한 미결정 사항

- **요청 DTO를 `price` 단일 필드로 좁게 갈지, 아니면 향후 PROD-003~005/014를 염두에 두고 지금부터 `action`/`targetStatus` 같은 필드를 넣어둘지.** 이번 계획은 전자(좁게 감)로 가정했다 — 아직 요구되지 않은 미래 케이스를 지금 설계하지 않는다는 원칙에 따름. 다른 방식을 원하면 알려달라.