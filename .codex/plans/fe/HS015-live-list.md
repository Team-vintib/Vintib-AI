# LIVE 라이브 목록 화면

## 배경/목표

상위 작업 `S15P11A108-217`의 공개 라이브 목록 화면을 구현한다.
현재 placeholder인 `/lives`를 실제 목록 화면으로 교체하고
`S15P11A108-413`, `S15P11A108-415`, `S15P11A108-418`을 순서대로 완료한다.

Jira 연결 항목에는 `LIVE-005 라이브 시청`이 표시되지만 세 하위 작업의 대상은
`라이브 목록`이다. 이번 작업은 `/lives` 목록과 목록 API만 다루며
`/lives/:liveId`의 영상, 채팅, 경매와 AI 시착은 포함하지 않는다.

## Jira별 구현 범위

### S15P11A108-413 — 라이브 목록 카드 UI 구현

- 라이브 도메인 전용 목록 타입과 mock 데이터를 정의한다.
- 카드형 목록과 `LIVE`, `예정`, `종료` 방송 상태 배지를 구현한다.
- 썸네일, 제목, 판매자, 시청자 수를 mock 데이터로 표시한다.
- 카드 이미지 대체 텍스트, 상태 텍스트와 키보드 focus를 제공한다.
- 카드 선택 시 기존 `LIVE_WATCH` route에 `liveId`를 전달한다.
- 공개 `/lives` route의 placeholder를 실제 목록 View로 교체한다.
- 실제 목록 API 호출은 제외한다.

### S15P11A108-415 — 라이브 목록 필터 반응 구현

- 카테고리, 정렬, 방송 상태 필터를 구현한다.
- 선택한 조건을 mock 목록과 결과 개수에 즉시 반영한다.
- 정렬 결과가 같은 경우에도 카드 순서가 불안정해지지 않도록 기준을 둔다.
- 필터의 현재 선택값과 결과 요약을 화면과 보조기술에 전달한다.
- 초기화 시 기본 필터와 전체 목록으로 돌아간다.
- 서버 필터링과 URL query 동기화는 제외한다.

### S15P11A108-418 — 목록 상태·반응형·API 연결

- 작업 시작 직전에 최신 `develop-FE`, `APIs.md`와 BE 라이브 API 문서를 다시 확인한다.
- API DTO와 FE 화면 모델을 분리하고 adapter에서 필드와 상태 enum을 매핑한다.
- 라이브 목록 조회 API를 연결해 실제 loading, empty, error, retry 상태를 처리한다.
- 필터 결과 없음 상태와 필터 초기화 동작을 제공한다.
- 목록 grid가 desktop, tablet, mobile에서 깨지지 않도록 최종 보강한다.
- API가 준비되지 않았거나 계약이 부족한 항목만 mock fallback으로 남기고 근거를 문서화한다.
- pagination 응답이면 전체 데이터를 받은 것처럼 클라이언트 필터링하지 않고
  서버 필터 parameter 필요 여부를 사용자에게 알린다.

## 예상 파일 구조

```text
FE/src/domains/live/
  api/
    liveListApi.ts
  components/
    LiveListCard.vue
    LiveListFilter.vue
    LiveListState.vue
  constants/
    liveListMockData.ts
  pages/
    LiveListView.vue
  types/
    liveList.types.ts

FE/docs/frontend/screens/LIVE-LIST/
  requirements.md
```

## 구현 목록

- [x] LIVE 목록 요구사항 문서 작성
- [x] 목록 타입과 mock 데이터 구성
- [x] 카드형 목록·상태 배지·기본 반응형 grid 구현
- [ ] 상태·카테고리·정렬 필터와 초기화 구현
- [ ] 결과 개수·선택 상태·접근성 구현
- [ ] 최신 BE API 문서와 FE view model 비교
- [ ] 목록 API adapter와 DTO 매핑 구현
- [ ] 실제 로딩·빈 목록·오류·재시도 상태 구현
- [ ] 필터 결과 없음과 최종 반응형 grid 보강
- [x] `/lives` placeholder를 실제 View로 교체
- [ ] route-map·현재 구조·구현 상태 문서 갱신
- [ ] lint·type-check·build와 수동 화면 검증

## BE API 확인 기준

- 카드 필수 필드: 라이브 ID, 썸네일, 제목, 판매자 표시명, 방송 상태, 시청자 수
- 필터 보조 필드: 카테고리, 정렬 기준 시간
- 상태 enum이 FE의 `LIVE`, `SCHEDULED`, `ENDED`와 다른지 확인한다.
- 응답 envelope와 pagination 구조가 공통 `ApiResponse` 규칙과 맞는지 확인한다.
- 필터·정렬 query parameter 제공 여부와 기본 정렬 기준을 확인한다.
- 계약에 없는 값은 임의로 확정하지 않고 mock 전용임을 표시한다.
- 추가 필드나 enum 협의가 필요하면 `.codex/requests/be/`에 요청 문서를 작성한다.

## Git 및 MR 작업 단위

- 기준: 최신 `origin/develop-FE`
- 브랜치: `feat/217-live-viewing`
- 커밋 1: `[S15P11A108-413] feat: 라이브 목록 카드 UI 구현`
- 커밋 2: `[S15P11A108-415] feat: 라이브 목록 필터 반응 구현`
- 커밋 3: `[S15P11A108-418] feat: 라이브 목록 상태 및 API 연동`
- 각 작업 종료 후 사용자가 해당 파일만 add·commit한다.
- 세 작업 완료 후 사용자가 push하고 MR을 생성한다.
- MR 제목: `[LIVE] 라이브 목록 탐색 화면 구현`
- MR 대상: `develop-FE`
