import type { ApiResponse } from '@/shared/types/api.types'

export type BusinessVerificationStatus = 'NONE' | 'PENDING' | 'APPROVED' | 'REJECTED'

export interface SubmitBusinessVerificationRequest {
  businessRegistrationNumber: string
  businessName: string
  representativeName: string
  certificate: File
}

export interface BusinessVerificationResponse {
  id: number
  status: BusinessVerificationStatus
  submittedAt: string
}

export const submitBusinessVerification = async (
  request: SubmitBusinessVerificationRequest,
): Promise<ApiResponse<BusinessVerificationResponse>> => {
  void request
  return {
    success: false,
    data: null,
    error: {
      code: 'BUSINESS_VERIFICATION_API_NOT_CONNECTED',
      message: '사업자 인증 API가 아직 연결되지 않았습니다.',
    },
  }
}
