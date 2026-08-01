export type LiveAuctionMockState =
  | 'BIDDABLE'
  | 'PENDING'
  | 'LEADING'
  | 'INSUFFICIENT_POINTS'
  | 'WON'
  | 'FAILED'

export interface LiveAuctionMockSnapshot {
  currentBid: number
  increment: number
  remainingSeconds: number
  highestBidder: string
  availablePoints: number
}

export interface LiveAuctionResult {
  winnerNickname: string
  winningBid: number
}
