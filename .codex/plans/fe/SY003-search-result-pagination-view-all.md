# S15P11A108-401/S15P11A108-404 검색 결과 전체보기·페이지네이션 구현 계획

## 배경/목표

`/search` 화면의 `전체` 탭은 상품, 라이브, 회원 결과를 한 화면에 묶어 보여준다.
이번 작업은 `전체` 탭에서 각 섹션의 일부 결과만 preview로 보여주고, `전체보기`로 같은 검색 화면의 개별 탭에 진입할 수 있게 만드는 것이다. 개별 탭에서는 mock 결과 기준 페이지네이션을 제공한다.

실제 통합 검색 API와 pagination envelope는 BE 계약 대기 상태이므로 이번 작업은 FE mock result와 URL query 구조까지만 구현한다.

## 작업 범위

- `전체` 탭 상품/라이브/회원 섹션에 `전체보기` 버튼 추가
- `전체보기` 클릭 시 같은 `/search` 화면에서 `type=product | live | member` query로 전환
- `전체` 탭 섹션별 preview 개수 3개 제한
- `product`, `live`, `member` 개별 탭에 페이지네이션 추가
- 페이지 상태를 URL query `page`로 관리
- 탭 변경, 검색어 변경, 필터 적용, 정렬 변경 시 페이지를 1페이지로 초기화
- 결과 개수가 page size 이하이면 페이지네이션 숨김
- 페이지네이션 검증을 위한 검색 mock data 최소 보강
- FE 문서에 `page`, 전체보기, mock pagination 상태 기록

## 범위 제외

- 실제 검색 API 호출 구현
- BE pagination envelope 확정
- 서버 기준 정렬, cursor pagination, 무한 스크롤
- 상품/라이브/회원 상세 화면 신규 구현
- 찜/팔로우 API 연동

## 수정 파일

- `FE/src/domains/search/pages/SearchResultsPage.vue`
- `FE/src/domains/search/constants/searchMockData.ts`
- `FE/docs/frontend/implementation/status.md`
- `FE/docs/frontend/flows/route-map.md`
- `FE/docs/frontend/api/api-index.md`
- `FE/docs/frontend/decisions/open-questions.md`

## 구현 체크리스트

- [x] 전체 탭 섹션별 `전체보기` 버튼 추가
- [x] `전체보기` 클릭 시 `type` query 전환
- [x] 전체 탭 preview 개수 제한
- [x] 개별 탭 페이지네이션 상태 계산
- [x] `page` query 동기화와 검색/필터/정렬 변경 시 초기화
- [x] 검색 페이지 페이지네이션 UI와 접근성 속성 추가
- [x] 상품 grid desktop 3열 유지 확인
- [x] mock data 보강
- [x] 문서 갱신
- [x] `npm run type-check`, `npm run build` 검증
- [ ] 1440px, 1024px, 720px 이하 브라우저 캡처 확인

## 확인 필요/미결정 사항

- 실제 검색 API의 page/size query 이름과 pagination envelope는 BE 계약 대기 중이다.
- `all` 탭에서 BE가 섹션별 preview를 내려줄지, FE가 탭별 endpoint를 조합할지 미정이다.
- 라이브/회원 결과의 최종 상세 route는 미정이다.
- 현재 세션에서 연결 가능한 브라우저와 로컬 Playwright가 없어 캡처 검증은 수행하지 못했다.

## Git 작업 단위

커밋 제안: `[S15P11A108-401][S15P11A108-404] feat: 검색 결과 전체보기 및 페이지네이션 구현`
