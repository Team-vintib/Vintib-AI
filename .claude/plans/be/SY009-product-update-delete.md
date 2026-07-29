# SY009 - 상품 정보 수정·삭제 API

## 배경/목표

`APIs.md`의 "상품 정보 수정"(`PATCH /products/{id}`, PROD-007)을 구현하고, 사용자 확인에 따라 "상품 삭제"(`DELETE /products/{id}`) API를 추가로 신설한다.

- PROD-007 원문은 "수정·비공개 처리"만 정의하고("경매 진행 중이거나 판매 완료된 상품의 수정 제한은 추가 논의 필요"), 별도의 삭제 기능은 기능 정의서/`APIs.md`에 없다.
- 사용자 확인 결과: "삭제"는 PRIVATE 상태 전환이 아니라 **실제 삭제 API**로 구현한다. 단, `docs/db/schema.sql` 최상단 설계 원칙("삭제는 물리 삭제 대신 상태 컬럼 또는 `deleted_at` 으로 처리한다")과 `product` 테이블에 이미 정의된 `deleted_at` 컬럼·`ix_product_status_created ... WHERE deleted_at IS NULL` 인덱스를 따라 **소프트 삭제**(`deleted_at` 타임스탬프 기록)로 구현한다. 물리 DELETE는 하지 않는다.
- 수정 가능 범위: 사용자 확인 결과, `DRAFT`/`ON_SALE`/`PRIVATE` 상태에서만 수정·삭제를 허용한다. `AUCTION_SCHEDULED`/`AUCTION_IN_PROGRESS`/`AUCTION_FAILED`/`SOLD` 상태는 수정·삭제 불가(400).

## 작업 내용

- **`Product` 엔티티**
  - `deletedAt`(`LocalDateTime`, nullable) 필드 추가.
  - `@SQLRestriction("deleted_at IS NULL")`을 엔티티에 추가해, Hibernate가 생성하는 모든 조회(`findById` 포함)에서 소프트 삭제된 상품을 자동으로 제외한다. 이렇게 하면 `ProductService.getProductDetail`, `ProductImageService`, `TryOnResultService` 등 기존에 `productRepository.findById(...)`를 쓰는 모든 곳이 별도 수정 없이 삭제된 상품을 "존재하지 않음"(`PRODUCT_NOT_FOUND`)으로 자연스럽게 처리하게 된다.
  - `isEditable()`: `saleStatus`가 `DRAFT`/`ON_SALE`/`PRIVATE`인지 여부.
  - `update(String title, String description, Long categoryId, Long brandId, String conditionGrade, String sizeLabel)`: null이 아닌 필드만 반영하는 부분 수정(기존 값 유지). `ProductImage`의 `updateImage`와 동일한 부분 수정 패턴.
  - `softDelete()`: `deletedAt = LocalDateTime.now()` 설정.
- **`ProductUpdateRequest`**(`product/dto/request`, 신규): `title`(nullable, `@Size(min = 1)`로 빈 문자열 방지), `description`, `categoryId`, `brandId`, `conditionGrade`, `sizeLabel` — 전부 nullable, 요청에 포함된 필드만 반영.
- **`PATCH /api/products/{id}`**
  - 인증 필요(JWT), 소유자 검증(`isOwnedBy`) — 기존 `registerDirectSale`/이미지 API와 동일한 패턴.
  - `isEditable()`이 아니면 400 `INVALID_PRODUCT_STATE`(기존 에러코드 재사용).
  - `ProductService.updateProduct(Long sellerId, Long productId, ProductUpdateRequest request)` → `ProductResponse` 반환, 200 OK.
- **`DELETE /api/products/{id}`**
  - 인증 필요(JWT), 소유자 검증.
  - `isEditable()`이 아니면 400 `INVALID_PRODUCT_STATE`.
  - `ProductService.deleteProduct(Long sellerId, Long productId)` → `product.softDelete()` 호출, 204 No Content. 별도 응답 바디 없음(기존 이미지 삭제 API와 동일).
  - `@SQLRestriction` 덕분에 이미 삭제된 상품/존재하지 않는 상품은 동일하게 404로 처리됨(삭제 여부 자체를 노출하지 않음).
- **연관 테이블 처리 범위 한정**: `product_image`/`wish`/`tryon_result`/`live_product`/`auction`/`orders` 등 `product`를 참조하는 테이블은 이번 범위에서 별도로 손대지 않는다(연쇄 소프트 삭제, 라이브·경매 연결 해제 등은 각 도메인이 생기면 별도 계획으로 다룬다). 이번 계획은 상품 자체의 수정/삭제 API로 한정한다.
- Swagger 어노테이션(`@Operation`/`@ApiResponses`) 추가.
- `APIs.md`에 `DELETE /products/{id}` 행 추가(기능 ID는 PROD-007 확장으로 표기, 기능 정의서에 별도 ID가 없음을 주석으로 남김).
- `ProductServiceTest`: 최소 아래 케이스 추가.
  - 수정: 본인 상품을 부분 수정하면 반영된 필드만 바뀐다 / 본인이 아니면 403 / `AUCTION_IN_PROGRESS` 등 수정 불가 상태면 400.
  - 삭제: 본인 상품을 삭제하면 `deletedAt`이 설정되고 이후 상세 조회가 404가 된다 / 본인이 아니면 403 / 수정 불가 상태면 400.
- `BE/README.md`는 변경 불필요(기존 `product/` 패키지 구조 유지).

## 구현 목록

- [x] `Product` 엔티티: `deletedAt` 필드, `@SQLRestriction("deleted_at IS NULL")`, `isEditable()`, `update(...)`, `softDelete()`
- [x] `ProductUpdateRequest` (`product/dto/request`)
- [x] `ProductService.updateProduct(Long sellerId, Long productId, ProductUpdateRequest request)`
- [x] `ProductService.deleteProduct(Long sellerId, Long productId)`
- [x] `ProductController` — `PATCH /api/products/{id}`, `DELETE /api/products/{id}` (Swagger 포함)
- [x] `APIs.md`에 `DELETE /products/{id}` 행 추가
- [x] `ProductServiceTest` 케이스 추가(수정 3건 + 삭제 3건)
- [x] `.claude/skills/verify` 기준 빌드/테스트 통과 확인

## 확인 완료된 사항 (참고)

- 삭제는 물리 삭제가 아닌 `deleted_at` 소프트 삭제로 구현(schema.sql 설계 원칙 준수).
- 수정·삭제 모두 `DRAFT`/`ON_SALE`/`PRIVATE` 상태에서만 허용, 그 외 상태는 400.
- 연관 테이블(이미지/위시/시착결과/라이브상품/경매/주문)의 연쇄 처리는 이번 범위 제외.

## 구현 중 변경된 사항

- `getProductDetail`에 `product.isDeleted()` 명시적 체크를 추가했다(계획 초안은 `@SQLRestriction`만으로 충분하다고 봤으나, Mockito 기반 단위 테스트는 실제 Hibernate 쿼리를 타지 않아 `@SQLRestriction`이 적용되지 않는다 — 서비스 레이어에 명시적 체크를 둬야 "삭제 후 조회 404"가 테스트 가능하고, 다른 경로에 대한 방어도 한 겹 더 생긴다). `@SQLRestriction`은 `ProductImageService`/`TryOnResultService` 등 이번 범위에서 손대지 않은 기존 코드에 대한 런타임 안전망으로 유지.