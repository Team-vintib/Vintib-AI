# 005 - 상품 기본 정보 저장 API

## 배경/목표

`APIs.md`의 "상품 정보 등록"(`POST /products`, PROD-001)을 두 단계로 나눠 구현한다.

1. **상품 기본 정보 저장** (이번 계획) — 로그인한 판매자가 카테고리/브랜드/제목/설명/상태등급/사이즈/판매방식을 입력해 `DRAFT` 상태 상품을 생성한다.
2. 판매 가격 설정 및 상시 판매 등록 (`PATCH /products/{id}/status`, PROD-002~005) — 이후 별도 계획으로 진행.

이 분리는 `docs/db/erd.md`에 이미 정의된 `product.sale_status` 상태 전이(`DRAFT → ON_SALE`)와 맞아떨어진다. 이번 API는 상품 목록/상세 조회 API와도 겹치지 않도록 "생성"만 다룬다.

## 작업 내용

- `product` 도메인 신설 (`com.ssafy.backend.product`) — `controller/service/entity/repository/dto`.
- **Product 엔티티**
  - `seller`: `Member`에 대한 `@ManyToOne` (member 도메인은 이미 존재).
  - `categoryId`, `brandId`: 아직 `category`/`brand` 엔티티가 없으므로 이번 범위에서는 매핑 없이 순수 `Long` 컬럼으로 저장한다(선택 입력, 존재 여부 검증 없음 — 사용자 확인 완료). 해당 도메인이 생기면 `@ManyToOne`으로 교체를 검토한다.
  - `title`, `description`, `conditionGrade`, `sizeLabel`, `saleType`(`Enumerated(STRING)`, **nullable** — 이번 API에서는 받지 않음), `saleStatus`(기본값 `DRAFT`), `price`(이번 API에서는 항상 `null`).
  - `BaseTimeEntity` 상속(`createdAt`/`updatedAt` 자동 관리).
  - `SaleType { DIRECT_SALE, AUCTION }`, `SaleStatus { DRAFT, ON_SALE, AUCTION_SCHEDULED, AUCTION_IN_PROGRESS, AUCTION_FAILED, SOLD, PRIVATE }` enum을 `product/entity`에 둔다(`docs/db/erd.md` §3-1 값 그대로).
  - `saleType`은 다음 단계(판매 가격 설정/상시 판매 등록, 또는 AUCT-001 경매 조건 설정)에서 그 API를 호출하는 순간 비로소 정해진다 — 어떤 판매 채널을 고르느냐가 곧 `saleType`을 결정하는 행위이므로, 기본 정보 저장 시점에 미리 확정시키지 않는다.
- **schema.sql 조정** — `product.sale_type` 컬럼의 `NOT NULL`을 제거한다(이번 단계에서 값을 받지 않으므로 DRAFT 상품은 `sale_type IS NULL`로 저장됨). `ck_product_price_by_type`(`sale_type <> 'DIRECT_SALE' OR price IS NOT NULL`)과 `ck_product_sale_type`(`sale_type IN (...)`)은 **수정하지 않아도 된다** — PostgreSQL CHECK 제약은 비교 결과가 `NULL`이면 위반으로 보지 않으므로, `sale_type IS NULL`인 동안은 두 제약 모두 자동으로 통과한다.
- **Hibernate로 제약 미러링** — `local` 프로파일은 `ddl-auto: update`라 Hibernate가 CHECK 제약을 자동 생성하지 않는다. `Product` 엔티티에 `org.hibernate.annotations.Check`로 schema.sql의 기존 제약 3개(`ck_product_sale_type`, `ck_product_sale_status`, `ck_product_price_by_type`, 원문 그대로)를 옮겨, 로컬 DB도 schema.sql과 동일한 무결성 규칙을 갖게 한다.
- **`POST /api/products`**
  - 인증 필요(JWT) — `Authentication`에서 `memberId` 추출(`AuthController.logout`과 동일한 패턴, `(Long) authentication.getPrincipal()`).
  - Request(`ProductCreateRequest`): `title`(`@NotBlank`), `description`(nullable), `categoryId`(nullable), `brandId`(nullable), `conditionGrade`(nullable, 자유 문자열), `sizeLabel`(nullable). **`saleType`은 이번 요청에 포함하지 않는다.**
  - saleStatus는 항상 `DRAFT`로 생성, `saleType`/`price`는 저장하지 않는다(둘 다 `null`).
  - Response(`ProductResponse`): `id`, `sellerId`, `categoryId`, `brandId`, `title`, `description`, `conditionGrade`, `sizeLabel`, `saleType`(항상 `null`), `saleStatus`, `createdAt`.
  - 201 Created.
  - 신규 `ErrorCode` 불필요 — 이번 API는 `@Valid` 검증 실패(400) 외 별도 실패 케이스가 없다(카테고리/브랜드 존재 검증은 하지 않기로 확인됨).
- Swagger 어노테이션(`@Tag`/`@Operation`/`@ApiResponses`) 추가.
- `ProductServiceTest`: 최소 1개 이상 — 예) `상품_기본_정보를_저장하면_saleType_없이_DRAFT_상태로_생성된다()`.
- `BE/README.md` 디렉터리 구조 섹션에 `product/` 패키지 반영.

## 구현 목록

- [x] `docs/db/schema.sql`: `product.sale_type` 컬럼 `NOT NULL` 제거
- [x] `Product` 엔티티 + `SaleType`/`SaleStatus` enum (`product/entity`), Hibernate `@Check` 미러링 (Hibernate 7의 `org.hibernate.annotations.Check`는 deprecated라 `@Table(check = @CheckConstraint(...))`(JPA 3.2 표준)로 대체)
- [x] `ProductRepository`
- [x] `ProductCreateRequest` / `ProductResponse` (`product/dto/request`, `product/dto/response`) — `saleType` 필드 없음
- [x] `ProductService.createProduct(Long sellerId, ProductCreateRequest request)`
- [x] `ProductController` — `POST /api/products` (Swagger 포함)
- [x] `ProductServiceTest`
- [x] `BE/README.md` 디렉터리 구조 갱신
- [x] `.claude/skills/verify` 기준 빌드/테스트 통과 확인

## 확인 완료된 사항 (참고)

- `sale_type`은 이번 API에서 받지 않는다(다음 단계에서 결정). DB 컬럼은 nullable로 변경.
- 상품 이미지(`product_image`)는 이번 API 범위에서 제외(별도 계획).
- `categoryId`/`brandId`는 선택 입력, 존재 검증 없음.
