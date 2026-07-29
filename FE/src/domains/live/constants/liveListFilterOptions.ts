import type {
  LiveCategoryFilter,
  LiveListFilterOption,
  LiveSortOption,
  LiveStatusFilter,
} from '@/domains/live/types/liveList.types'

export const LIVE_CATEGORY_FILTER_OPTIONS: LiveListFilterOption<LiveCategoryFilter>[] = [
  { id: 'ALL', label: '전체' },
  { id: '아우터', label: '아우터' },
  { id: '상의', label: '상의' },
  { id: '하의', label: '하의' },
  { id: '가방', label: '가방' },
  { id: '신발', label: '신발' },
  { id: '액세서리', label: '액세서리' },
]

export const LIVE_STATUS_FILTER_OPTIONS: LiveListFilterOption<LiveStatusFilter>[] = [
  { id: 'ALL', label: '전체' },
  { id: 'LIVE', label: '진행 중' },
  { id: 'SCHEDULED', label: '방송 예정' },
]

export const LIVE_SORT_OPTIONS: LiveListFilterOption<LiveSortOption>[] = [
  { id: 'LATEST', label: '최신 방송순' },
  { id: 'VIEWERS_DESC', label: '시청자 많은순' },
  { id: 'TITLE_ASC', label: '제목순' },
]
