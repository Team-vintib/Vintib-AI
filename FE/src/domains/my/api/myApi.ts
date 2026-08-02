import {
  mockMyPageViewData,
  mockMyProfile,
} from '@/domains/my/constants/myMockData'
import type {
  MyOrderItem,
  MyPageViewData,
  MyProfile,
  MyProfileUpdateRequest,
  MySaleItem,
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
import { getBrands, getCategories } from '@/domains/product/api/productApi'
import type { ApiResponse } from '@/shared/types/api.types'

const MOCK_DELAY_MS = 250
const MY_API_ENABLED = import.meta.env.VITE_MY_API_ENABLED === 'true'

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

const wait = (delay: number) =>
  new Promise<void>((resolve) => {
    window.setTimeout(resolve, delay)
  })

export const getMyPageViewData = async (userId: number): Promise<MyPageViewData> => {
  if (!MY_API_ENABLED) {
    await wait(MOCK_DELAY_MS)
    const media = readMockProfileMedia(userId)

    return {
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
  }

  const response = await http.get<ApiResponse<MyPageViewData>>(`/users/${userId}/mypage`)
  return unwrapApiData(response.data, '마이페이지 정보를 불러오지 못했습니다.')
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

export const isMyApiEnabled = () => MY_API_ENABLED

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
