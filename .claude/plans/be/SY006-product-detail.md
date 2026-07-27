# SY006 - 상품 상세 조회 API

## 배경/목표

`APIs.md`의 "상품 상세 조회"(`GET /products/{id}`, PROD-006)를 구현한다. 기능 정의서 원문은 이미지·실측/하자·판매자·판매 방식·연결 라이브를 모두 포함하지만, 현재 코드베이스에는 이미지(`product_image`)·실측/하자·라이브(`live`, `live_product`) 도메인이 아직 엔티티/리포지토리로 구현되어 있지 않다(`docs/db/schema.sql`에 테이블만 정의됨). `SY004`(상품 기본 정보 저장)에서 이미지 등을 별도 계획으로 미룬 것과 같은 방식으로, 이번 계획은 **현재 존재하는 `Product`/`Member` 엔티티만으로 구성 가능한 범위**로 좁혀 구현한다. 이미지/실측·하자/연결 라이브는 해당 도메인이 생긴 뒤 응답에 추가한다.

## 작업 내용

- **`GET /api/products/{id}`**
  - 비로그인 사용자도 조회 가능(PROD-006 대상: 전체). `SecurityConfig`의 `PUBLIC_ENDPOINTS`는 문자열 패턴 배열이라 HTTP 메서드를 구분하지 못하므로, `POST /api/products`(인증 필요)와 경로가 겹치지 않게 `requestMatchers(HttpMethod.GET, "/api/products/{id}")`로 GET만 별도로 permitAll 처리한다(`HOME-001`의 `/api/home` 공개 패턴과 동일한 취지).
  - `Authentication`은 nullable로 받는다(토큰 없으면 `JwtAuthenticationFilter`가 SecurityContext를 채우지 않음). 로그인 상태면 `authentication.getPrincipal()`로 `viewerId`를 얻어 본인 상품 여부를 판단한다.
  - 검증/공개 범위:
    - 상품이 없으면 404 `PRODUCT_NOT_FOUND`(기존 에러코드 재사용).
    - `saleStatus`가 `DRAFT` 또는 `PRIVATE`인 상품은 비공개로 간주해 **판매자 본인이 아니면 404**로 응답한다(존재 자체를 숨김 — 403 대신 404를 쓰는 이유는 비공개 상품의 존재 여부 노출을 막기 위함). 그 외 상태(`ON_SALE`/`AUCTION_SCHEDULED`/`AUCTION_IN_PROGRESS`/`AUCTION_FAILED`/`SOLD`)는 누구나 조회 가능.
  - Response(`ProductDetailResponse`, 신규 — 목록/생성에 쓰는 기존 `ProductResponse`와는 분리): `id`, `sellerId`, `sellerNickname`, `categoryId`, `brandId`, `title`, `description`, `conditionGrade`, `sizeLabel`, `saleType`, `saleStatus`, `price`, `createdAt`, `updatedAt`.
    - `sellerNickname`은 `home` 도메인의 `LiveCardResponse.hostNickname`과 동일하게 평탄화된 필드로 둔다(중첩 객체 X).
  - 200 OK.
- Swagger 어노테이션(`@Operation`/`@ApiResponses`) 추가(404 케이스 명시).
- `ProductServiceTest`에 케이스 추가: 공개 상태 상품은 비로그인/타인도 조회 가능 / `DRAFT`·`PRIVATE` 상품은 본인만 조회 가능 / 존재하지 않는 상품은 404.
- `BE/README.md`는 이미 `product/` 패키지가 반영되어 있으므로 변경 불필요.
- `DRAFT`/`PRIVATE` 상품을 타인이 조회했을 때 404로 존재 숨김.

## 구현 목록

- [x] `SecurityConfig`: `GET /api/products/{id}`만 permitAll로 열기 (`POST /api/products`는 계속 인증 필요)
- [x] `ProductDetailResponse` (`product/dto/response`) — `sellerNickname` 포함
- [x] `Product`/`ProductRepository`에 추가 변경 없음(기존 `findById` 재사용, `seller`는 `LAZY`라 nickname 조회 시 프록시 초기화됨)
- [x] `ProductService.getProductDetail(Long viewerId, Long productId)` — `viewerId`는 nullable
- [x] `ProductController` — `GET /api/products/{id}` (Swagger 포함, `Authentication`은 필수 아님)
- [x] `ProductServiceTest` 케이스 3건 추가
- [x] `.claude/skills/verify` 기준 빌드/테스트 통과 확인

## 확인이 필요한 미결정 사항

- 이미지(`product_image`), 실측/하자, 연결 라이브(`live_product`)는 해당 도메인 엔티티가 아직 없어 이번 응답에서 제외했다. 필요 시 각각 별도 계획으로 진행.
- `product.view_count`(조회수 증가)는 PROD-006 기능 설명에 명시되어 있지 않아 이번 범위에서 다루지 않는다 — 필요하면 별도 확인 후 반영.