# S15P11A108-401/S15P11A108-404 검색 결과 정렬 구현 계획

## 배경/목표

검색 결과 상품 탭에 상품 목록과 같은 선택형 정렬을 추가한다. 정렬 옵션은 `최신순`,
`가격 낮은순`, `가격 높은순` 3개만 제공한다. 실제 검색 API 정렬 query는 아직 BE 계약 대기
상태이므로 이번 작업은 `/search`의 `sort` query와 mock 상품 결과 정렬까지만 구현한다.

## 확인한 현재 상태

- 상품 목록 화면은 `select` 기반 정렬 UI를 사용한다.
- 검색 화면은 상품 결과를 `filteredProducts` computed에서 필터링한 순서 그대로 렌더링한다.
- 검색 결과 타입에는 최신순 정렬 기준으로 쓸 생성/등록 일시 필드가 없다.
- `FE/docs/frontend/api/api-index.md`에는 최신순·가격 낮은순·가격 높은순 정렬 값이 미확정 항목으로 남아 있다.

## 작업 범위

- 검색 결과 상품 영역 상단에 정렬 select를 추가한다.
- 정렬 옵션은 아래 3개로 제한한다.
  - `LATEST`: 최신순
  - `PRICE_ASC`: 가격 낮은순
  - `PRICE_DESC`: 가격 높은순
- 정렬 상태는 `/search` query의 `sort`로 동기화한다.
- 잘못된 `sort` query가 들어오면 `LATEST`로 처리한다.
- 정렬 변경 시 같은 검색/필터/탭 query를 유지하고 `sort`만 갱신한다.
- 상품 결과에만 정렬을 적용하고 라이브/회원 결과 순서는 유지한다.
- 최신순 정렬을 위해 search mock 상품에 `createdAt` 필드를 추가한다.

## 범위 제외

- 실제 검색 API 호출
- BE 정렬 query/value 확정
- 라이브/회원 정렬
- 정렬과 페이지네이션 동시 연동

## 수정 예상 파일

- 수정: `FE/src/domains/search/pages/SearchResultsPage.vue`
- 수정: `FE/src/domains/search/types/search.types.ts`
- 수정: `FE/src/domains/search/constants/searchMockData.ts`
- 필요 시 수정: `FE/docs/frontend/api/api-index.md`
- 필요 시 수정: `FE/docs/frontend/decisions/open-questions.md`

## 구현 체크리스트

- [x] 검색 정렬 타입/옵션 정의
- [x] mock 상품 `createdAt` 추가
- [x] `sort` query 파싱과 기본값 처리
- [x] 상품 결과 정렬 computed 추가
- [x] 상품 섹션 상단 정렬 select UI 추가
- [x] 정렬 변경 시 query 갱신
- [x] `npm run type-check`, `npm run build` 검증
- [x] 1440px, 720px 레이아웃 확인

## 검증 시나리오

1. `/search?keyword=a&type=product`에서 정렬 select가 보인다.
2. 기본값은 최신순이다.
3. 가격 낮은순을 선택하면 상품 가격이 낮은 순서로 정렬된다.
4. 가격 높은순을 선택하면 상품 가격이 높은 순서로 정렬된다.
5. 정렬을 바꿔도 검색어, 탭, 필터 query가 유지된다.
6. 잘못된 `sort` query는 최신순처럼 동작한다.

## Git 작업 단위

- 커밋 제안: `[S15P11A108-401][S15P11A108-404] feat: 검색 상품 결과 정렬 추가`
