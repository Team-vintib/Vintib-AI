import { http } from '@/shared/api/http'

import type {
  SearchLiveResult,
  SearchMemberResult,
  SearchProductResult,
  SearchResultTabId,
  SearchResultsViewModel,
  SearchSortOptionId,
} from '@/domains/search/types/search.types'
import type { ApiResponse, PageMeta } from '@/shared/types/api.types'

const SEARCH_API_ENABLED = true

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

interface SearchProductDto {
  productId: number
  name: string
  brand?: string | null
  thumbnailUrl?: string | null
  sellType?: string | null
  sellStatus?: string | null
  price?: number | null
  auctionScheduled?: boolean
  sellerName?: string | null
  categoryName?: string | null
  isWished?: boolean | null
  startingBid?: number | null
  auctionStartsAt?: string | null
}

interface SearchLiveDto {
  liveId: number
  title: string
  hostId: number
  hostNickname: string
  thumbnailUrl?: string | null
  broadcastStatus: 'LIVE' | 'SCHEDULED'
  scheduledAt?: string | null
  startedAt?: string | null
  viewerCount?: number | null
  productCount?: number | null
}

interface SearchUserDto {
  id: number
  nickname: string
  profileImageUrl: string | null
  followerCount: number
  productCount: number
  isFollowing: boolean | null
}

interface SearchResponse {
  products: SearchPageResponse<SearchProductDto> | null
  lives: SearchPageResponse<SearchLiveDto> | null
  users: SearchPageResponse<SearchUserDto> | null
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
  })

  if (!data.success || !data.data) {
    throw new Error(data.error?.message ?? '검색 결과를 불러오지 못했습니다.')
  }

  const products = normalizeSearchPage(data.data.products)
  const lives = normalizeSearchPage(data.data.lives)
  const users = normalizeSearchPage(data.data.users)

  return {
    products: products.items.map(toSearchProductResult),
    lives: lives.items.map(toSearchLiveResult),
    members: users.items.map(toSearchMemberResult),
    productTotalElements: products.meta.totalElements,
    productTotalPages: products.meta.totalPages,
    liveTotalElements: lives.meta.totalElements,
    liveTotalPages: lives.meta.totalPages,
    memberTotalElements: users.meta.totalElements,
    memberTotalPages: users.meta.totalPages,
  }
}

const toSearchTypeParam = (type?: SearchResultTabId) => {
  if (!type || type === 'all') return undefined
  if (type === 'member') return 'USER'

  return type.toUpperCase()
}

const toSearchParams = (request: SearchRequest) => ({
  keyword: request.keyword,
  type: toSearchTypeParam(request.type),
  categoryIds: request.categories?.filter((category) => /^\d+$/.test(category)).join(',') || undefined,
  conditionGrades: request.conditions?.length ? request.conditions.join(',') : undefined,
  saleTypes: request.saleTypes?.length
    ? request.saleTypes.map((saleType) => (saleType === 'DIRECT' ? 'DIRECT_SALE' : saleType)).join(',')
    : undefined,
  minPrice: request.minPrice,
  maxPrice: request.maxPrice,
  sort: request.sort,
  page: request.page !== undefined ? Math.max(request.page - 1, 0) : undefined,
  size: request.size,
})

const EMPTY_META: PageMeta = {
  page: 1,
  size: 0,
  totalElements: 0,
  totalPages: 0,
}

const normalizeSearchPage = <T>(page: SearchPageResponse<T> | null) => {
  if (!page) {
    return {
      items: [],
      meta: EMPTY_META,
    }
  }

  return {
    items: page.items ?? page.content ?? [],
    meta: page.meta ?? {
      page: (page.page ?? 0) + 1,
      size: page.size ?? 0,
      totalElements: page.totalElements ?? 0,
      totalPages: page.totalPages ?? 0,
    },
  }
}

const toSearchProductResult = (product: SearchProductDto): SearchProductResult => {
  const isAuction = product.auctionScheduled || product.sellType === 'AUCTION_SCHEDULED'

  return {
    id: product.productId,
    brand: product.brand ?? '',
    name: product.name,
    sellerName: product.sellerName ?? '',
    price: product.price ?? product.startingBid ?? 0,
    createdAt: product.auctionStartsAt ?? '',
    conditionGrade: 'A',
    saleType: isAuction ? 'AUCTION' : 'DIRECT',
    categoryName: product.categoryName ?? '',
    imageUrl: product.thumbnailUrl ?? '',
    imageAlt: `${product.name} 상품 이미지`,
    isLiked: product.isWished ?? undefined,
  }
}

const toSearchLiveResult = (live: SearchLiveDto): SearchLiveResult => ({
  id: live.liveId,
  title: live.title,
  hostName: live.hostNickname,
  status: live.broadcastStatus,
  scheduledAt: live.scheduledAt ?? undefined,
  startedAt: live.startedAt ?? undefined,
  productCount: live.productCount ?? 0,
  thumbnailUrl: live.thumbnailUrl ?? '',
})

const toSearchMemberResult = (user: SearchUserDto): SearchMemberResult => ({
  id: user.id,
  nickname: user.nickname,
  profileImageUrl: user.profileImageUrl,
  followerCount: user.followerCount,
  productCount: user.productCount,
  isFollowing: user.isFollowing,
})
