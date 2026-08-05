# HS023 — AUCT-012/013 낙찰 축하 이벤트

- Jira: S15P11A108-434 (`[AUCT-012/013 | FE] 낙찰 축하 이벤트 UI 구현`) / 에픽 S15P11A108-209 [AUCT]
- 브랜치: `feat/209-chat-auction-panel` (에픽 209 재사용)

## 배경 / 목표

기능 정의서 **AUCT-013 낙찰 결과 연출**: 경매 종료 시 낙찰자 닉네임(전체)과 낙찰 가격을 **라이브 방송 화면 위에 크게 강조**하고 **폭죽 등 축하 효과**를 준다(최고 입찰자 표시보다 크게). AUCT-012 낙찰 처리(포인트 차감·주문 생성)는 BE 소관. FE는 **경매 종료 후 라이브 화면 위 축하 오버레이**를 구현한다. BE에 낙찰 결과 조회·경매 종료/낙찰 실시간 트리거 API가 없어 **mock 트리거로 구현**하고, 필요한 API는 `docs/requests/BE`에 요청한다. (레퍼런스 없음 → 현재 라이브 다크 테마에 맞춰 디자인.)

## 현황

- 낙찰 축하 UI **없음**(신규 구현).
- `LiveAuctionPanel`(경매 패널): mock 상태 `BIDDABLE|PENDING|LEADING|INSUFFICIENT_POINTS` + 파생 `SCHEDULED|ENDED|EMPTY`. "최고 입찰자" 표시 있음. 낙찰(WON) 개념 없음.
- `LiveWatchPage`: 영상 스테이지 + 채팅/시착/경매 패널 조립. `?auction=` 쿼리로 경매 mock 상태 주입 중.
- BE: `POST /api/lives/{liveId}/auctions`(경매 설정)만 존재. 입찰·낙찰 결과·경매 STOMP **전부 없음**. (`AuctionStatus`에 SUCCESS/FAILED enum만 있음)

## 작업 내용 (구두)

1. **낙찰 축하 오버레이 컴포넌트 신설**(auction 도메인, 예: `LiveAuctionResultOverlay.vue`): 낙찰자 닉네임 + 낙찰가를 크게 강조, 폭죽/축하 효과, 다크 라이브 테마. reduce-motion 대응.
2. **`LiveWatchPage`에 오버레이 연결**: 경매 결과가 낙찰(WON)일 때 **영상 스테이지 위**에 표시. mock 트리거는 기존 `?auction=` 쿼리에 `won`(및 `failed`) 시나리오 추가.
3. **mock 상태·데이터 추가**: `LiveAuctionMockState`에 `WON`(+ `FAILED` 미낙찰) 추가, mock 낙찰자 닉네임·낙찰가 상수 추가. 경매 패널도 종료/낙찰 상태 표기 정합.
4. **없는 API 문서화**(늘 하던 대로) → `docs/requests/BE/005-auction-chat-contract.md`: 낙찰 결과 조회 + 경매 종료/낙찰 확정 실시간(STOMP 토픽), AUCT-012/013. (입찰 관련은 다음 작업 AUCT-003~006에서 함께 정리)

## 구현 목록

- [x] `LiveAuctionResultOverlay.vue` 신설 (낙찰자 닉네임+낙찰가 강조 + 폭죽 축하 효과, 다크 테마, reduce-motion)
- [x] `LiveWatchPage`에 오버레이 연결 (경매 종료 낙찰 시 영상 스테이지 위 표시, `?auction=won` mock, 닫기)
- [x] `LiveAuctionMockState`에 `WON`/`FAILED` + `LIVE_AUCTION_MOCK_RESULT`(낙찰자/낙찰가)
- [x] `docs/requests/BE/009`(3.2 winner · 3.3 AUCTION_CLOSED)에 낙찰 연출용 필드(닉네임·낙찰가) 명시 — 낙찰 결과/실시간 요청은 009에 이미 존재
- [x] 폭죽 → **팝업 뒤에서 위로 터지는 불꽃놀이**(방사형 버스트)로 변경
- [x] Vue 화면 확인: `?auction=WON`(대문자)에서 축하 오버레이·불꽃 표시·닫힘 (사용자 확인 완료)

## 확인 필요 (미결정)

- 폭죽 효과 구현 방식(경량 CSS 애니메이션 우선, canvas는 과함). reduce-motion 시 효과 정지.
- 오버레이 자동 닫힘(몇 초 후) vs 수동 닫기 버튼 — 기본안: 축하 표시 유지 + 닫기 버튼(경매 종료 상태로 복귀).
