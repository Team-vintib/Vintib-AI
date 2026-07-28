# 검색 결과 화면 API 계약 보완 요청

- **요청한 파트**: FE
- **대상 파트**: BE
- **관련 티켓**: `S15P11A108-401`, `S15P11A108-404`
- **관련 화면**: `SEARCH-001`, `SEARCH-002`, `/search`

## 배경/이유

FE 검색 결과 화면은 상품, 라이브, 회원 결과를 탭으로 구분하고 카테고리·상태·가격·판매 유형 필터를 제공하도록 구현되어 있습니다.
상품 결과는 최신순·가격 낮은순·가격 높은순 정렬을 제공하고, `전체` 탭에서는 섹션별 preview와 `전체보기` 진입을 제공합니다.
현재는 실제 검색 API 계약이 없어 `domains/search`의 mock data를 클라이언트에서 필터링하고 있습니다.

## 요청 내용

- 통합 검색 조회 API 계약 확정을 요청합니다.
  - 단일 endpoint 예시: `GET /api/search`
  - 또는 상품/라이브/회원 탭별 endpoint 분리 여부 확정 필요
- FE가 현재 사용하는 query 후보는 아래와 같습니다.
  - `keyword`: 검색어
  - `type`: `all | product | live | member`
  - `page`: 페이지 번호. `product`, `live`, `member` 개별 탭에서 사용하며 `all` 탭과 1페이지에서는 생략합니다.
  - `categories`: 상품 카테고리 복수 선택
  - `conditions`: 상품 상태 등급 복수 선택
  - `saleTypes`: `DIRECT | AUCTION`
  - `minPrice`, `maxPrice`: 가격 범위
  - `sort`: `LATEST | PRICE_ASC | PRICE_DESC`
- 실제 API에서 확정이 필요한 항목은 아래와 같습니다.
  - 탭별 결과 count 제공 방식
  - pagination 요청/응답 구조와 `page`, `size`, `totalPages`, `totalElements` 등 envelope 필드명
  - `all` 탭에서 상품/라이브/회원 결과를 몇 개까지 내려줄지
  - `all` 탭의 `전체보기` 진입 시 개별 탭 API를 다시 호출할지, 같은 응답의 full list를 사용할지
  - 상품 정렬 기준과 query 값. FE 후보는 `LATEST`, `PRICE_ASC`, `PRICE_DESC`입니다.
  - 상품 결과 DTO의 가격, 판매 유형, 상태 등급, 썸네일, 찜 여부 필드
  - 상품 결과 DTO의 최신순 정렬 기준 필드. FE mock은 `createdAt`을 사용합니다.
  - 라이브 결과 DTO의 상태, 시작 일시, 시청자 수, 썸네일, 연결 상품 수 필드
  - 회원 결과 DTO의 닉네임, 프로필 이미지, 팔로워 수, 판매 상품 수, 팔로우 여부 필드
- 검색 결과에서 필요한 사용자 액션 API 정책 확인을 요청합니다.
  - 상품 찜 등록/해제 endpoint와 비로그인 클릭 시 처리 정책
  - 회원 팔로우 등록/해제 endpoint와 비로그인 클릭 시 처리 정책
  - 회원 검색 결과 카드 클릭 시 이동할 회원 프로필 route 또는 조회 endpoint

## FE 임시 처리

- `/search` route는 공개 접근으로 연결되어 있습니다.
- `keyword`, `type`, `page`, `sort`, 필터 query를 URL에 반영하고 mock data에서 결과를 필터링합니다.
- `전체` 탭은 상품/라이브/회원 섹션별 3개 preview를 보여주고, `전체보기` 클릭 시 같은 `/search` 화면에서 `type=product|live|member`로 이동합니다.
- `product`, `live`, `member` 개별 탭은 mock data 기준 페이지네이션을 제공합니다.
- 검색어 변경, 탭 변경, 필터 적용, 정렬 변경 시 FE는 `page`를 1페이지로 초기화합니다.
- `status=loading|error|empty` query는 FE 상태 화면 확인용 mock query이며 실제 API query가 아닙니다.
- 비로그인 상태에서 찜/팔로우를 누르면 `/auth/login?redirect=...`로 이동합니다.
- 로그인 상태의 찜/팔로우는 화면 안에서만 mock toggle 처리합니다.

## 관련 자료

- FE 계획: `.codex/plans/fe/SY002-search-result-tabs-states.md`
- FE 화면: `FE/src/domains/search/pages/SearchResultsPage.vue`
- FE 타입: `FE/src/domains/search/types/search.types.ts`
- FE mock data: `FE/src/domains/search/constants/searchMockData.ts`
- FE API 후보 문서: `FE/docs/frontend/api/api-index.md`
- FE 미확정 문서: `FE/docs/frontend/decisions/open-questions.md`
