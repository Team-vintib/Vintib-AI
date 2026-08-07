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

export type AuctionBidStatus = 'ACTIVE' | 'OUTBID' | 'WON' | 'LOST'

export interface AuctionBidItem {
  bidId: number
  bidderId: number
  bidderNickname: string
  amount: number
  status: AuctionBidStatus
  createdAt: string
  isMine: boolean
}

export interface AuctionBidPage {
  content: AuctionBidItem[]
  nextCursor: number | null
  hasNext: boolean
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
  // BE 유찰 목록은 마지막 경매의 시작가를 준다. 경매를 건 적이 없는 미판매 상품은 FE가
  // 편성 상품 목록으로 채우는데 그때는 값이 없을 수 있다(정찰제는 등록가, 경매 예정은 null).
  startPrice: number | null
  // BE 응답에는 없고 FE가 편성 상품 목록(GET /lives/{id})에서 채우는 값. 상품 상세
  // (GET /products/{id})는 상품에 따라 500이 나기도 해서(요청 029) 여기에 의존하지 않는다.
  saleType?: 'DIRECT_SALE' | 'AUCTION' | null
}
