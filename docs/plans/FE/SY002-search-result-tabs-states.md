# S15P11A108-401/S15P11A108-404 SEARCH-001/SEARCH-002 검색 결과 탭·상태 화면 계획

## 배경/목표

`SEARCH-001` 통합 검색은 키워드로 상품, 라이브, 회원 결과를 유형별로 구분해 보여야 하고, `SEARCH-002` 필터는 검색 조건 적용 후 결과 상태를 명확히 보여야 한다. 이번 작업은 `/search` 화면의 결과 탭 레이아웃과 검색 상태 화면을 먼저 구현해, 홈 검색 진입 이후 사용자가 검색 결과 영역의 구조와 로딩·빈·오류 상태를 확인할 수 있게 만드는 것을 목표로 한다.

## 확인한 기준

- Jira 범위는 `S15P11A108-401 [SEARCH-001/SEARCH-002 | FE] 검색 결과 탭 레이아웃 구현`, `S15P11A108-404 [SEARCH-001/SEARCH-002 | FE] 검색 상태 화면 구현`이다.
- 기능 정의서 기준 `SEARCH-001`은 상품·라이브·회원 검색 결과를 유형별로 구분한다.
- 기능 정의서 기준 `SEARCH-002`는 카테고리, 브랜드, 가격대, 상품 상태, 판매 방식 필터를 제공하며 경매 예정 상품은 가격대 필터에서 별도 처리가 필요하다.
- 이번 검색 결과 화면 필터는 상품 목록 화면과 맞춰 카테고리, 상태, 가격, 판매 유형(즉시 구매/경매)으로 구성한다. 브랜드 필터와 정렬은 실제 검색 API 계약 확정 후 별도 작업으로 둔다.
- 화면 요구 문서 기준 필요한 상태는 검색 결과 없음, 필터 결과 없음, 가격 범위 오류다.
- `ROUTE_PATHS.SEARCH`와 `ROUTE_NAMES.SEARCH`는 이미 존재하지만 `router/routes.ts`에는 아직 `/search` 실제 페이지 route가 없다.
- `domains/search` 하위 폴더는 구조만 있고 실제 화면 파일은 없다.
- 홈 검색 패널은 `/search?keyword=...`로 진입한다.
- 상품 목록 `PROD-008`에는 검색창, 필터 패널, 판매 방식 탭, 정렬, 상품 카드 그리드의 화면 확인용 구현이 있다.
- 현재 검색 API 계약은 `docs/frontend/api/api-index.md`에 확정되어 있지 않으므로 이번 작업은 임시 view model과 mock 상태로 제한한다.

## 작업 범위

- `/search` 공개 route를 실제 검색 결과 페이지에 연결한다.
- 검색어 query를 읽어 검색창 초기값과 결과 헤더 문구에 반영한다.
- 결과 유형 탭은 `전체`, `상품`, `라이브`, `회원`으로 구성하고 각 탭에 결과 수를 표시한다.
- 탭 전환 시 같은 화면 안에서 결과 영역만 전환되도록 만들고, 선택 상태는 접근 가능한 `tablist/tab/tabpanel` 구조로 표현한다.
- 상품 결과는 기존 `domains/product/components/ProductCard.vue` 재사용 가능성을 우선 검토한다.
- 라이브·회원 결과는 검색 도메인 전용 카드 컴포넌트로 얇게 구현한다.
- 필터 적용 결과 상태를 보여줄 수 있도록 검색 페이지 안에 필터 요약과 가격 범위 검증 메시지를 포함한다.
- 상태 화면은 초기 상태, 로딩, 검색 결과 없음, 필터 결과 없음, 오류, 가격 범위 오류를 분리해서 보여준다.
- 실제 API 대신 검색 도메인 mock data와 view model을 사용하고, API 전환이 쉬운 타입 경계를 둔다.
- 문서상 화면 구조·구현 상태·미확정 API 항목을 함께 갱신한다.

## 범위 제외

- 실제 검색 API 호출 구현
- 실제 필터 query 규격 확정
- 상품 상세, 라이브 시청, 회원 프로필 화면 구현
- 팔로우 API 호출과 인증 분기
- 찜 API 호출
- BE/AI 코드 수정
- Figma에 없는 신규 검색 추천 기능 추가

## 작업 내용

- `domains/search/pages/SearchResultsPage.vue`를 만들고 `DefaultLayout` 기반 검색 화면을 구성한다.
- 검색 결과 페이지 상단에 검색 입력, 검색어 요약, 전체 결과 수를 배치한다.
- 결과 탭 컴포넌트를 검색 도메인 안에 만들고, 탭별 count와 활성 상태를 URL 또는 내부 상태와 동기화한다.
- 결과 카드 영역은 상품, 라이브, 회원 목록을 각각 렌더링하되 빈 배열이면 상태 화면으로 대체한다.
- 검색 상태 컴포넌트를 만들어 empty/error/loading/filter-empty/validation-error 문구와 재검색·필터 초기화 CTA를 일관되게 표현한다.
- 카테고리, 상태, 가격, 판매 유형 필터는 이번 범위에서 실제 필터 API 호출 대신 mock 상품 결과와 화면 상태 검증만 담당한다.
- mock data는 검색 도메인 `constants` 또는 `api` adapter에 둬서 실제 API 교체 시 화면 컴포넌트 변경을 줄인다.
- 검색어가 없는 `/search` 진입은 초기 안내 상태로 처리한다.
- 검색어가 있고 mock 결과가 있는 경우 기본 탭은 `전체`로 보여준다.
- 검색어, 탭, 필터 상태 변경 시 `aria-live` 메시지로 결과 상태 변화를 보조한다.

## 생성·수정 예상 파일

- 신규: `FE/src/domains/search/pages/SearchResultsPage.vue`
- 신규: `FE/src/domains/search/components/SearchResultTabs.vue`
- 신규: `FE/src/domains/search/components/SearchStatePanel.vue`
- 신규: `FE/src/domains/search/components/SearchLiveResultCard.vue`
- 신규: `FE/src/domains/search/components/SearchMemberResultCard.vue`
- 신규: `FE/src/domains/search/types/search.types.ts`
- 신규: `FE/src/domains/search/constants/searchMockData.ts`
- 수정: `FE/src/router/routes.ts`
- 수정: `FE/docs/frontend/screens/screen-inventory.md`
- 수정: `FE/docs/frontend/flows/route-map.md`
- 수정: `FE/docs/frontend/api/api-index.md`
- 수정: `FE/docs/frontend/decisions/open-questions.md`
- 수정: `FE/docs/frontend/implementation/current-structure.md`
- 수정: `FE/docs/frontend/implementation/status.md`

## 구현 목록

- [x] `/search` route를 `SearchResultsPage.vue`에 연결
- [x] 검색어 query 초기화와 검색 submit 동작 정의
- [x] `전체/상품/라이브/회원` 결과 탭 레이아웃 구현
- [x] 탭별 결과 수와 활성 상태 표시
- [x] 상품 결과 카드 렌더링
- [x] 라이브 결과 카드 렌더링
- [x] 회원 결과 카드 렌더링과 팔로우 버튼 껍데기 구현
- [x] 검색 초기 상태 화면 구현
- [x] 로딩 상태 화면 구현
- [x] 검색 결과 없음 상태 화면 구현
- [x] 필터 결과 없음 상태 화면 구현
- [x] 오류 상태 화면과 재시도 CTA 구현
- [x] 최소/최대 가격 범위 오류 상태 구현
- [x] mock view model과 실제 API 대기 항목 문서화
- [x] 1440px, 1024px, 720px 이하 반응형 레이아웃 확인
- [x] `npm run type-check`, `npm run build` 검증

## 검증 시나리오

1. `/search` 직접 접근 시 검색어 입력을 유도하는 초기 상태가 보인다.
2. `/search?keyword=denim` 접근 시 검색어가 입력창과 결과 요약에 반영된다.
3. 결과 탭을 바꾸면 활성 탭과 결과 영역이 함께 바뀐다.
4. `전체` 탭에서는 상품, 라이브, 회원 결과 섹션이 한 화면에 구분되어 보인다.
5. 특정 탭에 결과가 없으면 전체 화면이 무너지지 않고 해당 빈 상태가 보인다.
6. mock 오류 상태에서는 오류 안내와 재시도 버튼이 보인다.
7. 최소 가격이 최대 가격보다 크면 가격 범위 오류가 보이고 필터 적용이 막힌다.
8. 키보드로 검색창, 탭, CTA, 카드 액션을 이동할 수 있고 focus가 보인다.
9. 모바일 폭에서 탭, 검색창, 상태 화면 텍스트가 겹치지 않는다.

## 확인 필요/미결정 사항

1. 실제 통합 검색 endpoint, request query, pagination envelope가 미확정이다.
2. 회원 결과 선택 시 이동할 회원 프로필 route가 아직 미확정이다.
3. 라이브 결과 카드에서 예정/진행/종료 상태별 CTA 정책이 미확정이다.
4. 팔로우 버튼은 인증 필요 여부와 실패 처리 정책이 미확정이므로 이번 작업에서는 UI 껍데기로 제한한다.
5. 경매 예정 상품의 가격대 필터 제외/포함 정책은 BE 계약 확정 후 실제 필터 로직에 반영한다.

## Git 작업 단위

- 브랜치 제안: `feat/401-search-result-tabs-states`
- 커밋 제안: `[S15P11A108-401][S15P11A108-404] feat: 검색 결과 탭 및 상태 화면 구현`
- push는 하지 않고, 사용자 승인 후 구현과 로컬 검증까지만 진행한다.
