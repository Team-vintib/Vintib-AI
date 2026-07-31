# LIVE-005 시청자 화면 전체 구조

## 배경/목표

`S15P11A108-419`에서 현재 placeholder인 `/lives/:liveId`를 Figma 라이브 시청 화면의
전체 구조로 교체한다. 이번 작업은 영상 중심 레이아웃, 상품 큐, 방송 정보와 후속 패널의
배치 기준을 확정하며 실제 스트리밍·채팅·입찰·AI 시착 기능은 구현하지 않는다.

기존 `feat/217-live-viewing` 스토리 브랜치에서 이어서 작업하고, 하위 작업 단위인
`S15P11A108-419`로 커밋한다.

## 확인 자료

- Figma 배포 프로토타입의 라이브 시청 화면
  - 상단 방송 바
  - 왼쪽 상품 큐
  - 중앙 영상과 overlay 영역
  - 하단 선택 상품 정보
  - 오른쪽 경매·시착 후속 패널 영역
- `FE/docs/notion/화면 기반 개발 요구 문서.md`
- `FE/docs/notion/기능 정의서.md`
- `FE/docs/notion/프론트엔드 디자인 구현 규칙.md`
- 2026-07-30 로컬 Swagger `VinTib API v0.1`
- `origin/develop-BE@dd6a0b6`의 최종 `009-live-list-api-contract.md`와
  `LiveDetailResponse`
- 기존 `LiveLayout.vue`, 라이브 목록 route와 mock/adapter 구조

AI 시착 상세 팝업은 Figma 구성이 변경되었으므로 이번 작업에서 구현하거나 기존 시안을
확정값으로 사용하지 않는다.

## 구현 범위

### 라우트와 페이지

- `/lives/:liveId`의 `RoutePlaceholder`를 `domains/live/pages/LiveWatchPage.vue`로 교체한다.
- 기존 `LiveLayout`의 dark theme를 사용한다.
- route의 `liveId`를 화면 데이터 조회와 mock 식별자에 사용한다.

### 화면 구조

- 상단 방송 바
  - 뒤로가기
  - `LIVE` 상태
  - 방송 제목
  - 시청자 수와 방송 경과 시간의 배치
- 왼쪽 상품 큐
  - 상품 이미지, 상품명, 브랜드, 가격
  - 현재 소개 상품 `NOW` 상태
  - 선택 상품 변경
- 중앙 영상 영역
  - 실제 영상 대신 mock poster
  - 영상 비율과 빈 공간을 유지하는 media stage
  - 후속 채팅·이모지 반응이 들어갈 overlay 영역
- 하단 선택 상품 정보
  - 선택 상품 이미지와 기본 정보
  - 상품 상세 보기·찜 action 배치
  - 후속 AI 시착 action 영역
- 오른쪽 패널
  - 후속 경매 패널이 들어갈 너비와 스크롤 기준
  - 이번 작업에서는 상세 경매 UI를 구현하지 않고 배치 영역만 제공

### 화면 상태

- 기본 라이브 화면
- 초기 loading
- 라이브 조회 실패와 재시도
- 존재하지 않는 라이브
- 연결 상품 없음
- 방송 예정·진행·종료 상태의 표시 차이

상태 재현은 기존 화면 패턴처럼 query 또는 mock scenario로 분리한다.

### 컴포넌트 경계

```text
FE/src/domains/live/
  api/
    liveWatchApi.ts
  components/
    LiveWatchHeader.vue
    LiveProductQueue.vue
    LiveVideoStage.vue
    LiveSelectedProduct.vue
    LiveWatchSidePanel.vue
    LiveWatchState.vue
  constants/
    liveWatchMockData.ts
  pages/
    LiveWatchPage.vue
  types/
    liveWatch.types.ts
```

- LIVE 화면 전용 코드는 `domains/live`에 둔다.
- CHAT, AUCT, TRYON 도메인 구현을 이번 작업에서 만들지 않는다.
- 후속 작업은 위 영역 컴포넌트 내부 또는 명시된 확장 지점에 연결해 페이지 전체 충돌을 줄인다.
- 실제 두 개 이상의 도메인에서 재사용되기 전에는 `shared`로 이동하지 않는다.

## Swagger 확인 결과

현재 사용할 수 있는 시청 정보 endpoint는 다음과 같다.

```http
GET /api/lives/{liveId}
```

확인된 응답 필드:

- `id`, `hostId`, `hostNickname`
- `title`, `thumbnailUrl`, `status`
- `scheduledAt`, `startedAt`, `endedAt`
- `peakViewerCount`
- `products[]`
  - `id`, `liveId`, `productId`, `productTitle`, `sortOrder`, `addedAt`
- `categories[]`
  - `id`, `name`

주의:

- `peakViewerCount`는 현재 동시 시청자 수로 사용하지 않는다.
- 상품 큐에 필요한 이미지, 브랜드, 가격, 현재 소개 상품 여부는 계약에 없다.
- 영상 접속 토큰은 Swagger 설명상 별도 API 대상이지만 현재 endpoint가 없다.
- DTO와 FE view model을 분리하고, 계약에 없는 값은 mock 전용 필드로 명시한다.
- API가 완성되기 전에도 UI 작업을 검증할 수 있도록 mock adapter를 기본값으로 둔다.

## 구현하지 않는 범위

- WebRTC/OpenVidu/영상 SDK와 실제 재생
- 영상 접속 토큰 발급
- 채팅 메시지 목록·입력·전송·WebSocket
- 경매 현재가·최고 입찰자·입찰 버튼과 실시간 동기화
- AI 시착 진입 버튼의 Figma 기준 위치·형태는 전체 레이아웃에 포함한다.
- AI 시착 진입 상태와 변경된 상세 팝업
- 실제 팔로우·찜 API
- 낙찰·유찰 결과
- FE에서 임의로 확정한 실시간 event 또는 API 필드

## 문서 작업

- `FE/docs/frontend/screens/LIVE-005/requirements.md`를 작성한다.
- `FE/docs/frontend/flows/route-map.md`의 placeholder 상태를 갱신한다.
- `FE/docs/frontend/implementation/current-structure.md`를 갱신한다.
- `FE/docs/frontend/implementation/status.md`를 갱신한다.
- `009` 반영 이후 남은 BE 계약은
  `.codex/requests/be/012-live-watch-detail-contract-gaps.md`에 기록한다.

## 구현 목록

- [x] LIVE-005 화면 요구사항 문서 작성
- [x] 시청 화면 DTO, view model, mock scenario 정의
- [x] Swagger 기반 adapter와 mock fallback 구성
- [x] 라이브 상단 방송 바 구현
- [x] 상품 큐와 선택 상태 구현
- [x] mock 영상 stage와 후속 overlay 영역 구현
- [x] 선택 상품 정보와 후속 action 영역 구현
- [x] 오른쪽 후속 패널 영역 구현
- [x] loading·오류·없음·상품 없음·방송 상태 화면 구현
- [x] `/lives/:liveId` route를 실제 페이지로 교체
- [x] desktop 기준 Figma 비교와 1280px 실제 grid 폭 확인
- [x] 좁은 화면에서 주요 패널이 겹치지 않는 최소 반응형 보강
- [x] 구현 구조·상태·route 문서 갱신
- [x] lint·type-check·build 검증
- [x] 라이브 목록에서 시청 화면 진입과 상태별 수동 확인

## 검증 기준

1. `/lives/:liveId`가 placeholder가 아닌 dark live 화면을 표시한다.
2. Figma 기준 상품 큐·영상·상품 정보·오른쪽 패널의 정보 우선순위가 유지된다.
3. 상품을 선택하면 선택 표시와 하단 상품 정보가 함께 변경된다.
4. 실제 스트리밍 없이도 media stage가 레이아웃을 안정적으로 유지한다.
5. 후속 CHAT/AUCT/TRYON 구현이 들어갈 영역이 컴포넌트 경계로 분리되어 있다.
6. 계약에 없는 값을 실제 API 필드처럼 취급하지 않는다.
7. loading·오류·라이브 없음·상품 없음 상태가 확인 가능하다.

## 확인이 필요한 사항

- Figma의 채팅 overlay와 오른쪽 경매 패널의 최종 세부 크기는 후속 작업에서 확정한다.
- AI 시착 상세 팝업의 변경된 구성은 별도 TRYON 계획에서 다시 확인한다.
- 현재 동시 시청자 수, 현재 소개 상품과 상품 큐 표시 정보는 BE 계약 반영 전까지 mock이다.

## Git 및 MR 작업 단위

- 브랜치: `feat/217-live-viewing`
- 하위 작업: `S15P11A108-419`
- 커밋 후보: `[S15P11A108-419] feat: 라이브 시청 화면 전체 구조 구현`
- push는 사용자가 직접 수행한다.
- MR은 LIVE-005 스토리 단위이며 대상은 `develop-FE`다.

## 검증 결과

- 변경 파일 대상 ESLint 통과
- `npm.cmd run type-check` 통과
- `npm.cmd run build-only` 통과
- `/lives`의 LIVE 카드에서 `/lives/101` 이동 확인
- 1280px viewport에서 상품 큐 220px, 영상 stage 1060px, 하단 선택 상품 680px,
  오른쪽 경매 패널 380px과 가로 overflow 없음 확인
- 상품 선택 시 큐 선택 상태·하단 정보·오른쪽 선택 상품 동기화 확인
- `loading`, `error`, `not-found`, `empty-products`, `scheduled`, `ended` 상태 확인
- 종료 상태에서 현재 상품 `NOW` 배지가 표시되지 않는 것 확인
