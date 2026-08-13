import type { SearchFilterOption } from '@/domains/search/types/search.types'

// 카테고리 필터는 getCategories()+buildProductCategoryOptions()(productApi.ts)로 실제 BE
// 카테고리 마스터에서 구한다 — 등록/상품목록 화면과 같은 패턴(SY046). 하드코딩 목록은 제거.

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
