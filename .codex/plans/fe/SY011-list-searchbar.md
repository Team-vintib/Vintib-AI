# 목록 화면 공통 검색바 적용 계획

## 배경/목표

상품 목록(`/products`)과 라이브 목록(`/lives`) 상단에 홈 검색바와 같은 디자인의 검색바를
제공한다. 홈, 상품, 라이브에서 검색 UI가 중복 구현되지 않도록 공통 컴포넌트로 정리하고
기존 통합 검색 결과(`/search`) 흐름을 재사용한다.

## 확인한 기준

- `HomeSearchPanel.vue`는 46px 높이, 12px radius, 검색 아이콘 버튼, 인기 검색어 태그를 가진
  홈 전용 검색 UI다.
- `ProductListView.vue`에는 이미 자체 검색 폼이 있으나 홈과 디자인이 다르고, 현재는 화면
  조작 안내만 표시한다.
- `LiveListView.vue`에는 목록 검색 폼이 없다.
- `SearchResultsPage.vue`는 `keyword` query와 `type=product|live|member` query를 지원한다.
- `PROD-008` 요구사항은 상품 목록의 검색 입력을 포함하고, 실제 검색·query 동기화는 후속
  작업으로 분리되어 있다.
- `LIVE-LIST` 요구사항에는 검색 입력이 아직 명시되어 있지 않아 이번 작업에서 요구사항
  문서를 함께 갱신한다.

## 작업 내용

- 홈 검색바의 마크업과 스타일을 `shared/components`의 재사용 컴포넌트로 분리한다.
- 공통 검색바는 `v-model`, `placeholder`, `aria-label`, `submit` 이벤트, 선택적 인기 검색어
  태그를 props/events로 제공한다.
- 홈 화면은 기존 `HomeSearchPanel.vue`의 public UI를 유지하되 내부에서 공통 검색바를 사용하게
  바꾼다.
- 상품 목록의 기존 검색 폼은 공통 검색바로 교체한다.
- 라이브 목록은 페이지 header 아래, 필터/결과 content 위에 공통 검색바를 추가한다.
- 상품/라이브 목록 모두 타이틀·설명 영역 아래에 검색바를 배치한다.
- 상품 목록에서 검색 submit 시 `/search?keyword=<검색어>&type=product`로 이동한다.
- 라이브 목록에서 검색 submit 시 `/search?keyword=<검색어>&type=live`로 이동한다.
- 빈 검색어 submit은 상품/라이브 목록 맥락을 유지하도록 각 유형 query를 유지한다.
- 검색바 디자인은 홈 기준을 따른다. 단, 목록 화면에서는 인기 검색어 태그를 노출하지 않는다.
- 모바일에서는 홈 검색바와 동일하게 아이콘 버튼 중심의 compact 형태를 유지한다.
- 변경된 화면 요구사항과 구현 상태 문서를 갱신한다.

## 생성·수정할 파일

- 새 파일: `FE/src/shared/components/AppSearchBar.vue`
- 수정: `FE/src/domains/home/components/HomeSearchPanel.vue`
- 수정: `FE/src/domains/product/pages/ProductListView.vue`
- 수정: `FE/src/domains/live/pages/LiveListView.vue`
- 수정: `FE/docs/frontend/screens/PROD-008/requirements.md`
- 수정: `FE/docs/frontend/screens/LIVE-LIST/requirements.md`
- 수정: `FE/docs/frontend/implementation/current-structure.md`
- 수정: `FE/docs/frontend/implementation/status.md`

## 구현 목록

- [x] 홈 검색바의 공통화 가능한 props/events와 태그 표시 옵션 정의
- [x] `AppSearchBar.vue` 공통 컴포넌트 구현
- [x] 홈 검색 패널을 공통 검색바 기반으로 변경하고 기존 인기 검색어 UI 유지
- [x] 상품 목록 검색 폼을 공통 검색바로 교체
- [x] 라이브 목록 header 아래에 공통 검색바 추가
- [x] 상품/라이브 검색 submit 시 검색 결과 route와 유형 query 연결
- [x] 빈 검색어 submit의 type query 유지 여부 최종 반영
- [x] 요구사항·구현 상태 문서 갱신
- [x] `npm run lint`, `npm run type-check`, `npm run build` 검증
- [x] `/`, `/products`, `/lives`, `/search` route 응답 검증
- [ ] 브라우저 수동 화면 검증

## 확인이 필요한 미결정 사항

1. 상품/라이브 목록에서 빈 검색어를 제출하면 `/search?type=product|live`로 이동해 목록
   맥락의 결과 탭을 유지한다.
2. 홈은 기존처럼 `/search` 또는 `/search?keyword=...`로 이동해 전체 탭을 유지한다.

## 범위 제외

- 상품 목록 자체의 검색어 기반 로컬 필터링
- 라이브 목록 API에 검색 query parameter 추가
- 검색 결과 API 연동
- BE·AI 코드 변경
