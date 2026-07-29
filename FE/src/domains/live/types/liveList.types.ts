export type LiveBroadcastStatus = 'LIVE' | 'SCHEDULED' | 'ENDED'

export type LiveCategory = '아우터' | '상의' | '하의' | '가방' | '신발' | '액세서리'

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
