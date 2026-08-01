// 판매자 경매 설정 패널(AUCT-001/002)의 로컬 view model.
// 실제 경매 설정·시작 트리거, 진행 중 실시간, 종료 판정은 BE 계약 없음 → 전부 mock.
// 관련 요청: docs/requests/BE/009(경매 이벤트), docs/requests/FE/001(경매 토픽 Phase 6~8).

export type SellerAuctionPhase = 'IDLE' | 'RUNNING' | 'ENDED_WON' | 'ENDED_FAILED'

export interface SellerAuctionConfig {
  startPrice: number
  increment: number
  durationSeconds: number
}

export interface SellerAuctionDurationPreset {
  label: string
  seconds: number
}
