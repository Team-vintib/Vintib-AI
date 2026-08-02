import {
  mockMyPageViewData,
  mockMyProfile,
} from '@/domains/my/constants/myMockData'
import type {
  MyPageViewData,
  MyProfile,
  MyProfileUpdateRequest,
} from '@/domains/my/types/my.types'
import { http } from '@/shared/api/http'
import type { ApiResponse } from '@/shared/types/api.types'

const MOCK_DELAY_MS = 250
const MY_API_ENABLED = import.meta.env.VITE_MY_API_ENABLED === 'true'

const wait = (delay: number) =>
  new Promise<void>((resolve) => {
    window.setTimeout(resolve, delay)
  })

export const getMyPageViewData = async (userId: number): Promise<MyPageViewData> => {
  if (!MY_API_ENABLED) {
    await wait(MOCK_DELAY_MS)
    return {
      ...mockMyPageViewData,
      summary: {
        ...mockMyPageViewData.summary,
        profile: {
          ...mockMyPageViewData.summary.profile,
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
      id: userId,
    }
  }

  const response = await http.get<ApiResponse<MyProfile>>('/me')
  return unwrapApiData(response.data, '회원 정보를 불러오지 못했습니다.')
}

export const updateMyProfile = async (
  userId: number,
  request: MyProfileUpdateRequest,
): Promise<MyProfile> => {
  if (!MY_API_ENABLED) {
    await wait(MOCK_DELAY_MS)
    return {
      ...mockMyProfile,
      ...request,
      id: userId,
    }
  }

  const response = await http.patch<ApiResponse<MyProfile>>(`/users/${userId}`, request)
  return unwrapApiData(response.data, '회원 정보를 저장하지 못했습니다.')
}

export const isMyApiEnabled = () => MY_API_ENABLED

const unwrapApiData = <T>(response: ApiResponse<T>, fallbackMessage: string) => {
  if (!response.success || response.data === null) {
    throw new Error(response.error?.message ?? fallbackMessage)
  }

  return response.data
}

