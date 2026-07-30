import { http } from '@/shared/api/http'

import type {
  SearchLiveResult,
  SearchMemberResult,
  SearchProductResult,
  SearchResultTabId,
  SearchResultsViewModel,
  SearchSortOptionId,
} from '@/domains/search/types/search.types'
import type { ApiResponse } from '@/shared/types/api.types'

const SEARCH_API_ENABLED = import.meta.env.VITE_SEARCH_API_ENABLED === 'true'

interface SearchPageResponse<T> {
  items?: T[]
  content?: T[]
  meta?: {
    page: number
    size: number
    totalElements: number
    totalPages: number
  }
  page?: number
  size?: number
  totalElements?: number
  totalPages?: number
}

interface SearchResponse {
  products: SearchPageResponse<SearchProductResult>
  lives: SearchPageResponse<SearchLiveResult>
  members: SearchPageResponse<SearchMemberResult>
}

export interface SearchRequest {
  keyword: string
  type?: SearchResultTabId
  categories?: string[]
  conditions?: string[]
  saleTypes?: string[]
  minPrice?: number
  maxPrice?: number
  sort?: SearchSortOptionId
  page?: number
  size?: number
}

export const isSearchApiEnabled = () => SEARCH_API_ENABLED

export const searchUnified = async (request: SearchRequest): Promise<SearchResultsViewModel> => {
  if (!SEARCH_API_ENABLED) {
    throw new Error('Search API is disabled until the backend contract is implemented.')
  }

  const { data } = await http.get<ApiResponse<SearchResponse>>('/search', {
    params: toSearchParams(request),
    skipAuth: true,
  })

  if (!data.success || !data.data) {
    throw new Error(data.error?.message ?? '검색 결과를 불러오지 못했습니다.')
  }

  return {
    products: unwrapSearchPage(data.data.products),
    lives: unwrapSearchPage(data.data.lives),
    members: unwrapSearchPage(data.data.members),
  }
}

const toSearchParams = (request: SearchRequest) => ({
  keyword: request.keyword,
  type: request.type && request.type !== 'all' ? request.type : undefined,
  categories: request.categories?.length ? request.categories.join(',') : undefined,
  conditions: request.conditions?.length ? request.conditions.join(',') : undefined,
  saleTypes: request.saleTypes?.length ? request.saleTypes.join(',') : undefined,
  minPrice: request.minPrice,
  maxPrice: request.maxPrice,
  sort: request.sort,
  page: request.page,
  size: request.size,
})

const unwrapSearchPage = <T>(page: SearchPageResponse<T>) => page.items ?? page.content ?? []
