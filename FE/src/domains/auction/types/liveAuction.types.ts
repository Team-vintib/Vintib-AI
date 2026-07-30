export type LiveAuctionMockState =
  | 'BIDDABLE'
  | 'PENDING'
  | 'LEADING'
  | 'INSUFFICIENT_POINTS'

export interface LiveAuctionMockSnapshot {
  currentBid: number
  increment: number
  remainingSeconds: number
  highestBidder: string
  availablePoints: number
}
