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

/**
 * STOMP `/topic/lives/{liveId}/product-sold` payload — 정찰제 즉시구매로 상품이 팔렸다는 알림.
 *
 * 경매 낙찰은 이 토픽으로 오지 않는다(`/auctions`의 `AUCTION_CLOSED`가 그대로 담당). 양쪽에서
 * 쏘면 같은 상품을 두 번 처리하게 돼 BE가 일부러 나눠 놓았다.
 *
 * 전파 대상 방송은 주문 요청의 `liveId`가 아니라 편성 정보로 정해진다 — 상품 상세에서 산
 * 경우에도 그 상품이 진행 중 방송에 편성돼 있으면 시청자 큐에서 빠진다.
 */
export interface ProductSoldMessage {
  liveId: number
  productId: number
  saleStatus: 'SOLD'
  soldVia: 'DIRECT_SALE'
  soldAt: string
}
