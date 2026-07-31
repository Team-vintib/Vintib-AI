import type { LiveBroadcastStatus } from '@/domains/live/types/liveList.types'

export type LiveWatchStatus = LiveBroadcastStatus | 'CANCELED'

export type LiveWatchLoadState = 'loading' | 'success' | 'error' | 'not-found'

export type LiveWatchMockScenario =
  | 'default'
  | 'loading'
  | 'error'
  | 'not-found'
  | 'empty-products'
  | 'scheduled'
  | 'ended'

export type LiveProductSaleType = 'AUCTION' | 'FIXED_PRICE'

export interface LiveWatchProduct {
  id: number
  title: string
  brandName: string | null
  price: number | null
  thumbnailUrl: string | null
  saleType: LiveProductSaleType | null
  material: string | null
  condition: string | null
  measurements: string | null
  defectSummary: string | null
}

export interface LiveWatchCategory {
  id: number
  name: string
}

export interface LiveWatchViewData {
  id: number
  hostId: number
  hostNickname: string
  hostProfileImageUrl: string | null
  title: string
  description: string | null
  posterUrl: string | null
  status: LiveWatchStatus
  scheduledAt: string | null
  startedAt: string | null
  endedAt: string | null
  currentViewerCount: number | null
  peakViewerCount: number
  currentProductId: number | null
  products: LiveWatchProduct[]
  categories: LiveWatchCategory[]
}

export interface LiveCategoryDto {
  id: number
  name: string
}

export interface LiveProductDto {
  id: number
  liveId: number
  productId: number
  productTitle: string
  sortOrder: number
  addedAt: string
}

export interface LiveDetailDto {
  id: number
  hostId: number
  hostNickname: string
  title: string
  thumbnailUrl: string | null
  status: LiveWatchStatus
  scheduledAt: string | null
  startedAt: string | null
  endedAt: string | null
  peakViewerCount: number
  currentViewerCount?: number
  products: LiveProductDto[]
  categories?: LiveCategoryDto[]
}
