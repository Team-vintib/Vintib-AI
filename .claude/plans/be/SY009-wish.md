# SY009 - 상품 찜/해제 API

## 배경/목표

`APIs.md` "팔로우 / 찜 (Socials)" 섹션, 기능 정의서 `MY-009`(상품 찜·해제)를 구현한다. 1차로 찜 등록/해제만 구현했고, 이번에 찜 목록 조회(`GET /users/{id}/wishes`, `MY-006`/`MY-009` 조회 부분)를 추가한다(같은 기능번호 `MY-009` 작업이라 같은 계획 파일에 이어서 정리).

## 작업 내용

- 새 도메인 패키지 `wish`를 만든다. `찜`은 `member`/`product`와 구분되는 독립 리소스이므로, `tryon`이 `/users/{userId}/tryons`로 별도 패키지를 둔 것과 동일한 방식을 따른다.
- **엔티티 `Wish`**: DB 스키마(`docs/db/schema.sql`)의 `wish` 테이블과 동일하게 대리키 없이 `(member_id, product_id)` 복합키 + `created_at`만 갖는다. `@EmbeddedId`로 복합키(`WishId` — `memberId`, `productId`)를 구성하고, `member`/`product`는 `@MapsId`로 복합키 필드와 연결한다.
- **`POST /api/users/{userId}/wishes`**
  - 인증 필요. path의 `userId`가 인증된 본인이 아니면 403(`TryOnController.requireSelf`와 동일한 패턴, IDOR 방지 — 신규 `WISH_FORBIDDEN`).
  - Request body: `productId`.
  - 대상 상품이 없거나 `DRAFT`/`PRIVATE` 상태면 404 `PRODUCT_NOT_FOUND`(`Product.isPrivate()` 재사용 — 상품 상세 조회와 동일한 공개 범위 기준).
  - 이미 찜한 상품이면 409(신규 `WISH_ALREADY_EXISTS`).
  - 성공 시 201, `WishResponse(productId, createdAt)` 반환.
- **`DELETE /api/users/{userId}/wishes/{id}`**
  - 인증 필요, `userId` 본인 확인은 위와 동일.
  - `id`는 별도 찜 PK가 없으므로 상품 ID를 그대로 받는다 — `TryOnController` 상단 주석에 이미 명시된 `APIs.md`의 `/users/{userId}/wishes/{id}` 표기 관례를 그대로 따른다.
  - 찜 기록이 없으면 404(신규 `WISH_NOT_FOUND`).
  - 성공 시 204 No Content.
- **`ErrorCode`**: `// [소셜(팔로우/찜)]` 구역을 새로 추가하고 `S001 WISH_ALREADY_EXISTS`(409), `S002 WISH_NOT_FOUND`(404)를 채운다(기존 C/U/L/A/W/O/P/T와 겹치지 않는 새 접두어). 구현 중 `requireSelf` 403 전용 코드가 없다는 걸 확인해 `S003 WISH_FORBIDDEN`(403)도 같은 구역에 추가했다(계획 대비 추가분).
- Swagger 어노테이션(`@Tag`/`@Operation`/`@ApiResponses`, 401/403/404/409 케이스 포함).
- `WishServiceTest`(서비스 단위 테스트): 찜 성공 / 중복 찜 시 409 / 비공개(DRAFT·PRIVATE)·존재하지 않는 상품 찜 시도 404(2건) / 찜 해제 성공 / 존재하지 않는 찜 해제 시 404 — 총 6건(계획 시점엔 404 케이스를 하나로 뭉뚱그려 5건으로 적었으나, 구현 시 "상품 자체가 없음"과 "DRAFT/PRIVATE라 404"를 별도 케이스로 나눠 6건이 됨).
- `BE/README.md` 디렉터리 구조 섹션에 `wish/` 패키지 반영.

### 찜 목록 조회 (추가분)

- **`GET /api/users/{userId}/wishes?page=&size=`**
  - 인증 필요. `userId` 본인 확인은 등록/해제와 동일한 `requireSelf`(403 `WISH_FORBIDDEN`).
  - 페이지네이션은 `SY007`(상품 목록 조회)과 동일하게 Spring Data `Pageable`(offset 기반) 사용. 정렬은 찜한 시각(`wish.created_at DESC`, 최근 찜한 순) 고정 — 클라이언트가 다른 sort를 보내도 무시(`ProductService.getProductList`의 `PageRequest.of(..., Sort.by(DESC, "createdAt"))` 패턴 재사용).
  - `MY-009` 스펙("판매 완료 또는 비공개 상품은 현재 상태를 함께 표시한다")에 따라 등록/해제와 달리 **상품 상태로 필터링하지 않는다** — 찜한 이후 상품이 `SOLD`/`PRIVATE`로 바뀌어도 목록에서 빠지지 않고 현재 상태 그대로 노출한다.
  - N+1 방지: `WishRepository`에 `@EntityGraph(attributePaths = "product")`로 product를 함께 fetch하는 조회 메서드를 추가한다(`findByMember_Id(Long memberId, Pageable pageable)` 형태, `Page<Wish>` 반환).
  - Response: 기존 `PageResponse<T>`(`global/response`)를 재사용해 `PageResponse<WishItemResponse>`로 응답한다. 항목 DTO는 상품 정보(기존 `ProductResponse` 재사용)와 찜한 시각을 함께 담는 신규 `WishItemResponse(ProductResponse product, LocalDateTime wishedAt)`.
  - 200 OK, 목록이 비어 있어도 200 + 빈 `content`(에러 아님) — `SY007`과 동일한 규칙.
- Swagger 어노테이션 추가(200/401/403 케이스).
- `WishServiceTest`에 케이스 추가: 찜한 상품 목록 반환(최근 찜한 순) / 찜한 뒤 상품이 `SOLD`·`PRIVATE`로 바뀌어도 목록에 남고 상태가 반영됨 / 빈 목록 처리.

## 구현 목록

- [x] `Wish` 엔티티 + `WishId`(`@EmbeddedId`) (`wish/entity`)
- [x] `WishRepository`(`existsById`/`findById`/`deleteById`로 충분, 커스텀 쿼리 메서드 불필요) (`wish/repository`)
- [x] `ErrorCode`에 `S001 WISH_ALREADY_EXISTS`, `S002 WISH_NOT_FOUND`, `S003 WISH_FORBIDDEN`(계획 대비 추가) 추가
- [x] `WishCreateRequest`(`productId`, `@NotNull`) (`wish/dto/request`)
- [x] `WishResponse`(`productId`, `createdAt`) (`wish/dto/response`)
- [x] `WishService.wish(memberId, productId)` / `unwish(memberId, productId)` (`wish/service`)
- [x] `WishController` — `POST /api/users/{userId}/wishes`, `DELETE /api/users/{userId}/wishes/{id}` (`wish/controller`, Swagger 포함)
- [x] `WishServiceTest` 케이스 6건
- [x] `BE/README.md` 디렉터리 구조 갱신
- [x] `.claude/skills/BE:verify` 기준 빌드/테스트 통과 확인 (`BUILD SUCCESSFUL`, 신규 테스트 6건 모두 통과)

### 찜 목록 조회 (추가분)

- [x] `WishRepository.findByMember_Id(Long memberId, Pageable pageable)` — `@EntityGraph(attributePaths = "product")`로 product 함께 fetch
- [x] `WishItemResponse(ProductResponse product, LocalDateTime wishedAt)` (`wish/dto/response`)
- [x] `WishService.getWishList(Long memberId, Pageable pageable)` — 상태 필터 없이 전체 반환, 찜한 시각 최신순 고정 정렬
- [x] `WishController` — `GET /api/users/{userId}/wishes`(`Pageable` 파라미터, Swagger 포함)
- [x] `WishServiceTest` 케이스 추가(목록 반환 / 판매완료·비공개 상품도 노출 / 빈 목록) — 3건 추가로 총 9건
- [x] `.claude/skills/BE:verify` 기준 빌드/테스트 통과 확인 (`BUILD SUCCESSFUL`, 신규 테스트 9건 모두 통과)