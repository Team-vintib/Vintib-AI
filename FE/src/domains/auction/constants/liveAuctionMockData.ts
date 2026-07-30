import type {
  LiveAuctionMockSnapshot,
  LiveAuctionMockState,
} from '@/domains/auction/types/liveAuction.types'

export const LIVE_AUCTION_MOCK_STATES: LiveAuctionMockState[] = [
  'BIDDABLE',
  'PENDING',
  'LEADING',
  'INSUFFICIENT_POINTS',
]

export const LIVE_AUCTION_MOCK_SNAPSHOT: LiveAuctionMockSnapshot = {
  currentBid: 39_000,
  increment: 3_000,
  remainingSeconds: 187,
  highestBidder: 'user1',
  availablePoints: 125_000,
}
