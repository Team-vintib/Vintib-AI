export type HomeLiveStatus = 'live' | 'scheduled'

export interface HomeLiveItem {
  id: number
  status: HomeLiveStatus
  title: string
  sellerName: string
  category: string
  thumbnailUrl: string
  representativeProductName: string
  viewerCount?: number
  reservationCount?: number
  startedAt?: string
  scheduledAt?: string
}

export type HomeProductSaleType = 'fixed' | 'auction'
export type HomeProductStatus = 'on_sale' | 'auction_scheduled'

export interface HomeProductItem {
  id: number
  saleType: HomeProductSaleType
  status: HomeProductStatus
  name: string
  sellerName: string
  brandName: string
  category: string
  imageUrl: string
  price?: number
  startingBid?: number
  auctionStartsAt?: string
  isWished: boolean
}

export type HomeContentAudience = 'guest' | 'member' | 'all'

export interface HomeContentItem {
  id: number
  title: string
  description: string
  imageUrl: string
  ctaLabel: string
  targetPath: string
  audience: HomeContentAudience
}

export interface HomeSellerItem {
  id: number
  name: string
  profileImageUrl: string
  description: string
  followerCount: number
}

export interface HomeMockData {
  liveNow: HomeLiveItem[]
  scheduledLives: HomeLiveItem[]
  fixedPriceProducts: HomeProductItem[]
  upcomingAuctions: HomeProductItem[]
  contents: HomeContentItem[]
  recommendedSellers: HomeSellerItem[]
  followingLives: HomeLiveItem[]
  followingProducts: HomeProductItem[]
}
