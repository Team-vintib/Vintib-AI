import {
  mockMyPageViewData,
  mockMyProfile,
} from '@/domains/my/constants/myMockData'
import { PRODUCT_LIST_MOCK_DATA } from '@/domains/product/constants/productListMockData'
import { getUnreadNotificationCount } from '@/domains/notification/api/notificationApi'
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
import { http } from '@/shared/api/http'
import {
  deleteMockDefaultTryOnImage,
  deleteMockProfileImage,
  readImageFileAsDataUrl,
  readMockProfileMedia,
  saveMockDefaultTryOnImage,
  saveMockProfileImage,
} from '@/shared/api/mockProfileMediaStorage'
import {
  getMockInterestOptions,
  readMockUserInterests,
  saveMockUserInterests,
  type InterestBrand,
  type InterestCategory,
  type UserInterests,
} from '@/shared/api/mockInterestStorage'
import { getBrands, getCategories, removeWish } from '@/domains/product/api/productApi'
import type { ProductConditionGrade, ProductListItem } from '@/domains/product/types/productList.types'
import type { ApiResponse, PageMeta, PageResponse } from '@/shared/types/api.types'

const MOCK_DELAY_MS = 250
const MY_API_ENABLED = import.meta.env.VITE_MY_API_ENABLED === 'true'
const MY_LIVE_API_ENABLED = import.meta.env.VITE_LIVE_LIST_API_ENABLED !== 'false'

interface MyProfileImageResponse {
  profileImageUrl: string | null
}

interface MyDefaultTryOnImageResponse {
  defaultTryOnImageUrl: string | null
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

const wait = (delay: number) =>
  new Promise<void>((resolve) => {
    window.setTimeout(resolve, delay)
  })

export const getMyPageViewData = async (userId: number): Promise<MyPageViewData> => {
  await wait(MY_API_ENABLED || MY_LIVE_API_ENABLED ? 0 : MOCK_DELAY_MS)
  const media = readMockProfileMedia(userId)
  const baseViewData: MyPageViewData = {
    ...mockMyPageViewData,
    summary: {
      ...mockMyPageViewData.summary,
      profile: {
        ...mockMyPageViewData.summary.profile,
        ...media,
        id: userId,
      },
    },
  }

  if (!MY_API_ENABLED && !MY_LIVE_API_ENABLED) {
    return baseViewData
  }

  const [wishesResult, productsResult, livesResult, notificationCountResult] =
    await Promise.allSettled([
      MY_API_ENABLED ? getMyWishList(userId) : Promise.resolve(null),
      MY_API_ENABLED ? getMySellerProducts(userId) : Promise.resolve(null),
      MY_LIVE_API_ENABLED ? getMyHostLives(userId) : Promise.resolve(null),
      MY_API_ENABLED ? getUnreadNotificationCount(userId) : Promise.resolve(null),
    ])

  const wishes = getSettledValue(wishesResult)
  const products = getSettledValue(productsResult)
  const lives = getSettledValue(livesResult)
  const unreadNotifications = getSettledValue(notificationCountResult)

  return {
    ...baseViewData,
    products: products ?? baseViewData.products,
    lives: lives ?? baseViewData.lives,
    wishes: wishes?.items ?? baseViewData.wishes,
    wishMeta: wishes?.meta ?? baseViewData.wishMeta,
    summary: {
      ...baseViewData.summary,
      counts: {
        ...baseViewData.summary.counts,
        wishes: wishes?.items.length ?? baseViewData.summary.counts.wishes,
        unreadNotifications: unreadNotifications ?? baseViewData.summary.counts.unreadNotifications,
      },
      productStatusCounts: products
        ? getProductStatusCounts(products)
        : baseViewData.summary.productStatusCounts,
      todoCounts: lives
        ? {
            ...baseViewData.summary.todoCounts,
            scheduledLives: lives.filter((live) => live.status === 'SCHEDULED').length,
          }
        : baseViewData.summary.todoCounts,
    },
  }
}

export const getMyProfile = async (userId: number): Promise<MyProfile> => {
  if (!MY_API_ENABLED) {
    await wait(MOCK_DELAY_MS)
    return {
      ...mockMyProfile,
      ...readMockProfileMedia(userId),
      id: userId,
    }
  }

  const response = await http.get<ApiResponse<MyProfile>>('/me')
  return unwrapApiData(response.data, '회원 정보를 불러오지 못했습니다.')
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
  if (!MY_API_ENABLED) {
    await wait(MOCK_DELAY_MS)
    const order = mockMyPageViewData.orders.find((item) => item.id === orderId)

    if (!order) {
      throw new Error('구매 내역을 찾지 못했습니다.')
    }

    return order
  }

  const response = await http.get<ApiResponse<MyOrderItem>>(`/users/${userId}/orders/${orderId}`)
  return unwrapApiData(response.data, '구매 상세 정보를 불러오지 못했습니다.')
}

export const getMySaleDetail = async (userId: number, saleId: number): Promise<MySaleItem> => {
  if (!MY_API_ENABLED) {
    await wait(MOCK_DELAY_MS)
    const sale = mockMyPageViewData.sales.find((item) => item.id === saleId)

    if (!sale) {
      throw new Error('판매 내역을 찾지 못했습니다.')
    }

    return sale
  }

  const response = await http.get<ApiResponse<MySaleItem>>(`/users/${userId}/sales/${saleId}`)
  return unwrapApiData(response.data, '판매 상세 정보를 불러오지 못했습니다.')
}

export const updateMyProfile = async (
  userId: number,
  request: MyProfileUpdateRequest,
): Promise<MyProfile> => {
  if (!MY_API_ENABLED) {
    await wait(MOCK_DELAY_MS)
    return {
      ...mockMyProfile,
      ...readMockProfileMedia(userId),
      ...request,
      id: userId,
    }
  }

  const response = await http.patch<ApiResponse<MyProfile>>(`/users/${userId}`, request)
  return unwrapApiData(response.data, '회원 정보를 저장하지 못했습니다.')
}

export const updateMyProfileImage = async (userId: number, file: File) => {
  if (!MY_API_ENABLED) {
    await wait(MOCK_DELAY_MS)
    const profileImageUrl = await readImageFileAsDataUrl(file, '프로필 사진을 읽지 못했습니다.')

    saveMockProfileImage(userId, profileImageUrl)

    return { profileImageUrl } satisfies MyProfileImageResponse
  }

  const formData = new FormData()
  formData.append('profileImage', file)

  const response = await http.put<ApiResponse<MyProfileImageResponse>>('/me/profile-image', formData, {
    headers: {
      'Content-Type': undefined,
    },
  })

  return unwrapApiData(response.data, '프로필 사진을 저장하지 못했습니다.')
}

export const deleteMyProfileImage = async (userId: number) => {
  if (!MY_API_ENABLED) {
    await wait(MOCK_DELAY_MS)
    deleteMockProfileImage(userId)

    return { profileImageUrl: null } satisfies MyProfileImageResponse
  }

  const response = await http.delete<ApiResponse<MyProfileImageResponse | null>>('/me/profile-image')
  const data = unwrapNullableApiData(response.data, '프로필 사진을 삭제하지 못했습니다.')

  return data ?? { profileImageUrl: null }
}

export const updateMyDefaultTryOnImage = async (userId: number, file: File) => {
  if (!MY_API_ENABLED) {
    await wait(MOCK_DELAY_MS)
    const defaultTryOnImageUrl = await readImageFileAsDataUrl(
      file,
      'AI 시착용 사진을 읽지 못했습니다.',
    )

    saveMockDefaultTryOnImage(userId, defaultTryOnImageUrl)

    return { defaultTryOnImageUrl } satisfies MyDefaultTryOnImageResponse
  }

  const formData = new FormData()
  formData.append('bodyPhoto', file)

  const response = await http.put<ApiResponse<MyDefaultTryOnImageResponse>>('/me/tryon', formData, {
    headers: {
      'Content-Type': undefined,
    },
  })

  return unwrapApiData(response.data, 'AI 시착용 사진을 저장하지 못했습니다.')
}

export const deleteMyDefaultTryOnImage = async (userId: number) => {
  if (!MY_API_ENABLED) {
    await wait(MOCK_DELAY_MS)
    deleteMockDefaultTryOnImage(userId)

    return { defaultTryOnImageUrl: null } satisfies MyDefaultTryOnImageResponse
  }

  const response = await http.delete<ApiResponse<MyDefaultTryOnImageResponse | null>>('/me/tryon/image')
  const data = unwrapNullableApiData(response.data, 'AI 시착용 사진을 삭제하지 못했습니다.')

  return data ?? { defaultTryOnImageUrl: null }
}

export const getMyInterestOptions = async () => {
  if (!MY_API_ENABLED) {
    await wait(MOCK_DELAY_MS)
    return getMockInterestOptions()
  }

  const [brands, categories] = await Promise.all([getBrands(), getCategories()])

  return {
    brands: brands satisfies InterestBrand[],
    categories: categories satisfies InterestCategory[],
  }
}

export const getMyInterests = async (userId: number) => {
  if (!MY_API_ENABLED) {
    await wait(MOCK_DELAY_MS)
    return readMockUserInterests(userId)
  }

  const response = await http.get<ApiResponse<UserInterests>>(`/users/${userId}/interests`)
  return unwrapApiData(response.data, '관심 정보를 불러오지 못했습니다.')
}

export const updateMyInterests = async (userId: number, request: UpdateMyInterestsRequest) => {
  if (!MY_API_ENABLED) {
    await wait(MOCK_DELAY_MS)
    return saveMockUserInterests(userId, request.brandIds, request.categoryIds)
  }

  const response = await http.put<ApiResponse<UserInterests>>(`/users/${userId}/interests`, request)
  return unwrapApiData(response.data, '관심 정보를 저장하지 못했습니다.')
}

export const removeMyWish = async (userId: number, productId: number) => {
  if (!MY_API_ENABLED) {
    await wait(MOCK_DELAY_MS)
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
  if (
    live.broadcastStatus !== 'LIVE' &&
    live.broadcastStatus !== 'SCHEDULED' &&
    live.broadcastStatus !== 'ENDED'
  ) {
    return null
  }

  const broadcastAt = live.broadcastStatus === 'LIVE' ? live.startedAt : live.scheduledAt

  if (!broadcastAt) {
    return null
  }

  return {
    id: live.liveId,
    title: live.title,
    status: live.broadcastStatus,
    thumbnailUrl: live.thumbnailUrl || PRODUCT_LIST_MOCK_DATA[0]?.imageUrl || '',
    productCount: 0,
    viewerCount: live.viewerCount,
    broadcastAt,
  }
}

const toProductListItem = (product: MyProductApiDto): ProductListItem => {
  const mockFallback = PRODUCT_LIST_MOCK_DATA.find((item) => item.id === product.id)

  return {
    id: product.id,
    brand: product.brandName || mockFallback?.brand || fallbackBrandLabel(product.brandId),
    name: product.title,
    price: product.price ?? 0,
    conditionGrade: product.conditionGrade,
    saleType: product.saleType === 'AUCTION' ? 'AUCTION' : 'DIRECT',
    imageUrl: product.primaryImageUrl || mockFallback?.imageUrl || PRODUCT_LIST_MOCK_DATA[0]?.imageUrl || '',
    imageAlt: `${product.title} 상품 이미지`,
    isLiked: product.isWished ?? true,
  }
}

const toMyProductStatus = (status: ProductSaleStatusDto): MyProductStatus | null => {
  if (status === 'ON_SALE' || status === 'AUCTION_SCHEDULED' || status === 'SOLD') {
    return status
  }

  return null
}

const getProductStatusCounts = (products: MyProductItem[]) => ({
  onSale: products.filter((item) => item.status === 'ON_SALE').length,
  auctionScheduled: products.filter((item) => item.status === 'AUCTION_SCHEDULED').length,
  sold: products.filter((item) => item.status === 'SOLD').length,
})

const fallbackBrandLabel = (brandId: number | null) =>
  brandId ? `브랜드 #${brandId}` : '브랜드 미상'

const unwrapApiData = <T>(response: ApiResponse<T>, fallbackMessage: string) => {
  if (!response.success || response.data === null) {
    throw new Error(response.error?.message ?? fallbackMessage)
  }

  return response.data
}

const unwrapNullableApiData = <T>(
  response: ApiResponse<T | null>,
  fallbackMessage: string,
) => {
  if (!response.success) {
    throw new Error(response.error?.message ?? fallbackMessage)
  }

  return response.data
}
