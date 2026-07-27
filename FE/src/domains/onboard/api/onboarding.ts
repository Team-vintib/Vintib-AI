import { http } from '@/shared/api/http'

import type { ApiResponse } from '@/shared/types/api.types'

export type OnboardingGender = 'MALE' | 'FEMALE'
export type OnboardingMemberType = 'GENERAL' | 'BUSINESS'

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

export interface SaveOnboardingTryOnProfileRequest {
  bodyPhoto?: File
  heightCm?: string
  weightKg?: string
  chest?: string
  waist?: string
  hip?: string
}

export interface CompleteOnboardingRequest {
  memberType: OnboardingMemberType
}

export const saveOnboardingBasicInfo = async (request: SaveBasicInfoRequest) => {
  const { data } = await http.patch<ApiResponse<null>>('/me/onboarding', request)

  return data
}

export const saveOnboardingInterests = async (request: SaveOnboardingInterestsRequest) => {
  const { data } = await http.put<ApiResponse<null>>('/me/interests', request)

  return data
}

export const saveOnboardingTryOnProfile = async (
  request: SaveOnboardingTryOnProfileRequest,
) => {
  const formData = new FormData()

  Object.entries(request).forEach(([field, value]) => {
    if (value !== undefined) {
      formData.append(field, value)
    }
  })

  const { data } = await http.put<ApiResponse<null>>('/me/tryon', formData, {
    headers: {
      'Content-Type': undefined,
    },
  })

  return data
}

export const completeOnboarding = async (request: CompleteOnboardingRequest) => {
  const { data } = await http.post<ApiResponse<null>>('/me/onboarding/complete', request)

  return data
}
