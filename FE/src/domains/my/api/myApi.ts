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
  MyMonthlyRevenue,
  MyOrderItem,
  MyOrderStatus,
  MyPageViewData,
  MyProductItem,
  MyProductStatus,
  MyProfile,
  MyProfileUpdateRequest,
  MySaleItem,
  MySalesPerformance,
  MySettlementStatus,
  MySettlementSummary,
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
  brand: string | null
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
  // BE 확인 필요(docs/requests/BE/041) — 반영 전에는 항상 undefined로 내려와 환불 대기 카운트가 0으로 집계된다.
  refundRequested?: boolean
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
      scheduledLives: 0,
      refundRequests: 0,
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
  const sellerOrders = getSettledValue(salesResult)
  const orders = getSettledValue(ordersResult)?.map(toMyOrderItem) ?? null
  const sales = sellerOrders?.map(toMySaleItem) ?? null
  const dashboardMetrics = sellerOrders
    ? buildSellerDashboardMetrics(sellerOrders, products?.length ?? 0)
    : null

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
      salesPerformance: dashboardMetrics?.salesPerformance ?? baseViewData.summary.salesPerformance,
      settlementSummary: dashboardMetrics
        ? { ...dashboardMetrics.settlementSummary, withdrawableAmount: 0 }
        : baseViewData.summary.settlementSummary,
      productStatusCounts: products ? getProductStatusCounts(products) : baseViewData.summary.productStatusCounts,
      todoCounts: {
        shippingPending: dashboardMetrics?.shippingPending ?? 0,
        scheduledLives: lives?.filter((live) => live.status === 'SCHEDULED').length ?? 0,
        refundRequests: dashboardMetrics?.refundRequests ?? 0,
      },
      monthlyRevenue: dashboardMetrics?.monthlyRevenue ?? baseViewData.summary.monthlyRevenue,
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

const MY_ORDERS_PAGE_SIZE = 100

// 판매자 대시보드 집계(월별 수익 등)가 정확하려면 첫 페이지만으론 부족해 전체를 순회한다.
const getMyOrders = async (
  userId: number,
  role: 'BUYER' | 'SELLER',
): Promise<OrderListItemDto[]> => {
  const firstPage = await fetchMyOrdersPage(userId, role, 0)

  if (firstPage.meta.totalPages <= 1) {
    return firstPage.items
  }

  const restPages = await Promise.all(
    Array.from({ length: firstPage.meta.totalPages - 1 }, (_, index) =>
      fetchMyOrdersPage(userId, role, index + 1),
    ),
  )

  return [firstPage, ...restPages].flatMap((page) => page.items)
}

const fetchMyOrdersPage = async (userId: number, role: 'BUYER' | 'SELLER', page: number) => {
  const response = await http.get<
    ApiResponse<PageResponse<OrderListItemDto> | BackendPageResponse<OrderListItemDto>>
  >(`/users/${userId}/orders`, {
    params: {
      role,
      page,
      size: MY_ORDERS_PAGE_SIZE,
    },
  })

  return normalizePageResponse(unwrapApiData(response.data, '주문 목록을 불러오지 못했습니다.'))
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

const MONTHLY_REVENUE_MONTH_COUNT = 12
const SHIPPING_PENDING_STATUSES = new Set(['PAID', 'SHIPPING'])
const SETTLEMENT_PENDING_STATUSES = new Set(['PAID', 'SHIPPING', 'DELIVERED', 'CONFIRMED'])

interface SellerDashboardMetrics {
  salesPerformance: MySalesPerformance
  settlementSummary: Omit<MySettlementSummary, 'withdrawableAmount'>
  shippingPending: number
  refundRequests: number
  monthlyRevenue: MyMonthlyRevenue[]
}

// 판매자 대시보드 전용 집계 API가 없어, 판매 주문 목록(role=SELLER)을 클라이언트에서 묶어
// salesPerformance/settlementSummary/monthlyRevenue를 만든다.
// 정산 완료 "시각"을 담는 필드가 BE에 없어(docs/requests/BE/030), 주문 생성일(createdAt)을
// 정산일 근사치로 쓴다 — BE가 필드를 추가하면 이 함수만 교체하면 된다.
const buildSellerDashboardMetrics = (
  sellerOrders: OrderListItemDto[],
  registeredProductCount: number,
): SellerDashboardMetrics => {
  const settledOrders = sellerOrders.filter((order) => order.status === 'SETTLED')
  const pendingOrders = sellerOrders.filter((order) => SETTLEMENT_PENDING_STATUSES.has(order.status))

  const grossRevenue = settledOrders.reduce((sum, order) => sum + order.orderPrice, 0)
  const soldCount = settledOrders.length
  const averageOrderAmount = soldCount > 0 ? Math.round(grossRevenue / soldCount) : 0
  const sellThroughRate =
    registeredProductCount > 0 ? Math.round((soldCount / registeredProductCount) * 100) : 0

  const purchaseCountByBuyerId = new Map<number, number>()
  settledOrders.forEach((order) => {
    purchaseCountByBuyerId.set(order.buyerId, (purchaseCountByBuyerId.get(order.buyerId) ?? 0) + 1)
  })
  const repeatBuyerCount = [...purchaseCountByBuyerId.values()].filter((count) => count > 1).length

  const pendingAmount = pendingOrders.reduce((sum, order) => sum + order.orderPrice, 0)
  const lastSettledAt = settledOrders.map((order) => order.createdAt).sort().at(-1) ?? ''

  return {
    salesPerformance: {
      soldCount,
      grossRevenue,
      // BE 응답에 수수료 관련 필드가 없어 순수익은 총매출과 동일하게 둔다.
      netRevenue: grossRevenue,
      averageOrderAmount,
      sellThroughRate,
      repeatBuyerCount,
    },
    settlementSummary: {
      settledAmount: grossRevenue,
      pendingAmount,
      escrowAmount: pendingAmount,
      lastSettledAt,
    },
    shippingPending: sellerOrders.filter((order) => SHIPPING_PENDING_STATUSES.has(order.status)).length,
    refundRequests: sellerOrders.filter((order) => order.refundRequested === true).length,
    monthlyRevenue: buildMonthlyRevenue(settledOrders),
  }
}

// 이번 달을 포함한 최근 12개월을 항상 12칸으로 채운다(주문이 없는 달도 0으로 표시).
const buildMonthlyRevenue = (settledOrders: OrderListItemDto[]): MyMonthlyRevenue[] => {
  const now = new Date()
  const months = Array.from({ length: MONTHLY_REVENUE_MONTH_COUNT }, (_, index) => {
    const date = new Date(now.getFullYear(), now.getMonth() - (MONTHLY_REVENUE_MONTH_COUNT - 1 - index), 1)

    return { key: `${date.getFullYear()}-${date.getMonth()}`, month: `${date.getMonth() + 1}월` }
  })

  const bucketByKey = new Map<string, { revenue: number; soldCount: number }>()
  settledOrders.forEach((order) => {
    const orderDate = new Date(order.createdAt)
    const key = `${orderDate.getFullYear()}-${orderDate.getMonth()}`
    const bucket = bucketByKey.get(key) ?? { revenue: 0, soldCount: 0 }

    bucket.revenue += order.orderPrice
    bucket.soldCount += 1
    bucketByKey.set(key, bucket)
  })

  return months.map(({ key, month }) => {
    const bucket = bucketByKey.get(key) ?? { revenue: 0, soldCount: 0 }

    return { month, revenue: bucket.revenue, soldCount: bucket.soldCount }
  })
}

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
    brand: product.brand || '',
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

const fallbackCategoryLabel = (categoryId: number | null) =>
  categoryId ? `카테고리 #${categoryId}` : ''

const unwrapApiData = <T>(response: ApiResponse<T>, fallbackMessage: string) => {
  if (!response.success || response.data === null) {
    throw new Error(response.error?.message ?? fallbackMessage)
  }

  return response.data
}
