import { getUnreadNotificationCount } from '@/domains/notification/api/notificationApi'
import {
  getBrands,
  getCategories,
  getProductPrimaryImageUrl,
  removeWish,
} from '@/domains/product/api/productApi'
import { PRODUCT_LIST_MOCK_DATA } from '@/domains/product/constants/productListMockData'

import type {
  MyLiveItem,
  MyOrderItem,
  MyOrderStatus,
  MyPageViewData,
  MyProductItem,
  MyProductStatus,
  MyProfile,
  MyProfileUpdateRequest,
  MySaleItem,
  MySettlementStatus,
  MyWishItem,
} from '@/domains/my/types/my.types'
import type {
  ProductConditionGrade,
  ProductListItem,
  ProductSaleStatus,
} from '@/domains/product/types/productList.types'
import { http } from '@/shared/api/http'
import type {
  InterestBrand,
  InterestCategory,
  UserInterests,
} from '@/shared/api/mockInterestStorage'
import { readMockProfileMedia } from '@/shared/api/mockProfileMediaStorage'
import type { ApiResponse, PageMeta, PageResponse } from '@/shared/types/api.types'

const MY_API_ENABLED = import.meta.env.VITE_MY_API_ENABLED === 'true'
const MY_LIVE_API_ENABLED = import.meta.env.VITE_LIVE_LIST_API_ENABLED !== 'false'
const WISH_API_ENABLED = import.meta.env.VITE_WISH_API_ENABLED !== 'false'
const MOCK_MY_PROFILE_STORAGE_KEY = 'vidtib:mock-my-profile'

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
  isLiked?: boolean
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

interface OrderProductDto {
  id: number
  sellerId: number
  categoryId: number | null
  brandId: number | null
  title: string
  description?: string | null
  conditionGrade?: string | null
  sizeLabel?: string | null
  saleType: ProductSaleTypeDto
  saleStatus?: ProductSaleStatusDto
  price: number | null
  createdAt: string
}

interface OrderListItemDto {
  orderId: number
  product: OrderProductDto
  buyerId: number
  buyerNickname: string
  sellerId: number
  sellerNickname: string
  orderPrice: number
  status: string
  createdAt: string
}

interface BackendPageResponse<T> {
  content: T[]
  page: number
  size: number
  totalElements: number
  totalPages: number
  hasNext: boolean
}

type MockMyProfileMap = Record<string, Partial<MyProfile>>

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

  const [
    profileResult,
    wishesResult,
    productsResult,
    livesResult,
    notificationCountResult,
    ordersResult,
    salesResult,
  ] = await Promise.allSettled([
    getMyProfile(userId),
    getMyWishList(userId),
    MY_API_ENABLED ? getMySellerProducts(userId) : Promise.resolve(null),
    MY_LIVE_API_ENABLED ? getMyHostLives(userId) : Promise.resolve(null),
    MY_API_ENABLED ? getUnreadNotificationCount(userId) : Promise.resolve(null),
    MY_API_ENABLED ? getMyOrders(userId, 'BUYER') : Promise.resolve(null),
    MY_API_ENABLED ? getMyOrders(userId, 'SELLER') : Promise.resolve(null),
  ])

  const profile = getSettledValue(profileResult)
  const wishes = getSettledValue(wishesResult)
  const products = getSettledValue(productsResult)
  const lives = getSettledValue(livesResult)
  const unreadNotifications = getSettledValue(notificationCountResult)
  const orders = getSettledValue(ordersResult)?.map(toMyOrderItem) ?? null
  const sales = getSettledValue(salesResult)?.map(toMySaleItem) ?? null

  return {
    ...baseViewData,
    products: products ?? [],
    lives: lives ?? [],
    wishes: wishes?.items ?? [],
    orders: orders ?? [],
    sales: sales ?? [],
    wishMeta: wishes?.meta ?? EMPTY_PAGE_META,
    summary: {
      ...baseViewData.summary,
      profile: profile ?? baseViewData.summary.profile,
      counts: {
        ...baseViewData.summary.counts,
        wishes: wishes?.items.length ?? 0,
        unreadNotifications: unreadNotifications ?? 0,
        orders: orders?.length ?? 0,
        sales: sales?.length ?? 0,
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
    return {
      ...createEmptyProfile(userId),
      ...readMockMyProfile(userId),
      ...readMockProfileMedia(userId),
    }
  }

  const response = await http.get<ApiResponse<MyProfileApiDto>>(`/users/${userId}`)
  const profile = unwrapApiData(response.data, '회원 정보를 불러오지 못했습니다.')

  return {
    ...profile,
    defaultTryOnImageUrl: profile.defaultTryOnImageUrl ?? null,
  }
}

export const getMyWishList = async (userId: number) => {
  if (!WISH_API_ENABLED) {
    void userId
    const items = PRODUCT_LIST_MOCK_DATA
      .filter((product) => product.isLiked)
      .map((product, index) => ({
        product: {
          ...product,
          saleStatus: product.saleType === 'AUCTION' ? 'AUCTION_SCHEDULED' : 'ON_SALE',
        },
        wishedAt: `2026-08-0${index + 1}T10:00:00+09:00`,
      }) satisfies MyWishItem)

    return {
      items,
      meta: {
        page: 1,
        size: items.length,
        totalElements: items.length,
        totalPages: items.length > 0 ? 1 : 0,
      } satisfies PageMeta,
    }
  }

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
    items: await Promise.all(pageResponse.items.map(toMyWishItem)),
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

  const products = await Promise.all(
    pageResponse.items
      .filter((product) => product.sellerId === userId)
      .map(toMyProductItem),
  )

  return products.filter((item): item is MyProductItem => item !== null)
}

const getMyOrders = async (
  userId: number,
  role: 'BUYER' | 'SELLER',
): Promise<OrderListItemDto[]> => {
  const response = await http.get<
    ApiResponse<PageResponse<OrderListItemDto> | BackendPageResponse<OrderListItemDto>>
  >(`/users/${userId}/orders`, {
    params: {
      role,
      page: 0,
      size: 100,
    },
  })
  const pageResponse = normalizePageResponse(
    unwrapApiData(response.data, '주문 목록을 불러오지 못했습니다.'),
  )

  return pageResponse.items
}

const getMyHostLives = async (userId: number): Promise<MyLiveItem[]> => {
  const response = await http.get<
    ApiResponse<PageResponse<MyLiveApiDto> | BackendPageResponse<MyLiveApiDto>>
  >('/lives', {
    // hostId 필터 + 인증 토큰으로 호출해야 종료·취소된 내 라이브까지 서버가 돌려준다.
    // skipAuth로 비회원 취급되면 공개 상태(SCHEDULED/LIVE)만 내려온다(req 028 §2).
    params: {
      hostId: userId,
      page: 0,
      size: 100,
      sort: 'LATEST',
    },
  })
  const pageResponse = normalizePageResponse(
    unwrapApiData(response.data, '라이브 목록을 불러오지 못했습니다.'),
  )

  // 서버가 hostId로 이미 좁혀 주므로 클라이언트 재필터는 하지 않는다.
  return pageResponse.items
    .map(toMyLiveItem)
    .filter((item): item is MyLiveItem => item !== null)
}

export const updateMyProfile = async (
  userId: number,
  request: MyProfileUpdateRequest,
): Promise<MyProfile> => {
  if (!MY_API_ENABLED) {
    const nextProfile = {
      ...createEmptyProfile(userId),
      ...readMockMyProfile(userId),
      ...request,
    }

    writeMockMyProfile(userId, nextProfile)
    return nextProfile
  }

  const response = await http.patch<ApiResponse<MyProfile>>(`/users/${userId}`, request)
  return unwrapApiData(response.data, '회원 정보를 저장하지 못했습니다.')
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
  if (!WISH_API_ENABLED) {
    return
  }

  await removeWish(userId, productId)
}

export const isMyApiEnabled = () => MY_API_ENABLED

const getSettledValue = <T>(result: PromiseSettledResult<T>) =>
  result.status === 'fulfilled' ? result.value : null

const getMockMyProfileKey = (userId: number) => String(userId)

const readMockMyProfileMap = (): MockMyProfileMap => {
  if (typeof window === 'undefined') {
    return {}
  }

  try {
    const storedValue = window.localStorage.getItem(MOCK_MY_PROFILE_STORAGE_KEY)

    if (!storedValue) {
      return {}
    }

    return JSON.parse(storedValue) as MockMyProfileMap
  } catch {
    return {}
  }
}

const readMockMyProfile = (userId: number): Partial<MyProfile> =>
  readMockMyProfileMap()[getMockMyProfileKey(userId)] ?? {}

const writeMockMyProfile = (userId: number, profile: MyProfile) => {
  if (typeof window === 'undefined') {
    return
  }

  const profileMap = readMockMyProfileMap()

  profileMap[getMockMyProfileKey(userId)] = profile
  window.localStorage.setItem(MOCK_MY_PROFILE_STORAGE_KEY, JSON.stringify(profileMap))
}

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

const toMyWishItem = async (wish: MyWishApiDto): Promise<MyWishItem> => ({
  product: await toProductListItem(wish.product),
  wishedAt: wish.wishedAt,
})

const toMyProductItem = async (product: MyProductApiDto): Promise<MyProductItem | null> => {
  const status = toMyProductStatus(product.saleStatus)

  if (!status) {
    return null
  }

  return {
    id: product.id,
    product: await toProductListItem(product),
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

const toMyOrderItem = (order: OrderListItemDto): MyOrderItem => ({
  id: order.orderId,
  type: order.product.saleType === 'AUCTION' ? 'AUCTION' : 'DIRECT',
  status: order.status as MyOrderStatus,
  productName: order.product.title,
  productThumbnailUrl: '',
  sellerNickname: order.sellerNickname,
  paidAmount: order.orderPrice,
  createdAt: order.createdAt,
  recipientName: '',
  recipientPhoneNumber: '',
  postalCode: '',
  address: '',
  detailAddress: '',
})

const toMySaleItem = (order: OrderListItemDto): MySaleItem => ({
  id: order.orderId,
  status: order.status as MyOrderStatus,
  settlementStatus: toMySettlementStatus(order.status),
  productName: order.product.title,
  productThumbnailUrl: '',
  buyerNickname: order.buyerNickname,
  paidAmount: order.orderPrice,
  createdAt: order.createdAt,
  recipientName: '',
  recipientPhoneNumber: '',
  postalCode: '',
  address: '',
  detailAddress: '',
})

const toMySettlementStatus = (status: string): MySettlementStatus => {
  if (status === 'SETTLED') {
    return 'SETTLED'
  }

  if (status === 'CONFIRMED') {
    return 'PENDING'
  }

  if (status === 'REFUNDED') {
    return 'REFUND_REQUESTED'
  }

  return 'ESCROW'
}

const toProductListItem = async (product: MyProductApiDto): Promise<ProductListItem> => {
  const imageUrl =
    product.primaryImageUrl || (await getProductPrimaryImageUrl(product.id).catch(() => ''))

  return {
    id: product.id,
    brand: product.brandName || fallbackBrandLabel(product.brandId),
    name: product.title,
    price: product.price ?? 0,
    conditionGrade: product.conditionGrade,
    saleType: product.saleType === 'AUCTION' ? 'AUCTION' : 'DIRECT',
    saleStatus: product.saleStatus satisfies ProductSaleStatus,
    categoryId: product.categoryId,
    categoryName: product.categoryName ?? fallbackCategoryLabel(product.categoryId),
    imageUrl,
    imageAlt: `${product.title} 상품 이미지`,
    isLiked: product.isWished ?? product.isLiked ?? true,
  }
}

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

const fallbackCategoryLabel = (categoryId: number | null) =>
  categoryId ? `카테고리 #${categoryId}` : ''

const unwrapApiData = <T>(response: ApiResponse<T>, fallbackMessage: string) => {
  if (!response.success || response.data === null) {
    throw new Error(response.error?.message ?? fallbackMessage)
  }

  return response.data
}
