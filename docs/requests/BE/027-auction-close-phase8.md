# 027 경매 종료·낙찰 확정(Phase 8) 실 API/이벤트 요청

- **요청자 파트**: FE (김현수)
- **대상 파트**: BE
- **관련 이슈**: FE `S15P11A108-566` [AUCT-002~006] 경매 시작·입찰 실 API/실시간 연결
- **작성일**: 2026-08-04

## 배경 / 이유

경매 **시작·입찰** 계약(`docs/requests/FE/024`·`025`)은 정의돼 있어 FE가 연결할 수 있지만,
**경매 종료·낙찰 확정(Phase 8)** 이 BE에 아직 구현되지 않아(`docs/plans/BE/JY008` Phase 8, `-467`)
FE가 경매 API 연결(#1)을 **끝까지 못 합니다.** 종료 이벤트가 없으면 낙찰/유찰 결과·낙찰 축하·
미판매 처리 흐름이 계속 mock에 머뭅니다.

## 요청 내용

경매 종료·낙찰 관련 실 API/이벤트를 구현해 주세요:

- **경매 종료(close)** — 진행 시간 만료/수동 종료 시 상태 전이.
- **낙찰자 확정(winner)** + 상품 상태: 낙찰이면 `SOLD`, 유찰이면 `AUCTION_SCHEDULED`(자동 복원 —
  `007` 예비답변 기준).
- **실시간 종료 이벤트(`AUCTION_CLOSED`)** — STOMP 경매 네임스페이스(`001`에서 예약됨)로 낙찰자·
  최종가·유찰 여부 전달.
- **`AUCTION_WON` 알림** — `docs/requests/FE/027` §2에서 예고된 낙찰 알림.

정의되면 FE가 `024`/`025` + 종료 이벤트로 경매 연결(#1)을 마무리합니다.

## 관련 자료

- FE 계약: `docs/requests/FE/024-auction-snapshot-start-contract.md`, `025-auction-bid-contract.md`
- BE 계획: `docs/plans/BE/JY008-live-screen-complete.md` (Phase 8)
- 관련: `docs/requests/BE/007-unsold-product-disposition.md`, `018-live-broadcast-end-summary.md`
