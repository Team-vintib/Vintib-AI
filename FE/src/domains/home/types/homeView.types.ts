// Mock 전용 홈 화면 view model입니다.
// Swagger 또는 BE 응답 계약이 확정되면 API 응답 타입과 매핑 로직으로 교체합니다.

export type HomeLiveStatus = 'LIVE' | 'SCHEDULED'

export interface HomeLiveCardItem {
  id: number
  status: HomeLiveStatus
  title: string
  thumbnailUrl: string
  hostName: string
  scheduledAt?: string
  startedAt?: string
  viewerCount?: number
  reservationCount?: number
  categoryName?: string
}

export type HomeProductSaleType = 'DIRECT_SALE' | 'AUCTION'
export type HomeProductSaleStatus = 'ON_SALE' | 'AUCTION_SCHEDULED'

export interface HomeProductCardItem {
  id: number
  title: string
  saleType: HomeProductSaleType
  saleStatus: HomeProductSaleStatus
  primaryImageUrl: string
  sellerName: string
  price?: number
  startingBid?: number
  auctionStartsAt?: string
  brandName?: string
  categoryName?: string
  isWished?: boolean
}

export type HomeContentAudience = 'guest' | 'member' | 'all'

export interface HomeContentCardItem {
  id: number
  title: string
  description: string
  imageUrl: string
  ctaLabel: string
  targetPath: string
  audience: HomeContentAudience
}

export interface HomeViewMockData {
  liveNow: HomeLiveCardItem[]
  scheduledLives: HomeLiveCardItem[]
  directSaleProducts: HomeProductCardItem[]
  upcomingAuctionProducts: HomeProductCardItem[]
  contentCards: HomeContentCardItem[]
}
