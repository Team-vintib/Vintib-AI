export type SearchResultTabId = 'all' | 'product' | 'live' | 'member'

export type SearchStateKind = 'initial' | 'loading' | 'empty' | 'filter-empty' | 'error' | 'price-error'

export interface SearchProductResult {
  id: number
  brand: string
  name: string
  sellerName: string
  price: number
  conditionGrade: 'S' | 'A' | 'B' | 'C'
  saleType: 'DIRECT' | 'AUCTION'
  categoryName: string
  imageUrl: string
  imageAlt: string
  isLiked: boolean
}

export interface SearchLiveResult {
  id: number
  title: string
  hostName: string
  status: 'LIVE' | 'SCHEDULED' | 'ENDED'
  scheduledAt?: string
  startedAt?: string
  productCount: number
  thumbnailUrl: string
}

export interface SearchMemberResult {
  id: number
  nickname: string
  profileImageUrl: string
  description: string
  followerCount: number
  productCount: number
  liveCount: number
  isFollowing: boolean
}

export interface SearchResultsViewModel {
  products: SearchProductResult[]
  lives: SearchLiveResult[]
  members: SearchMemberResult[]
}

export interface SearchResultTab {
  id: SearchResultTabId
  label: string
  count: number
}

export interface SearchFilterOption {
  id: string
  label: string
}

export interface SearchStateContent {
  title: string
  description: string
  actionLabel?: string
}
