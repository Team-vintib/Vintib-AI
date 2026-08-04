import { http } from '@/shared/api/http'

import { saveMyTryOnProfile } from '@/domains/tryon/api/tryOnProfileApi'

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

export interface SaveBasicInfoOptions {
  userId?: number | null
}

export interface SaveOnboardingInterestsRequest {
  brandIds: number[]
  categoryIds: number[]
}

export interface SaveOnboardingInterestsOptions {
  userId?: number | null
}

export interface SaveOnboardingTryOnProfileRequest {
  bodyPhoto?: File
  heightCm?: string
  weightKg?: string
  chest?: string
  waist?: string
  hip?: string
}

export interface SaveOnboardingTryOnProfileOptions {
  userId?: number | null
}

export interface SaveOnboardingTryOnProfileResponse {
  defaultTryOnImageUrl: string | null
}

export interface CompleteOnboardingRequest {
  memberType: OnboardingMemberType
}

export interface CompleteOnboardingOptions {
  userId?: number | null
}

export interface CompleteOnboardingResponse {
  onboardingCompleted: boolean
  memberType: OnboardingMemberType
  status: string
}

export const saveOnboardingBasicInfo = async (
  request: SaveBasicInfoRequest,
  options: SaveBasicInfoOptions = {},
) => {
  if (!options.userId) {
    if (!ONBOARDING_API_ENABLED) {
      return ONBOARDING_SUCCESS_RESPONSE
    }

    throw new Error('기본 정보를 저장할 회원 ID가 없습니다.')
  }

  const { data } = await http.patch<ApiResponse<null>>(`/users/${options.userId}`, request)

  return data
}

export const saveOnboardingInterests = async (
  request: SaveOnboardingInterestsRequest,
  options: SaveOnboardingInterestsOptions = {},
): Promise<ApiResponse<null>> => {
  if (!options.userId) {
    if (!ONBOARDING_API_ENABLED) {
      void request
      return ONBOARDING_SUCCESS_RESPONSE
    }

    throw new Error('관심 정보를 저장할 회원 ID가 없습니다.')
  }

  const { data } = await http.put<ApiResponse<null>>(
    `/users/${options.userId}/interests`,
    request,
  )

  return data
}

export const saveOnboardingTryOnProfile = async (
  request: SaveOnboardingTryOnProfileRequest,
  options: SaveOnboardingTryOnProfileOptions = {},
): Promise<ApiResponse<SaveOnboardingTryOnProfileResponse | null>> => {
  const profile = await saveMyTryOnProfile(request, options.userId)

  return {
    success: true,
    data: {
      defaultTryOnImageUrl: profile.bodyPhotoUrl,
    },
    error: null,
  }
}

export const completeOnboarding = async (
  request: CompleteOnboardingRequest,
  options: CompleteOnboardingOptions = {},
): Promise<ApiResponse<CompleteOnboardingResponse | null>> => {
  if (!options.userId) {
    if (!ONBOARDING_API_ENABLED) {
      return ONBOARDING_SUCCESS_RESPONSE
    }

    throw new Error('온보딩을 완료할 회원 ID가 없습니다.')
  }

  const { data } = await http.patch<ApiResponse<CompleteOnboardingResponse | null>>(
    `/users/${options.userId}/member-type`,
    request,
  )

  return data
}
