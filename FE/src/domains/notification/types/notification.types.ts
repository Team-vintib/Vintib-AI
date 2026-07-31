import type { RouteLocationRaw } from 'vue-router'

import type { PageMeta } from '@/shared/types/api.types'

export type NotificationCategory = 'ALL' | 'LIVE' | 'AUCTION' | 'TRADE' | 'SHIPPING' | 'POINT'

export type NotificationLoadState = 'idle' | 'loading' | 'success' | 'error'

export type NotificationMockScenario = 'default' | 'loading' | 'empty' | 'error'

export interface NotificationItemDto {
  id: number
  type: string
  title: string
  body: string | null
  refType: string | null
  refId: number | null
  isRead: boolean
  createdAt: string
}

export interface NotificationItem {
  id: number
  type: string
  title: string
  body: string
  refType: string | null
  refId: number | null
  isRead: boolean
  createdAt: string
  category: NotificationCategory
  route: RouteLocationRaw | null
}

export interface NotificationListResult {
  items: NotificationItem[]
  meta: PageMeta
  hasNext: boolean
}

export interface NotificationReadAllResult {
  updatedCount: number
}
