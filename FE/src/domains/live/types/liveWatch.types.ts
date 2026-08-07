import type { LiveBroadcastStatus } from '@/domains/live/types/liveList.types'

export type LiveWatchStatus = LiveBroadcastStatus | 'CANCELED'

export type LiveWatchLoadState = 'loading' | 'success' | 'error' | 'not-found'

export type LiveWatchMockScenario =
  'default' | 'loading' | 'error' | 'not-found' | 'empty-products' | 'scheduled' | 'ended'

export type LiveProductSaleType = 'AUCTION' | 'DIRECT_SALE'

// BE SaleStatus (docs/requests/FE/035 §3-1) — 라이브 상품 응답에도 이 값이 실려 온다.
export type LiveProductSaleStatus =
  'DRAFT' | 'ON_SALE' | 'AUCTION_SCHEDULED' | 'AUCTION_IN_PROGRESS' | 'SOLD'

export interface LiveWatchProduct {
  id: number
  title: string
  brandName: string | null
  price: number | null
  thumbnailUrl: string | null
  saleType: LiveProductSaleType | null
  saleStatus: LiveProductSaleStatus | null
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
  isHost: boolean
  isReminderSet: boolean
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
  brandName?: string | null
  price?: number | null
  saleType?: LiveProductSaleType | null
  saleStatus?: LiveProductSaleStatus | null
  conditionGrade?: string | null
  material?: string | null
  measurements?: Record<string, number> | null
  defectSummary?: string | null
  thumbnailUrl?: string | null
  sortOrder: number
  addedAt: string
}

export interface LiveDetailDto {
  id: number
  hostId: number
  hostNickname: string
  hostProfileImageUrl?: string | null
  isHost?: boolean
  isReminderSet?: boolean
  title: string
  thumbnailUrl: string | null
  description?: string | null
  status: LiveWatchStatus
  scheduledAt: string | null
  startedAt: string | null
  endedAt: string | null
  peakViewerCount: number
  currentViewerCount?: number
  currentProductId?: number | null
  products: LiveProductDto[]
  categories?: LiveCategoryDto[]
}

/**
 * STOMP `/topic/lives/{liveId}/status` payload (BE `LiveStatusResponse`).
 * datetime은 오프셋 없는 KST 벽시계 — 그대로 `new Date`로 파싱한다.
 */
export interface LiveStatusMessage {
  liveId: number
  status: LiveWatchStatus
  startedAt: string | null
  endedAt: string | null
}

/**
 * STOMP `/topic/lives/{liveId}/product` payload (BE `CurrentProductResponse`).
 * 상품 상세는 싣지 않고 ID만 온다 — 편성 목록에서 찾아 NOW 배지를 옮긴다.
 */
export interface CurrentProductMessage {
  liveId: number
  currentProductId: number | null
}
