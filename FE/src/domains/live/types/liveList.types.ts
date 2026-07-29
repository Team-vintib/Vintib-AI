export type LiveBroadcastStatus = 'LIVE' | 'SCHEDULED' | 'ENDED'

export type LiveCategory = '아우터' | '상의' | '하의' | '가방' | '신발' | '액세서리'

export type LiveCategoryFilter = 'ALL' | LiveCategory

export type LiveStatusFilter = 'ALL' | Exclude<LiveBroadcastStatus, 'ENDED'>

export type LiveSortOption = 'LATEST' | 'VIEWERS_DESC' | 'TITLE_ASC'

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
