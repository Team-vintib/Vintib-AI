import { BUSINESS_SUBMISSION_DELAY_MS } from '@/domains/biz/constants/businessVerification'
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

const waitForMockSubmission = () =>
  new Promise<void>((resolve) => {
    window.setTimeout(resolve, BUSINESS_SUBMISSION_DELAY_MS)
  })

export const submitBusinessVerification = async (
  request: SubmitBusinessVerificationRequest,
): Promise<ApiResponse<BusinessVerificationResponse>> => {
  void request
  await waitForMockSubmission()

  return {
    success: true,
    data: {
      id: Date.now(),
      status: 'PENDING',
      submittedAt: new Date().toISOString(),
    },
    error: null,
  } satisfies ApiResponse<BusinessVerificationResponse>
}
