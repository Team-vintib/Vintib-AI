import type { SearchFilterOption } from '@/domains/search/types/search.types'

export const SEARCH_CATEGORY_FILTER_OPTIONS: SearchFilterOption[] = [
  { id: '아우터', label: '아우터' },
  { id: '상의', label: '상의' },
  { id: '하의', label: '하의' },
  { id: '원피스', label: '원피스' },
  { id: '신발', label: '신발' },
  { id: '액세서리', label: '액세서리' },
  { id: '시계', label: '시계' },
]

export const SEARCH_CONDITION_FILTER_OPTIONS: SearchFilterOption[] = [
  { id: 'S', label: 'S급' },
  { id: 'A', label: 'A급' },
  { id: 'B', label: 'B급' },
  { id: 'C', label: 'C급' },
]

export const SEARCH_SALE_TYPE_FILTER_OPTIONS: SearchFilterOption[] = [
  { id: 'DIRECT', label: '즉시 구매' },
  { id: 'AUCTION', label: '경매' },
]
