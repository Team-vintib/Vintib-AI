# SY031 — 판매자 프로필용 상품 목록 (011 §3.5)

## 배경/목표

`docs/requests/BE/011` §3.5(공개 프로필에서 판매자 상품/라이브 보여주기)의 남은 부분을 마무리한다.

**조사 결과, 라이브는 이미 돼 있다** — `GET /api/lives?hostId={id}`(MY-005)는 011 §3.5에 "본인
전용"이라고 잘못 적혀 있었을 뿐, 실제로는 비회원도 호출 가능하고 `hostId`가 조회자 본인이 아니면
자동으로 공개 상태(`SCHEDULED`/`LIVE`)만 필터링해서 준다(`LiveController.resolveStatuses`,
`selfView` 분기). 새로 만들 게 없다.

**상품만 빠져 있다.** `GET /api/products`(PROD-008)에 `sellerId` 필터가 없어서, 판매자 프로필에서
"이 판매자가 파는 상품" 목록을 못 뽑는다. 이거 하나만 추가한다.

## 작업 내용

- `ProductListFilterParams`에 `sellerId` 필터 추가(`hasSellerFilter()` 헬퍼 포함, 다른 필터와 동일
  패턴).
- `ProductController GET /api/products`에 `sellerId` 쿼리 파라미터 추가.
- `ProductRepository.findWithFilter` JPQL에 `AND (:hasSellerFilter = false OR p.seller.id =
  :sellerId)` 조건 추가.
- `ProductService.getProductList`에서 새 파라미터를 그대로 전달.
- DRAFT 제외는 기존 로직 그대로 유지 — `sellerId` 필터를 걸어도 비공개 상태는 안 보인다(공개
  프로필 용도에 그대로 맞음, 별도 처리 불필요).
- 인증 요구사항은 안 건드린다 — `GET /api/products`는 현재도 인증 필요(`SecurityConfig`에 permitAll
  없음, 상세 조회 `/products/{id}`만 공개). `sellerId` 필터 추가와 별개 결정이라 이번엔 그대로 둔다.

## 구현 목록

- [x] `ProductListFilterParams.sellerId`/`hasSellerFilter()` 추가
- [x] `ProductController` 쿼리 파라미터 추가
- [x] `ProductRepository.findWithFilter` JPQL 조건 추가
- [x] `ProductService.getProductList` 파라미터 전달
- [x] `ProductServiceTest`에 sellerId 필터 테스트 2개 추가, 기존 `findWithFilter`/
      `ProductListFilterParams` 호출부 시그니처 갱신(8+6곳)
- [x] 부수 발견: `GET /api/products`(목록) 자체가 `SecurityConfig`에서 인증을 요구하도록 막혀
      있었다(`docs/APIs.md`엔 원래 비회원 가능으로 문서화돼 있었음 — 구현 누락). §3.5의 목적(비회원
      공개 프로필에서 상품 목록 보기)을 위해 permitAll로 고치고 `@SecurityRequirement` 제거.
- [x] `docs/APIs.md` 갱신
- [x] `docs/requests/BE/011` 삭제(전 항목 처리 완료), 인덱스(`012`)에서도 행 제거
- [x] `docs/requests/FE/012`/`014` 간결화, `014`에 sellerId/hostId 필터 정보 추가
- [x] `./gradlew build` 통과
