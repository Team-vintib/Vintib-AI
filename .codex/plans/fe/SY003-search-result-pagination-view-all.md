# S15P11A108-401/S15P11A108-404 검색 결과 전체보기·페이지네이션 구현 계획

## 배경/목표

현재 `/search` 화면은 검색어와 필터를 기준으로 상품, 라이브, 회원 결과를 탭으로 구분해 보여준다.
다음 단계에서는 `전체` 탭에서 각 결과 묶음의 전체보기 진입을 제공하고, 검색 결과가 많아졌을 때
페이지 단위로 탐색할 수 있게 만든다. 실제 검색 API와 pagination envelope는 아직 BE 계약 대기 상태이므로
이번 작업은 mock result 기준 화면 동작과 URL query 구조까지만 구현한다.

## 확인한 현재 상태

- `/search`는 `type=all | product | live | member` query로 탭을 전환한다.
- `SearchResultTabs.vue`는 탭 선택 이벤트만 담당하고, 결과 렌더링은 `SearchResultsPage.vue`에 있다.
- 검색 결과 count는 `filteredProducts`, `visibleLives`, `visibleMembers` 기준으로 계산한다.
- 상품 결과 grid는 desktop에서 3열, 1180px 이하 2열, 720px 이하 1열로 되어 있다.
- 상품 목록 화면 `ProductListView.vue`에 페이지네이션 UI 패턴이 있다.
- 실제 통합 검색 API의 pagination 구조는 `.codex/requests/be/008-search-result-api-contract.md`로 BE 요청되어 있다.

## 작업 범위

- `전체` 탭에서 상품/라이브/회원 섹션 헤더에 `전체보기` 버튼을 추가한다.
- `전체보기`를 누르면 같은 `/search` 화면에서 `type=product | live | member` query로 이동한다.
- `전체` 탭은 섹션별 미리보기 개수를 제한한다.
  - 상품: 한 줄 3개 기준으로 3개 노출
  - 라이브: 3개 노출
  - 회원: 3개 노출
- `product`, `live`, `member` 개별 탭에서는 해당 유형 결과에 페이지네이션을 제공한다.
- 페이지 상태는 URL query `page`로 관리한다.
- 탭 변경, 검색어 변경, 필터 적용 시 `page=1`로 초기화한다.
- 결과 개수가 페이지당 개수 이하이면 페이지네이션은 숨긴다.
- 페이지네이션 버튼은 상품 목록 화면과 유사하게 이전/다음, 페이지 번호, `aria-current="page"`를 제공한다.
- 상품 grid는 desktop에서 한 줄 3개가 유지되도록 기존 3열 기준을 유지하고, preview도 같은 grid를 사용한다.

## 범위 제외

- 실제 검색 API 호출 구현
- BE pagination envelope 확정
- 서버 기준 정렬, cursor pagination, 무한 스크롤
- 상품/라이브/회원 상세 화면 신규 구현
- 찜/팔로우 API 연동

## 작업 내용

- `SearchResultsPage.vue`에 페이지 관련 computed/state를 추가한다.
  - `currentPage`
  - `itemsPerPage`
  - `pagedProducts`, `pagedLives`, `pagedMembers`
  - `totalPages`
  - `visiblePageNumbers`
- `전체` 탭과 개별 탭의 렌더링 데이터를 분리한다.
  - 전체 탭: `previewProducts`, `previewLives`, `previewMembers`
  - 개별 탭: 페이지네이션 적용 결과
- 섹션 헤더에 count와 `전체보기` 버튼을 함께 배치한다.
- 페이지네이션 nav UI와 스타일을 검색 화면에 추가한다.
- mock data가 페이지네이션을 확인하기에 부족하면 검색 도메인 mock data만 보강한다.
- 문서에는 mock pagination이며 실제 API 계약 대기 상태임을 남긴다.

## 수정 예상 파일

- 수정: `FE/src/domains/search/pages/SearchResultsPage.vue`
- 필요 시 수정: `FE/src/domains/search/constants/searchMockData.ts`
- 수정: `FE/docs/frontend/implementation/status.md`
- 수정: `FE/docs/frontend/flows/route-map.md`
- 수정: `FE/docs/frontend/api/api-index.md`
- 수정: `FE/docs/frontend/decisions/open-questions.md`

## 구현 체크리스트

- [ ] 전체 탭 섹션별 `전체보기` 버튼 추가
- [ ] `전체보기` 클릭 시 `type` query 전환
- [ ] 전체 탭 preview 개수 제한
- [ ] 개별 탭 페이지네이션 상태 계산
- [ ] `page` query 동기화와 탭/검색/필터 변경 시 초기화
- [ ] 검색 페이지 페이지네이션 UI와 접근성 속성 추가
- [ ] 상품 grid desktop 3열 유지 확인
- [ ] mock data 보강 필요 여부 확인
- [ ] 문서 갱신
- [ ] `npm run type-check`, `npm run build` 검증
- [ ] 1440px, 1024px, 720px 이하 반응형 확인

## 검증 시나리오

1. `/search?keyword=omega&type=all`에서 상품/라이브/회원 섹션 헤더에 전체보기 버튼이 보인다.
2. 전체 탭 상품 섹션은 desktop에서 한 줄 3개까지 보인다.
3. 상품 전체보기를 누르면 `/search?...&type=product&page=1`로 이동한다.
4. 개별 탭에서 결과가 여러 페이지면 페이지 번호와 이전/다음 버튼이 보인다.
5. 마지막 페이지에서 다음 버튼이 비활성화된다.
6. 검색어를 다시 제출하거나 필터를 적용하면 page가 1로 초기화된다.
7. 결과가 페이지당 개수 이하이면 페이지네이션이 보이지 않는다.
8. 720px 이하에서 페이지네이션 버튼과 카드가 겹치지 않는다.

## 확인 필요/미결정 사항

1. 실제 검색 API의 page/size query 이름과 pagination envelope는 BE 계약 대기 중이다.
2. `all` 탭에서 BE가 섹션별 preview를 내려줄지, FE가 탭별 endpoint를 조합할지는 미정이다.
3. 라이브/회원 결과의 최종 상세 route는 미정이다.

## Git 작업 단위

- 커밋 제안: `[S15P11A108-401][S15P11A108-404] feat: 검색 결과 전체보기 및 페이지네이션 구현`
