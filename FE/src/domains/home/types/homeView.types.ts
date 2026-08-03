// 홈 화면 view model입니다.
// API 응답은 domains/home/api adapter에서 이 화면 모델로 변환합니다.

export type HomeLiveStatus = 'LIVE' | 'SCHEDULED'

export interface HomeLiveCardItem {
  id: number
  status: HomeLiveStatus
  title: string
  thumbnailUrl: string
  hostName: string
  scheduledAt?: string
  startedAt?: string
  scheduledProductCount?: number
  viewerCount?: number
  reservationCount?: number
  categoryName?: string
}

export type HomeProductSaleType = 'DIRECT_SALE' | 'AUCTION'
export type HomeProductSaleStatus = 'ON_SALE' | 'AUCTION_SCHEDULED' | 'RESERVED' | 'SOLD_OUT'

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

export interface HomeFollowedSellerItem {
  id: number
  liveId?: number
  name: string
  profileImageUrl: string
  coverImageUrl: string
  specialty: string
  followerCount: number
  followingCount: number
  newProductCount: number
  liveCount: number
  liveStatus?: HomeLiveStatus
  liveTitle?: string
  liveAt?: string
}

export interface HomeRecommendedProductItem extends HomeProductCardItem {
  recommendationReason: string
}

export interface HomeCategoryProductSection {
  id: string
  title: string
  categoryName: string
  products: HomeProductCardItem[]
}

export interface HomeViewData {
  liveNow: HomeLiveCardItem[]
  scheduledLives: HomeLiveCardItem[]
  directSaleProducts: HomeProductCardItem[]
  upcomingAuctionProducts: HomeProductCardItem[]
  followedSellers: HomeFollowedSellerItem[]
  recommendedProducts: HomeRecommendedProductItem[]
  categoryProductSections: HomeCategoryProductSection[]
}
