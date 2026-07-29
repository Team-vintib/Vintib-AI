# SY007 - 상품 목록 조회 API

## 배경/목표

`APIs.md`의 "상품 목록 조회"(`GET /products`, PROD-008)를 구현한다. 기능 정의서 PROD-008은 대상이 "회원"이고 "상시 판매, 경매 여부와 관계없이 상품 목록을 모두 보여준다"만 규정한다. 같은 API로 매핑된 `SEARCH-002`(카테고리/브랜드/가격대/상태/판매방식 필터)는 이번 범위에서 제외하고 별도 계획으로 미룬다 — 검색 도메인 자체가 아직 없고, 필터까지 포함하면 스펙이 커진다(사용자 확인 완료).

## 작업 내용

- **`GET /api/products?page=&size=`**
  - 인증 필요(회원 대상, PROD-008). `SecurityConfig`는 이미 명시적으로 permitAll 처리한 경로 외에는 기본적으로 `anyRequest().authenticated()`이고, `GET /api/products/{id}`만 별도로 열려 있으므로 `GET /api/products`(경로 변수 없음)는 추가 설정 없이 이미 인증이 필요하다.
  - 페이지네이션은 Spring Data `Pageable`(offset 기반, `page`/`size` 쿼리 파라미터)을 사용한다(사용자 확인 완료 — 코드베이스 첫 도입).
  - 정렬은 최신순(`createdAt DESC`) 고정. 정렬 옵션 파라미터는 이번 범위에서 다루지 않는다(HOME-001 인덱스 설계 `ix_product_status_created (sale_status, created_at DESC)`와 동일한 방향).
  - 공개 범위: `PROD-006` 상세 조회와 동일한 기준으로 `DRAFT`/`PRIVATE` 상태 상품은 목록에서 제외한다(비공개 상품은 목록에도 노출하지 않음). 그 외 상태(`ON_SALE`/`AUCTION_SCHEDULED`/`AUCTION_IN_PROGRESS`/`AUCTION_FAILED`/`SOLD`)는 판매 방식(`saleType`)과 무관하게 모두 포함한다.
  - Response: 페이지 메타(전체 개수/페이지 수/다음 페이지 여부)를 담는 공용 래퍼 `PageResponse<T>`(`global/response`, 신규)를 추가하고 `PageResponse<ProductResponse>`로 응답한다. Spring의 `Page<T>`를 그대로 직렬화하지 않고 필요한 필드만 평탄화한다(`content`, `page`, `size`, `totalElements`, `totalPages`, `hasNext`).
    - 항목 DTO는 기존 `ProductResponse`를 재사용한다(주석에 이미 "목록/생성에 쓰는 기존 ProductResponse"로 명시돼 있어 이번 목록 API가 그 용도에 해당).
  - 200 OK. 목록이 비어 있어도 200 + 빈 `content` 배열(에러 아님).
- Swagger 어노테이션(`@Operation`/`@ApiResponses`) 추가(401 케이스 명시).
- `ProductServiceTest`에 케이스 추가: 공개 상태 상품만 반환(DRAFT/PRIVATE 제외) / 페이지네이션 동작(2페이지 이상 데이터로 개수·다음 페이지 여부 확인) / 빈 결과 처리.
- `BE/README.md`는 이미 `product/` 패키지가 반영되어 있으므로 변경 불필요.

## 구현 목록

- [x] `PageResponse<T>` (`global/response`, 신규) — `content`, `page`, `size`, `totalElements`, `totalPages`, `hasNext`, `Page<T>` → 변환 정적 팩토리
- [x] `ProductRepository`에 `findBySaleStatusNotIn(List<SaleStatus>, Pageable)` 추가(또는 동등한 쿼리 메서드)
- [x] `ProductService.getProductList(Pageable pageable)` — `DRAFT`/`PRIVATE` 제외, `ProductResponse`로 매핑
- [x] `ProductController` — `GET /api/products` (`Pageable` 파라미터, Swagger 포함)
- [x] `ProductServiceTest` 케이스 3건 추가
- [x] `.claude/skills/verify` 기준 빌드/테스트 통과 확인

## 확인이 필요한 미결정 사항

- `page`/`size` 기본값과 `size` 상한은 스펙에 명시가 없어 구현 시 상식적인 기본값(`page=0`, `size=20`, 상한 `100`)으로 정한다. 화면 쪽 요구사항이 다르면 이후 조정.