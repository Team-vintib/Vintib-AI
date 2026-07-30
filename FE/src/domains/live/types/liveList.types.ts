export type LiveBroadcastStatus = 'LIVE' | 'SCHEDULED' | 'ENDED'

export type LiveCategory = '아우터' | '상의' | '하의' | '가방' | '신발' | '액세서리'

export type LiveCategoryFilter = 'ALL' | LiveCategory

export type LiveStatusFilter = 'ALL' | Exclude<LiveBroadcastStatus, 'ENDED'>

export type LiveSortOption = 'LATEST' | 'VIEWERS_DESC' | 'TITLE_ASC'

export type LiveListLoadState = 'loading' | 'success' | 'error'

export type LiveListMockScenario = 'default' | 'loading' | 'empty' | 'error'

export interface LiveListFilterOption<T extends string> {
  id: T
  label: string
}

export interface LiveListItem {
  id: number
  title: string
  sellerName: string
  thumbnailUrl: string
  status: LiveBroadcastStatus
  viewerCount: number
  category: LiveCategory
  broadcastAt: string
}

export interface LiveListDto {
  liveId: number
  title: string
  hostId: number
  hostNickname: string
  thumbnailUrl: string | null
  broadcastStatus: LiveBroadcastStatus | 'CANCELED'
  categories?: {
    id: number
    name: string
  }[]
  categoryId?: number
  categoryName?: string
  scheduledAt: string | null
  startedAt: string | null
  viewerCount: number
}

export interface LiveListQuery {
  categoryId?: number
  status?: Exclude<LiveBroadcastStatus, 'ENDED'>
  sort?: LiveSortOption
  page: number
  size: number
}

export interface LiveListViewData {
  items: LiveListItem[]
  totalElements: number
  totalPages: number
}
