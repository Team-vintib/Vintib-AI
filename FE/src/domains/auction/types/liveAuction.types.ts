export type AuctionStatus = 'READY' | 'RUNNING' | 'SUCCESS' | 'FAILED' | 'CANCELED'

export interface AuctionSnapshot {
  auctionId: number
  liveId: number
  productId: number
  productTitle: string | null
  status: AuctionStatus
  startPrice: number
  bidUnit: number
  durationSeconds: number
  currentPrice: number
  nextBidPrice: number
  highestBidderId: number | null
  highestBidderNickname: string | null
  bidCount: number
  startedAt: string | null
  endsAt: string | null
  endedAt: string | null
  extensionCount: number
  serverNow: string
}

export type AuctionEventType = 'AUCTION_STARTED' | 'BID_PLACED' | 'AUCTION_CLOSED'

export interface AuctionEventMessage {
  type: AuctionEventType
  auction: AuctionSnapshot
}

export interface AuctionConfigureRequest {
  productId: number
  startPrice: number
  bidUnit: number
  durationSeconds: number
}

export interface AuctionConfigured {
  id: number
  liveId: number
  productId: number
  startPrice: number
  bidUnit: number
  durationSeconds: number
  status: AuctionStatus
  currentPrice: number
  createdAt: string
}

export interface AuctionWinner {
  auctionId: number
  liveId: number
  productId: number
  status: AuctionStatus
  winnerId: number | null
  winnerNickname: string | null
  finalPrice: number | null
  bidCount: number
  endedAt: string | null
}

export type BroadcastSaleStatus = 'SOLD' | 'UNSOLD'
export type BroadcastSaleMethod = 'AUCTION' | 'DIRECT_SALE'

export interface BroadcastProductResult {
  productId: number
  title: string
  thumbnailUrl: string | null
  status: BroadcastSaleStatus
  finalPrice: number | null
  soldVia: BroadcastSaleMethod | null
}

export interface BroadcastEndSummary {
  soldCount: number
  unsoldCount: number
  totalSales: number
  results: BroadcastProductResult[]
}

export interface LiveUnsoldProduct {
  productId: number
  title: string
  thumbnailUrl: string | null
  startPrice: number
}
