# HS025 — AUCT-012/013 판매자 방송 종료 대시보드·낙찰 이벤트

- Jira: `S15P11A108-441`(`[AUCT-012/013 | FE] 판매자 낙찰 이벤트 UI 구현`),
  `S15P11A108-438`(`[AUCT-012/013 | FE] 방송 종료 대시보드 구현`)
  / 스토리 `S15P11A108-101`[AUCT-012/013] 낙찰 확정·결과 연출 / 에픽 `S15P11A108-209`[AUCT]
- 브랜치: `feat/209-auction-result-reveal` (스토리 101, `origin/develop-FE` 기준 신규)

## 배경/목표

판매자 방송 화면(`LiveBroadcastPage`)에 경매 종료 후 두 가지를 붙인다.

- **441 판매자 낙찰 이벤트**: 판매자 경매가 낙찰로 끝나면 방송 영상 위에 낙찰자·낙찰가 **축하 연출**을 띄운다(시청자 434와 대칭).
- **438 방송 종료 대시보드**: 방송이 종료(`ENDED`)되면 판매자에게 **방송 요약 대시보드**(상품별 낙찰/미낙찰·집계)를 보여준다. 이때 오른쪽 경매 설정 패널이 그대로 남지 않는다.

실제 경매 종료/낙찰 결과·방송 요약 API가 없어 **mock**으로 구현하고, 필요한 계약은 009/013에 정리한다.

## 기준 자료

- 시청자 낙찰 축하: `LiveAuctionResultOverlay.vue`(props `winnerNickname`/`winningBid`/`productTitle`,
  emit `close`) — **재사용 대상**. `HS023-auction-win-celebration`(434).
- 판매자 경매 패널 `SellerAuctionPanel.vue`(phase `IDLE`/`RUNNING`/`ENDED_WON`/`ENDED_FAILED`),
  `HS024-auction-setup-panel`.
- 판매자 방송 화면 `LiveBroadcastPage.vue`(`HS023-seller-broadcast`) — 종료 시 현재는 작은
  "방송을 종료했습니다" 오버레이만 있음.
- 사용자 결정([[auct-end-dashboard-leftover-disposition]]): 종료 시 **미낙찰(남은) 상품**은
  "경매 재시도 vs 상시 판매" 선택으로 이어지고(→ 440), **다 팔렸으면 그 섹션은 없음**.
- BE: `docs/requests/BE/009`(경매 snapshot/start/bid/close/winner·STOMP **전부 요청 중 = 미제공**),
  `013`(방송 종료 트리거).

## 작업 내용

### 441 판매자 낙찰 이벤트 (먼저)

- `SellerAuctionPanel`이 경매 종료 시 결과를 **상위로 emit**한다.
  예: `auction-ended` payload `{ result: 'WON' | 'FAILED', winnerNickname, winningBid, productTitle }`.
  (지금은 패널 내부 `phase`만 바뀌고 밖으로 안 알림 → emit 추가)
- `LiveBroadcastPage`가 이를 받아 **낙찰(WON)** 일 때 **영상 스테이지 위에
  `LiveAuctionResultOverlay` 재사용** 표시 + 닫기.
- 미낙찰(FAILED)은 오버레이 없음(패널 표기 유지).
- 트리거는 mock(패널 mock 경매 타이머 종료 시점). 실제 `AUCTION_CLOSED`/winner는 009 대기.

### 438 방송 종료 대시보드 (다음)

- `live.status === 'ENDED'`가 되면 브로드캐스트 본문을 **판매자 종료 대시보드**로 전환한다
  (현재의 작은 종료 오버레이 대체, **오른쪽 경매 설정 패널이 남지 않게**).
- 대시보드 내용(mock 집계):
  - 방송 요약: 방송 시간, 최고/현재 시청자, 연결 상품 수
  - **상품별 결과**: 낙찰(낙찰자·낙찰가) / 미낙찰 / (경매 안 함) 구분
  - **미낙찰 상품이 있으면** → "남은 상품 처리(경매 재시도/상시 판매)" 진입 섹션(실제 처리 UI는 440).
    **미낙찰이 없으면 이 섹션 숨김.**
  - "라이브 목록으로" 등 마무리 액션.
- 데이터는 mock(방송 결과 요약 API 없음). 계약 필요분은 013/009에 정리.

## API / mock 경계

- 경매 종료·낙찰 결과·방송 요약 전부 계약 없음 → **mock**. 계약에 없는 값은 `Mock 전용` 명시.
- 009(경매 close/winner·STOMP)·013(방송 종료 트리거)에 이미 요청 존재 → 필요 시 **방송 요약 필드만
  보강**(중복 요청 금지).

## 구현하지 않는 범위

- 실제 경매 종료/낙찰 확정·주문 생성(AUCT-012, BE)·STOMP 실연결
- 미낙찰 상품의 실제 처리 인터랙션(**440**)·PROD-005 판매방식 등록 화면
- 시청자 화면 변경(434 완료)

## 구현 목록

- [ ] `SellerAuctionPanel` 경매 종료 결과 emit(WON/FAILED + 낙찰자·낙찰가·상품명)
- [ ] `LiveBroadcastPage`에서 WON 시 `LiveAuctionResultOverlay` 재사용 표시·닫기(영상 위)
- [ ] 판매자 낙찰 연출 확인 경로(mock 시나리오)
- [ ] `live.status==='ENDED'` 시 방송 종료 대시보드로 전환(경매 설정 패널 미노출)
- [ ] 대시보드: 방송 요약 + 상품별 결과(낙찰/미낙찰) + 미낙찰 처리 진입 섹션(있을 때만)
- [ ] 종료 대시보드 mock 데이터·시나리오(전부 낙찰 / 일부 미낙찰)
- [ ] (필요 시) 009/013에 방송 요약 필드 보강
- [ ] 변경 파일 ESLint·`type-check`·`build-only`
- [ ] 실행 화면에서 낙찰 연출·종료 대시보드(미낙찰 유/무) 사용자 확인

## 확인 필요 (미결정)

- **종료 대시보드 배치**: **본문 전체 전환으로 확정**(사용자 결정) — 종료 시 3열 방송 레이아웃을 종료
  대시보드 화면으로 교체(경매 설정 패널이 확실히 사라짐).
- 판매자 낙찰 오버레이를 시청자와 **100% 동일 컴포넌트로 재사용**할지, 판매자 문구(예: "낙찰 완료·정산
  안내")를 살짝 다르게 할지.
- **438과 440의 경계**: 대시보드의 "미낙찰 처리" 섹션은 진입/목록까지(438), 실제 경매 재시도·상시판매
  선택 동작은 440.

## Git / MR 단위

- 브랜치: `feat/209-auction-result-reveal`
- 커밋(작업 단위·한글):
  - `[S15P11A108-441] feat: 판매자 낙찰 이벤트 UI 구현`
  - `[S15P11A108-438] feat: 방송 종료 대시보드 구현`
- MR: 스토리 101 완료(441+438) 시 `[AUCT] 낙찰 확정·결과 연출` → `develop-FE`
  (브랜치 다시 안 쓸 때 한 번). push는 사용자가 직접.
