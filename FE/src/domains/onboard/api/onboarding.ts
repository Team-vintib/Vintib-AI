import { http } from '@/shared/api/http'

import type { ApiResponse } from '@/shared/types/api.types'

export type OnboardingGender = 'MALE' | 'FEMALE'

export interface SaveBasicInfoRequest {
  nickname: string
  gender: OnboardingGender
  phoneNumber: string
  postalCode: string | null
  address: string
  detailAddress: string
}

export interface SaveOnboardingInterestsRequest {
  brandIds: string[]
  categoryIds: string[]
}

export const saveOnboardingBasicInfo = async (request: SaveBasicInfoRequest) => {
  const { data } = await http.patch<ApiResponse<null>>('/me/onboarding', request)

  return data
}

export const saveOnboardingInterests = async (request: SaveOnboardingInterestsRequest) => {
  const { data } = await http.put<ApiResponse<null>>('/me/interests', request)

  return data
}
