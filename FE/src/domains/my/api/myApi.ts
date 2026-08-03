import { getUnreadNotificationCount } from '@/domains/notification/api/notificationApi'
import { getBrands, getCategories, removeWish } from '@/domains/product/api/productApi'

import type {
  MyLiveItem,
  MyOrderItem,
  MyPageViewData,
  MyProductItem,
  MyProductStatus,
  MyProfile,
  MyProfileUpdateRequest,
  MySaleItem,
  MyWishItem,
} from '@/domains/my/types/my.types'
import type { ProductConditionGrade, ProductListItem } from '@/domains/product/types/productList.types'
import { http } from '@/shared/api/http'
import type {
  InterestBrand,
  InterestCategory,
  UserInterests,
} from '@/shared/api/mockInterestStorage'
import type { ApiResponse, PageMeta, PageResponse } from '@/shared/types/api.types'

const MY_API_ENABLED = import.meta.env.VITE_MY_API_ENABLED === 'true'
const MY_LIVE_API_ENABLED = import.meta.env.VITE_LIVE_LIST_API_ENABLED !== 'false'

interface MyProfileImageResponse {
  profileImageUrl: string | null
}

interface MyDefaultTryOnImageResponse {
  defaultTryOnImageUrl: string | null
}

interface MyProfileApiDto extends Omit<MyProfile, 'defaultTryOnImageUrl'> {
  defaultTryOnImageUrl?: string | null
}

interface UpdateMyInterestsRequest {
  brandIds: number[]
  categoryIds: number[]
}

type ProductSaleTypeDto = 'DIRECT_SALE' | 'AUCTION'
type ProductSaleStatusDto =
  | 'DRAFT'
  | 'ON_SALE'
  | 'AUCTION_SCHEDULED'
  | 'AUCTION_IN_PROGRESS'
  | 'AUCTION_FAILED'
  | 'SOLD'
  | 'PRIVATE'

interface MyProductApiDto {
  id: number
  sellerId: number
  categoryId: number
  categoryName?: string | null
  brandId: number | null
  brandName?: string | null
  title: string
  conditionGrade: ProductConditionGrade
  saleType: ProductSaleTypeDto
  saleStatus: ProductSaleStatusDto
  price: number | null
  primaryImageUrl?: string | null
  isWished?: boolean
  createdAt: string
}

interface MyWishApiDto {
  product: MyProductApiDto
  wishedAt: string
}

interface MyLiveApiDto {
  liveId: number
  title: string
  hostId: number
  hostNickname: string
  thumbnailUrl: string | null
  broadcastStatus: MyLiveItem['status'] | 'CANCELED'
  scheduledAt: string | null
  startedAt: string | null
  viewerCount: number
}

interface BackendPageResponse<T> {
  content: T[]
  page: number
  size: number
  totalElements: number
  totalPages: number
  hasNext: boolean
}

const EMPTY_PAGE_META: PageMeta = {
  page: 1,
  size: 0,
  totalElements: 0,
  totalPages: 0,
}

const createEmptyProfile = (userId: number): MyProfile => ({
  id: userId,
  email: '',
  name: '',
  nickname: '',
  phoneNumber: '',
  postalCode: null,
  address: '',
  detailAddress: '',
  gender: 'MALE',
  profileImageUrl: null,
  defaultTryOnImageUrl: null,
  memberType: 'GENERAL',
  businessVerificationStatus: 'NONE',
  onboardingCompleted: false,
})

const createEmptyMyPageViewData = (userId: number): MyPageViewData => ({
  summary: {
    profile: createEmptyProfile(userId),
    counts: {
      orders: 0,
      sales: 0,
      wishes: 0,
      followers: 0,
      unreadNotifications: 0,
    },
    pointBalance: 0,
    pendingSettlementAmount: 0,
    salesPerformance: {
      soldCount: 0,
      grossRevenue: 0,
      netRevenue: 0,
      averageOrderAmount: 0,
      sellThroughRate: 0,
      repeatBuyerCount: 0,
    },
    settlementSummary: {
      settledAmount: 0,
      pendingAmount: 0,
      escrowAmount: 0,
      withdrawableAmount: 0,
      lastSettledAt: '',
    },
    todoCounts: {
      shippingPending: 0,
      refundRequests: 0,
      scheduledLives: 0,
    },
    productStatusCounts: {
      onSale: 0,
      auctionScheduled: 0,
      sold: 0,
    },
    monthlyRevenue: [],
  },
  products: [],
  orders: [],
  sales: [],
  lives: [],
  wishes: [],
  followers: [],
  followings: [],
  wishMeta: EMPTY_PAGE_META,
})

export const getMyPageViewData = async (userId: number): Promise<MyPageViewData> => {
  const baseViewData = createEmptyMyPageViewData(userId)

  const [profileResult, wishesResult, productsResult, livesResult, notificationCountResult] =
    await Promise.allSettled([
      MY_API_ENABLED ? getMyProfile(userId) : Promise.resolve(null),
      MY_API_ENABLED ? getMyWishList(userId) : Promise.resolve(null),
      MY_API_ENABLED ? getMySellerProducts(userId) : Promise.resolve(null),
      MY_LIVE_API_ENABLED ? getMyHostLives(userId) : Promise.resolve(null),
      MY_API_ENABLED ? getUnreadNotificationCount(userId) : Promise.resolve(null),
    ])

  const profile = getSettledValue(profileResult)
  const wishes = getSettledValue(wishesResult)
  const products = getSettledValue(productsResult)
  const lives = getSettledValue(livesResult)
  const unreadNotifications = getSettledValue(notificationCountResult)

  return {
    ...baseViewData,
    products: products ?? [],
    lives: lives ?? [],
    wishes: wishes?.items ?? [],
    wishMeta: wishes?.meta ?? EMPTY_PAGE_META,
    summary: {
      ...baseViewData.summary,
      profile: profile ?? baseViewData.summary.profile,
      counts: {
        ...baseViewData.summary.counts,
        wishes: wishes?.items.length ?? 0,
        unreadNotifications: unreadNotifications ?? 0,
      },
      productStatusCounts: products ? getProductStatusCounts(products) : baseViewData.summary.productStatusCounts,
      todoCounts: {
        ...baseViewData.summary.todoCounts,
        scheduledLives: lives?.filter((live) => live.status === 'SCHEDULED').length ?? 0,
      },
    },
  }
}

export const getMyProfile = async (userId: number): Promise<MyProfile> => {
  if (!MY_API_ENABLED) {
    return createEmptyProfile(userId)
  }

  const response = await http.get<ApiResponse<MyProfileApiDto>>(`/users/${userId}`)
  const profile = unwrapApiData(response.data, '회원 정보를 불러오지 못했습니다.')

  return {
    ...profile,
    defaultTryOnImageUrl: profile.defaultTryOnImageUrl ?? null,
  }
}

const getMyWishList = async (userId: number) => {
  const response = await http.get<
    ApiResponse<PageResponse<MyWishApiDto> | BackendPageResponse<MyWishApiDto>>
  >(`/users/${userId}/wishes`, {
    params: {
      page: 0,
      size: 60,
    },
  })
  const pageResponse = normalizePageResponse(unwrapApiData(response.data, '찜 목록을 불러오지 못했습니다.'))

  return {
    items: pageResponse.items.map(toMyWishItem),
    meta: pageResponse.meta,
  }
}

const getMySellerProducts = async (userId: number): Promise<MyProductItem[]> => {
  const response = await http.get<
    ApiResponse<PageResponse<MyProductApiDto> | BackendPageResponse<MyProductApiDto>>
  >('/products', {
    params: {
      page: 0,
      size: 100,
      sort: 'LATEST',
    },
  })
  const pageResponse = normalizePageResponse(
    unwrapApiData(response.data, '판매 상품 목록을 불러오지 못했습니다.'),
  )

  return pageResponse.items
    .filter((product) => product.sellerId === userId)
    .map(toMyProductItem)
    .filter((item): item is MyProductItem => item !== null)
}

const getMyHostLives = async (userId: number): Promise<MyLiveItem[]> => {
  const response = await http.get<
    ApiResponse<PageResponse<MyLiveApiDto> | BackendPageResponse<MyLiveApiDto>>
  >('/lives', {
    params: {
      page: 0,
      size: 100,
      sort: 'LATEST',
    },
    skipAuth: true,
  })
  const pageResponse = normalizePageResponse(
    unwrapApiData(response.data, '라이브 목록을 불러오지 못했습니다.'),
  )

  return pageResponse.items
    .filter((live) => live.hostId === userId)
    .map(toMyLiveItem)
    .filter((item): item is MyLiveItem => item !== null)
}

export const getMyOrderDetail = async (
  userId: number,
  orderId: number,
): Promise<MyOrderItem> => {
  void userId
  void orderId
  throw new Error('구매 상세 API가 아직 연결되지 않았습니다.')
}

export const getMySaleDetail = async (userId: number, saleId: number): Promise<MySaleItem> => {
  void userId
  void saleId
  throw new Error('판매 상세 API가 아직 연결되지 않았습니다.')
}

export const updateMyProfile = async (
  userId: number,
  request: MyProfileUpdateRequest,
): Promise<MyProfile> => {
  if (!MY_API_ENABLED) {
    return {
      ...createEmptyProfile(userId),
      ...request,
    }
  }

  const response = await http.patch<ApiResponse<MyProfile>>(`/users/${userId}`, request)
  return unwrapApiData(response.data, '회원 정보를 저장하지 못했습니다.')
}

export const updateMyProfileImage = async (userId: number, file: File) => {
  void userId
  void file
  return { profileImageUrl: null } satisfies MyProfileImageResponse
}

export const deleteMyProfileImage = async (userId: number) => {
  void userId
  return { profileImageUrl: null } satisfies MyProfileImageResponse
}

export const updateMyDefaultTryOnImage = async (userId: number, file: File) => {
  void userId
  void file
  return { defaultTryOnImageUrl: null } satisfies MyDefaultTryOnImageResponse
}

export const deleteMyDefaultTryOnImage = async (userId: number) => {
  void userId
  return { defaultTryOnImageUrl: null } satisfies MyDefaultTryOnImageResponse
}

export const getMyInterestOptions = async () => {
  if (!MY_API_ENABLED) {
    return {
      brands: [] satisfies InterestBrand[],
      categories: [] satisfies InterestCategory[],
    }
  }

  const [brands, categories] = await Promise.all([getBrands(), getCategories()])

  return {
    brands: brands satisfies InterestBrand[],
    categories: categories satisfies InterestCategory[],
  }
}

export const getMyInterests = async (userId: number) => {
  if (!MY_API_ENABLED) {
    void userId
    return {
      brands: [],
      categories: [],
    } satisfies UserInterests
  }

  const response = await http.get<ApiResponse<UserInterests>>(`/users/${userId}/interests`)
  return unwrapApiData(response.data, '관심 정보를 불러오지 못했습니다.')
}

export const updateMyInterests = async (userId: number, request: UpdateMyInterestsRequest) => {
  if (!MY_API_ENABLED) {
    void userId
    return {
      brands: [],
      categories: [],
    } satisfies UserInterests
  }

  const response = await http.put<ApiResponse<UserInterests>>(`/users/${userId}/interests`, request)
  return unwrapApiData(response.data, '관심 정보를 저장하지 못했습니다.')
}

export const removeMyWish = async (userId: number, productId: number) => {
  if (!MY_API_ENABLED) {
    return
  }

  await removeWish(userId, productId)
}

export const isMyApiEnabled = () => MY_API_ENABLED

const getSettledValue = <T>(result: PromiseSettledResult<T>) =>
  result.status === 'fulfilled' ? result.value : null

const normalizePageResponse = <T>(
  response: PageResponse<T> | BackendPageResponse<T>,
): PageResponse<T> => {
  if ('items' in response) {
    return response
  }

  return {
    items: response.content,
    meta: {
      page: response.page + 1,
      size: response.size,
      totalElements: response.totalElements,
      totalPages: response.totalPages,
    } satisfies PageMeta,
  }
}

const toMyWishItem = (wish: MyWishApiDto): MyWishItem => ({
  product: toProductListItem(wish.product),
  wishedAt: wish.wishedAt,
})

const toMyProductItem = (product: MyProductApiDto): MyProductItem | null => {
  const status = toMyProductStatus(product.saleStatus)

  if (!status) {
    return null
  }

  return {
    id: product.id,
    product: toProductListItem(product),
    status,
    updatedAt: product.createdAt,
  }
}

const toMyLiveItem = (live: MyLiveApiDto): MyLiveItem | null => {
  if (live.broadcastStatus === 'CANCELED') {
    return null
  }

  return {
    id: live.liveId,
    title: live.title,
    status: live.broadcastStatus,
    thumbnailUrl: live.thumbnailUrl || '',
    productCount: 0,
    viewerCount: live.viewerCount,
    broadcastAt: live.startedAt ?? live.scheduledAt ?? '',
  }
}

const toProductListItem = (product: MyProductApiDto): ProductListItem => ({
  id: product.id,
  brand: product.brandName || fallbackBrandLabel(product.brandId),
  name: product.title,
  price: product.price ?? 0,
  conditionGrade: product.conditionGrade,
  saleType: product.saleType === 'AUCTION' ? 'AUCTION' : 'DIRECT',
  imageUrl: product.primaryImageUrl || '',
  imageAlt: `${product.title} 상품 이미지`,
  isLiked: product.isWished ?? true,
})

const toMyProductStatus = (status: ProductSaleStatusDto): MyProductStatus | null => {
  if (status === 'ON_SALE') {
    return 'ON_SALE'
  }

  if (status === 'AUCTION_SCHEDULED' || status === 'AUCTION_IN_PROGRESS' || status === 'AUCTION_FAILED') {
    return 'AUCTION_SCHEDULED'
  }

  if (status === 'SOLD') {
    return 'SOLD'
  }

  return null
}

const getProductStatusCounts = (products: MyProductItem[]) => ({
  onSale: products.filter((product) => product.status === 'ON_SALE').length,
  auctionScheduled: products.filter((product) => product.status === 'AUCTION_SCHEDULED').length,
  sold: products.filter((product) => product.status === 'SOLD').length,
})

const fallbackBrandLabel = (brandId: number | null) =>
  brandId ? `브랜드 #${brandId}` : ''

const unwrapApiData = <T>(response: ApiResponse<T>, fallbackMessage: string) => {
  if (!response.success || response.data === null) {
    throw new Error(response.error?.message ?? fallbackMessage)
  }

  return response.data
}
