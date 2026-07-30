import { http } from '@/shared/api/http'

import type { ApiResponse } from '@/shared/types/api.types'

const ONBOARDING_API_ENABLED = import.meta.env.VITE_ONBOARDING_API_ENABLED === 'true'
const ONBOARDING_SUCCESS_RESPONSE: ApiResponse<null> = {
  success: true,
  data: null,
  error: null,
}

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
  if (!ONBOARDING_API_ENABLED) {
    return ONBOARDING_SUCCESS_RESPONSE
  }

  const { data } = await http.patch<ApiResponse<null>>('/me/onboarding', request)

  return data
}

export const saveOnboardingInterests = async (request: SaveOnboardingInterestsRequest) => {
  if (!ONBOARDING_API_ENABLED) {
    return ONBOARDING_SUCCESS_RESPONSE
  }

  const { data } = await http.put<ApiResponse<null>>('/me/interests', request)

  return data
}

export const saveOnboardingTryOnProfile = async (
  request: SaveOnboardingTryOnProfileRequest,
) => {
  if (!ONBOARDING_API_ENABLED) {
    return ONBOARDING_SUCCESS_RESPONSE
  }

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
  if (!ONBOARDING_API_ENABLED) {
    return ONBOARDING_SUCCESS_RESPONSE
  }

  const { data } = await http.post<ApiResponse<null>>('/me/onboarding/complete', request)

  return data
}
