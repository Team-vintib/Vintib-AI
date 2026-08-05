import type {
  LiveAuctionMockSnapshot,
  LiveAuctionMockState,
  LiveAuctionResult,
} from '@/domains/auction/types/liveAuction.types'

export const LIVE_AUCTION_MOCK_STATES: LiveAuctionMockState[] = [
  'BIDDABLE',
  'PENDING',
  'LEADING',
  'INSUFFICIENT_POINTS',
  'WON',
  'FAILED',
]

export const LIVE_AUCTION_MOCK_SNAPSHOT: LiveAuctionMockSnapshot = {
  currentBid: 39_000,
  increment: 3_000,
  remainingSeconds: 187,
  highestBidder: 'user1',
  availablePoints: 125_000,
}

// 낙찰 축하 연출(AUCT-013) mock 결과. 실제 낙찰자/낙찰가는 BE 낙찰 결과 API 연결 후 대체한다.
export const LIVE_AUCTION_MOCK_RESULT: LiveAuctionResult = {
  winnerNickname: 'vintage_hunter',
  winningBid: 51_000,
}
