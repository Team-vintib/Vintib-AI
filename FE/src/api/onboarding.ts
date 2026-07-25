import httpClient from '@/api/httpClient'

import type { ApiResponse } from '@/api/types'

export type OnboardingGender = 'MALE' | 'FEMALE'

export interface SaveBasicInfoRequest {
  nickname: string
  gender: OnboardingGender
  phoneNumber: string
  postalCode: string | null
  address: string
  detailAddress: string
}

export const saveOnboardingBasicInfo = async (request: SaveBasicInfoRequest) => {
  const { data } = await httpClient.patch<ApiResponse<null>>('/api/me/onboarding', request)

  return data
}
