# LIVE-003 판매자 방송 화면

## 배경/목표

시청자 화면(`LiveWatchPage`)은 완성돼 있으나 **판매자 방송(송출) 화면은 없다.** 방송 생성
(`LiveCreatePage`)까지만 있고, 개설 후 판매자가 방송을 진행하는 화면이 비어 있다.
스토리 `S15P11A108-86 [LIVE-003] 라이브 상품 연결 및 관리` 아래에서 판매자 방송 화면을
만든다. 이 문서는 두 하위 작업을 한 파일로 관리한다.

- **435 판매자 방송 화면 구조** (이번 작업, SP2)
- **437 상품 전환·종료 버튼** (같은 브랜치 다음 작업, SP1)

시청자와 달리 판매자는 **AI 시착이 없고**, 대신 경매 설정(436)·상품 전환·방송 종료 같은
**판매자 제어 영역**이 들어간다. 이번 작업(435)은 그 영역들의 자리를 잡는 **큰 틀**까지만
만들고, 경매 설정 UI(436)와 전환·종료 동작(437)은 placeholder slot으로 비워 둔다.
(시청자 화면을 구조→패널 순으로 만든 것과 같은 방식: HS016 → HS017.)

## 기준 자료

- Figma 판매자 방송 화면(있으면 그 기준, 없으면 시청자 화면 레이아웃을 판매자용으로 변형)
- 기존 `LiveWatchPage.vue`와 하위 컴포넌트(`LiveWatchHeader`, `LiveProductQueue`,
  `LiveVideoStage`, `LiveWatchState`, `LiveChatOverlay`)
- `docs/requests/FE/001-live-stomp-contract.md` (실시간 계약 현황)
- `LiveCreatePage.vue`의 개설 완료 후 이동 흐름

## 작업 내용 (435 — 이번 작업)

### 라우트와 진입

- `shared/constants/routes.ts`에 `LIVE_BROADCAST` 추가.
  - path: `/lives/:liveId/broadcast`, name: `LIVE_BROADCAST`, `requiresAuth: true`.
- `LiveCreatePage`의 즉시 방송(`IMMEDIATE`) 완료 액션(`라이브 시작`)을 시청자 화면
  (`LIVE_WATCH`)이 아니라 **판매자 방송 화면(`LIVE_BROADCAST`)**으로 이동하도록 연결한다.
- route의 `liveId`로 방송 데이터를 조회한다.

### 화면 구조 (다크 `LiveLayout` 재사용)

- **상단 방송 바** — `LiveBroadcastHeader.vue`(신규, 판매자용)
  - 방송 제목, `LIVE` 상태, 경과 시간, 현재 시청자 수
  - 오른쪽에 **방송 종료 버튼 자리**(437 slot) + 나가기
  - 시청자용 헤더의 팔로우 버튼은 없다
- **왼쪽 상품 큐** — 기존 `LiveProductQueue.vue` 재사용
  - 현재 소개 상품 `NOW` 표시, 상품 선택
  - "다음 상품으로 전환" 트리거 자리(437 slot)는 큐 하단 액션 영역으로 비워 둠
- **중앙 영상** — 기존 `LiveVideoStage.vue` 재사용
  - 실제 송출 대신 mock poster (OpenVidu/WebRTC는 범위 밖)
  - **AI 시착 버튼은 판매자 화면에서 숨김** (prop으로 비활성/미표시)
  - 채팅 overlay slot에 기존 `LiveChatOverlay.vue` 재사용(판매자도 채팅을 본다)
- **오른쪽 패널** — 판매자 제어 영역
  - 상단: **방송 정보**(제목·대표 브랜드·상품 수·경과·시청자) — `LiveBroadcastInfo.vue`(신규)
  - 하단: **경매 설정 패널 placeholder slot**(436에서 채움)
- **하단/큐 영역**: 상품 관리(전환)·방송 종료 액션 placeholder(437에서 채움)

### 상태 화면

- loading / 조회 실패·재시도 / 존재하지 않는 라이브 / 연결 상품 없음
- 시청자 화면과 동일하게 `LiveWatchState.vue` 재사용, mock scenario는 query로 분리
- 판매자 전용 상태(내 방송이 아님 등)는 이번엔 mock 표시만, 실제 판정은 BE 확인

### API / mock 경계

- 방송 상세는 `GET /api/lives/{liveId}` 재사용(시청자와 같은 계약). 어댑터는 기존
  `liveWatchApi`의 view data를 재사용하거나 얇은 broadcast 어댑터로 감싼다.
- **계약에 없는 판매자 전용 값**(방송 소유자 여부, 경매 설정 상태, 방송 제어 응답)은
  `Mock 전용`으로 명시하고 실제 API처럼 쓰지 않는다.
- 실시간(상품 전환 `/topic/.../product` = Phase 5 ⏳, 경매 `/topic/.../auction` = Phase 6~8 ⏳)은
  아직 미제공 → 이번 구조 작업에서는 연결하지 않는다. 판매자 제어 계약이 필요하면
  437·436 작업에서 `docs/requests/BE/`에 요청 문서를 남긴다.

### 컴포넌트 경계

```text
FE/src/domains/live/
  pages/LiveBroadcastPage.vue        # 신규 — 판매자 방송 화면 조립
  components/
    LiveBroadcastHeader.vue          # 신규 — 판매자 상단 바(+종료 버튼 slot)
    LiveBroadcastInfo.vue            # 신규 — 방송 정보 패널
    LiveProductQueue.vue             # 재사용
    LiveVideoStage.vue               # 재사용(시착 숨김)
    LiveWatchState.vue               # 재사용
  api/liveBroadcastApi.ts            # 신규(얇게) 또는 liveWatchApi 재사용
  types/liveBroadcast.types.ts       # 판매자 view model(필요 시)
  constants/liveBroadcastMockData.ts # 판매자 mock 시나리오
```

- 경매 설정(436)·전환/종료(437)는 위 slot 안에 후속 연결 → 페이지 충돌 최소화
- 실제 두 도메인 이상에서 재사용되기 전에는 `shared`로 옮기지 않는다

## 구현하지 않는 범위 (435)

- OpenVidu/WebRTC 실제 송출·영상 토큰
- 경매 설정 UI 동작(436), 상품 전환·방송 종료 동작(437)
- STOMP 실시간 연결(채팅 overlay는 기존 구현 그대로 재사용)
- FE에서 임의 확정한 판매자 제어 API 필드

## 구현 목록 (435)

- [x] `LIVE_BROADCAST` route 추가, 개설(즉시) 완료 → 판매자 방송 화면 이동 연결
- [x] 방송 상세는 시청자 view model(`LiveWatchViewData`)·mock·`liveWatchApi` 재사용
      (별도 broadcast api/types/mock 파일은 만들지 않음 — 같은 `GET /api/lives/{liveId}` 계약)
- [x] `LiveBroadcastHeader`(제목·상태·경과·시청자 + 종료 버튼 slot) 구현
- [x] 상품 큐 재사용 배치(+전환 액션 slot)
- [x] 영상 stage 재사용(`show-try-on=false`로 시착 숨김) + 채팅 overlay 배치
- [x] `LiveBroadcastInfo` + 경매 설정 placeholder slot 배치
- [x] loading·오류·없음 상태 구현(`LiveWatchState` 재사용)
- [x] `LiveBroadcastPage`로 전체 조립, 데스크톱 3열 레이아웃 확인
- [x] 좁은 화면 최소 반응형 보강(1100/900px)
- [x] 변경 파일 ESLint·`type-check`·`build-only` 검증 통과
- [x] 실행 화면에서 사용자 배치 확인 완료(mock 모드로 확인)

### 435 구현 메모

- `LiveVideoStage`에 `showTryOn?: boolean`(기본 true) prop 추가 — 판매자는 false로 AI 시착 숨김.
  시청자 화면은 prop 미전달로 기존 동작 유지.
- 상품 큐 선택은 동작함(선택 → 경매 설정 slot 문구 연동). 전환/종료/경매 설정은 placeholder.
- 신규: `pages/LiveBroadcastPage.vue`, `components/LiveBroadcastHeader.vue`,
  `components/LiveBroadcastInfo.vue`. 변경: `routes.ts`(상수·라우트), `LiveVideoStage.vue`,
  `LiveCreatePage.vue`(즉시 방송 완료 이동 대상).

## 작업 내용 (437 — 상품 전환·종료 버튼)

435에서 자리만 잡아둔 판매자 제어 두 개를 동작하게 만든다. 실제 서버 반영은 계약이 없어
로컬 상태 전환(mock)까지만 하고, 필요한 엔드포인트는 `docs/requests/BE/013`으로 요청한다.

### 상품 전환 (넘어가는 알림)

- 큐에서 상품을 선택한 뒤 **"선택 상품으로 전환"** 버튼으로 현재 소개 상품(`NOW`)을 그 상품으로 바꾼다.
- 로컬로 현재 상품 id를 갱신(`currentProductId`를 페이지 로컬 상태로 승격) → 큐 `NOW` 배지·방송 정보 반영.
- 전환 시 화면에 **전환 알림 토스트**("‘상품명’(으)로 넘어갔습니다")를 잠깐 띄운다.
- 선택 상품이 이미 현재 상품이거나 `LIVE`가 아니면 버튼 비활성.
- **시청자에게 가는 실제 알림**(시스템 메시지 / `/topic/lives/{id}/product`)은 BE Phase 5 → 이번엔 mock,
  계약은 013 요청. 판매자 화면 채팅 overlay에 직접 주입하지 않는다(채팅은 BE 소유).

### 방송 종료

- 헤더 **방송 종료** 버튼 → **확인 모달**("방송을 종료할까요?") → 확정 시 로컬 상태 `ENDED`로 전환.
- 종료 후: 제어 버튼 비활성 + 영상 위 종료 안내(+"라이브 목록으로").
- 실제 종료 API(라이브 상태 전환)는 BE 미확정 → mock, 계약은 013 요청.

### 컴포넌트 경계

- `LiveBroadcastPage.vue`에 상태(`currentProductId` 로컬 승격, `hasEnded`, 전환 토스트)와
  핸들러(`transitionToSelectedProduct`, `requestEndBroadcast`/`confirmEndBroadcast`)를 추가.
- 확인 모달·토스트는 페이지 내부 마크업으로 최소 구현(별도 공용 컴포넌트로 빼지 않는다).
- 헤더의 종료 버튼은 435에서 이미 이벤트만 연결돼 있음 → 확인 모달로 연결.

## 구현하지 않는 범위 (437)

- 실제 상품 전환/종료 서버 반영, STOMP 브로드캐스트, 시청자 시스템 메시지
- 미낙찰 상품 후처리(PROD-005)·경매 시작(AUCT-002, 436 이후)
- 종료 후 정산/요약 화면

## 구현 목록 (437)

- [x] "선택 상품으로 전환" 버튼 동작 — 로컬 `live` view data의 `currentProductId`를 선택 상품으로 갱신
- [x] 전환 버튼 비활성 조건(선택=현재 상품 또는 `LIVE` 아님)
- [x] 전환 알림 토스트(2.6초 후 자동 사라짐)
- [x] 방송 종료 확인 모달 + 확정 시 로컬 `ENDED` 전환·`endedAt` 세팅·제어 비활성
- [x] 종료 안내 오버레이(+라이브 목록으로)
- [x] `docs/requests/BE/013-live-seller-control.md` 작성(방송 종료·현재 상품 전환 트리거·시청자 알림)
- [x] 변경 파일 ESLint·type-check·build-only 검증 통과
- [x] 실행 화면에서 전환(NOW 이동·토스트)·종료(모달·종료 상태) 동작 확인

### 437 구현 메모

- 별도 로컬 ref 대신 `live.value`(view data)를 갱신하는 방식으로 전환/종료를 표현
  (`{ ...live.value, currentProductId }`, `{ ...live.value, status: 'ENDED', endedAt }`).
  자식 컴포넌트(큐 `NOW`·헤더 상태·영상 stage)가 그대로 반영됨.
- 시청자에게 가는 실제 전환/종료 전파는 mock(화면 토스트·오버레이)까지만. 계약은 `013` 요청.

## Git / MR 단위 (재확인)

- 브랜치: `feat/217-live-product-management` (435와 동일, 이어서 커밋)
- 커밋: `[S15P11A108-437] feat: 상품 전환·종료 버튼 구현`
- 435+437 완료 후 스토리 86 단위 MR: `[LIVE] 판매자 방송 화면` → `develop-FE`

## Git / MR 단위

- 브랜치: `feat/217-live-product-management` (스토리 86 단위, `origin/develop-FE`에서 분기)
- 커밋(작업 단위·한글):
  - `[S15P11A108-435] feat: 판매자 방송 화면 구조 구현`
  - `[S15P11A108-437] feat: 상품 전환·종료 버튼 구현`
- MR: 스토리 86 완료(435+437) 시 `[LIVE] 판매자 방송 화면` → `develop-FE`
- push는 사용자가 직접 수행한다.
