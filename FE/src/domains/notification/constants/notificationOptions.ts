import { ROUTE_NAMES } from '@/shared/constants/routes'

import type {
  NotificationCategory,
  NotificationItemDto,
} from '@/domains/notification/types/notification.types'

export const NOTIFICATION_TABS = [
  { id: 'ALL', label: '전체' },
  { id: 'LIVE', label: '라이브' },
  { id: 'AUCTION', label: '경매' },
  { id: 'TRADE', label: '거래' },
  { id: 'SHIPPING', label: '배송' },
  { id: 'POINT', label: '포인트' },
] satisfies Array<{ id: NotificationCategory; label: string }>

export const NOTIFICATION_CATEGORY_LABELS: Record<NotificationCategory, string> = {
  ALL: '전체',
  LIVE: '라이브',
  AUCTION: '경매',
  TRADE: '거래',
  SHIPPING: '배송',
  POINT: '포인트',
}

export const NOTIFICATION_CATEGORY_ICONS: Record<Exclude<NotificationCategory, 'ALL'>, string> = {
  LIVE: 'broadcast',
  AUCTION: 'bid',
  TRADE: 'receipt',
  SHIPPING: 'truck',
  POINT: 'point',
}

export const getNotificationCategory = (
  type: string | null | undefined,
  refType: string | null | undefined,
): Exclude<NotificationCategory, 'ALL'> => {
  const tokens = `${type ?? ''} ${refType ?? ''}`.toUpperCase()

  if (tokens.includes('LIVE') || tokens.includes('BROADCAST')) return 'LIVE'
  if (tokens.includes('AUCTION') || tokens.includes('BID')) return 'AUCTION'
  if (tokens.includes('SHIP') || tokens.includes('DELIVERY')) return 'SHIPPING'
  if (tokens.includes('POINT') || tokens.includes('WALLET') || tokens.includes('WITHDRAW')) {
    return 'POINT'
  }

  return 'TRADE'
}

export const getNotificationRoute = (notification: Pick<NotificationItemDto, 'refType' | 'refId'>) => {
  const refType = notification.refType?.toUpperCase()
  const refId = notification.refId

  if (!refType || !refId) {
    return null
  }

  if (refType === 'LIVE') {
    return { name: ROUTE_NAMES.LIVE_WATCH, params: { liveId: refId } }
  }

  if (refType === 'PRODUCT') {
    return { name: ROUTE_NAMES.PRODUCT_DETAIL, params: { productId: refId } }
  }

  if (refType === 'POINT' || refType === 'WALLET') {
    return { name: ROUTE_NAMES.POINT }
  }

  if (refType === 'ORDER' || refType === 'SHIPMENT' || refType === 'SHIPPING') {
    return { name: ROUTE_NAMES.MY, query: { section: 'orders' } }
  }

  if (refType === 'AUCTION') {
    return { name: ROUTE_NAMES.MY, query: { section: 'auctions' } }
  }

  return null
}
