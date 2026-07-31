# 상품 목록 필터·정렬 (PROD-008)

## 배경/목표

`GET /api/products`는 현재 페이지네이션과 DRAFT 제외만 지원하고, 정렬은 `createdAt DESC`로 고정되어 있으며 `sort` 파라미터를 보내도 무시된다(컨트롤러 주석에 명시). FE `PROD-008` 요구사항 문서(`FE/docs/frontend/screens/PROD-008/requirements.md`)는 카테고리/등급/가격범위/판매방식 필터와 최신순·가격순 정렬을 명시적으로 "후속 작업"으로 남겨뒀다. 이 API를 확장해 필터·정렬을 지원한다.

Jira: `S15P11A108-271`. 에픽 `S15P11A108-211`.

## 작업 내용

- `GET /api/products` 쿼리 파라미터 확장: `categoryIds`(복수), `conditionGrade`(복수), `saleType`(`DIRECT_SALE`/`AUCTION`), `minPrice`, `maxPrice`, `sort`(`LATEST`(기본값)/`PRICE_ASC`/`PRICE_DESC`).
- `ProductRepository`에 신규 필터 쿼리 메서드 추가. `LiveRepository.findPublicLives`(`live/repository/LiveRepository.java`)가 쓰는 "선택적 필터" JPQL 패턴(`(:flag = false OR p.x IN :xs)`)을 그대로 따른다 — 파라미터가 없으면 조건을 건너뛰는 boolean 플래그 방식.
- 정렬은 JPQL에 하드코딩하지 않고 서비스에서 `PageRequest.of(page, size, Sort.by(...))`로 구성해 넘긴다 — Spring Data가 `@Query` 메서드에도 `Pageable`의 `Sort`를 자동 반영한다.
- 컨트롤러 Swagger 설명에서 "sort 파라미터는 무시된다"는 기존 문구 제거하고 지원 값 문서화.
- `../../../../../APIs.md` 271 행에 쿼리 파라미터 갱신.

## 구현 목록

- [ ] `product/repository/ProductRepository.java` — 필터 쿼리 메서드 추가
- [ ] `product/service/ProductService.java` — `getProductList`에 필터/정렬 파라미터 처리 추가
- [ ] `product/controller/ProductController.java` — 쿼리 파라미터 바인딩, Swagger 설명 갱신
- [ ] `product/dto/request/`(필요시) 필터용 파라미터 객체 또는 개별 `@RequestParam`
- [ ] `../../../../../APIs.md` 271 행 갱신
- [ ] `ProductServiceTest`/리포지토리 슬라이스 테스트에 필터 조합·정렬 케이스 추가
- [ ] `BE:verify` 통과 확인

## 확인 필요한 미결정 사항

- 없음 (FE 요구사항 문서에 필터/정렬 후보가 이미 명시되어 있어 그대로 따름).
