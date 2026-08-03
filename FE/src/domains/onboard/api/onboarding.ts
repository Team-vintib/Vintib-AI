import { http } from '@/shared/api/http'
import {
  readImageFileAsDataUrl,
  saveMockDefaultTryOnImage,
} from '@/shared/api/mockProfileMediaStorage'
import { saveMockUserInterests, type UserInterests } from '@/shared/api/mockInterestStorage'

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

export const saveOnboardingBasicInfo = async (request: SaveBasicInfoRequest) => {
  if (!ONBOARDING_API_ENABLED) {
    return ONBOARDING_SUCCESS_RESPONSE
  }

  const { data } = await http.patch<ApiResponse<null>>('/me/onboarding', request)

  return data
}

export const saveOnboardingInterests = async (
  request: SaveOnboardingInterestsRequest,
  options: SaveOnboardingInterestsOptions = {},
): Promise<ApiResponse<UserInterests | null>> => {
  if (!ONBOARDING_API_ENABLED) {
    return {
      success: true,
      data: saveMockUserInterests(options.userId, request.brandIds, request.categoryIds),
      error: null,
    }
  }

  if (!options.userId) {
    throw new Error('관심 정보를 저장할 회원 ID가 없습니다.')
  }

  const { data } = await http.put<ApiResponse<UserInterests>>(
    `/users/${options.userId}/interests`,
    request,
  )

  return data
}

export const saveOnboardingTryOnProfile = async (
  request: SaveOnboardingTryOnProfileRequest,
  options: SaveOnboardingTryOnProfileOptions = {},
): Promise<ApiResponse<SaveOnboardingTryOnProfileResponse | null>> => {
  if (!ONBOARDING_API_ENABLED) {
    if (!request.bodyPhoto) {
      return ONBOARDING_SUCCESS_RESPONSE
    }

    const defaultTryOnImageUrl = await readImageFileAsDataUrl(
      request.bodyPhoto,
      'AI 시착용 사진을 읽지 못했습니다.',
    )

    saveMockDefaultTryOnImage(options.userId, defaultTryOnImageUrl)

    return {
      success: true,
      data: {
        defaultTryOnImageUrl,
      },
      error: null,
    }
  }

  const formData = new FormData()

  Object.entries(request).forEach(([field, value]) => {
    if (value !== undefined) {
      formData.append(field, value)
    }
  })

  const { data } = await http.put<ApiResponse<SaveOnboardingTryOnProfileResponse | null>>('/me/tryon', formData, {
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
