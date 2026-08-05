import { http } from '@/shared/api/http'
import type { ApiResponse } from '@/shared/types/api.types'

export type BusinessVerificationStatus = 'NONE' | 'PENDING' | 'APPROVED' | 'REJECTED'

export interface SubmitBusinessVerificationRequest {
  businessRegistrationNumber: string
  businessName: string
  representativeName: string
  certificate: File
}

export interface BusinessVerificationResponse {
  status: BusinessVerificationStatus
  businessNumber: string | null
  businessName: string | null
  representativeName: string | null
  certificateUrl: string | null
  submittedAt: string
  verifiedAt: string | null
}

interface BusinessCertificateUploadUrlResponse {
  key: string
  uploadUrl: string
  expiresInSeconds: number
}

export const submitBusinessVerification = async (
  userId: number,
  request: SubmitBusinessVerificationRequest,
): Promise<ApiResponse<BusinessVerificationResponse>> => {
  const certificateKey = await uploadBusinessCertificate(userId, request.certificate)
  const { data } = await http.post<ApiResponse<BusinessVerificationResponse>>(
    `/users/${userId}/business`,
    {
      businessNumber: request.businessRegistrationNumber,
      businessName: request.businessName,
      representativeName: request.representativeName,
      certificateKey,
    },
  )

  return data
}

const uploadBusinessCertificate = async (userId: number, file: File) => {
  const { data } = await http.post<ApiResponse<BusinessCertificateUploadUrlResponse>>(
    `/users/${userId}/business/upload-url`,
    { contentType: file.type || 'application/octet-stream' },
  )
  const upload = unwrapApiData(data, '사업자등록증 업로드 URL을 발급하지 못했습니다.')

  const uploadResponse = await fetch(upload.uploadUrl, {
    method: 'PUT',
    headers: {
      'Content-Type': file.type || 'application/octet-stream',
    },
    body: file,
  })

  if (!uploadResponse.ok) {
    throw new Error('사업자등록증 이미지를 업로드하지 못했습니다.')
  }

  return upload.key
}

const unwrapApiData = <T>(response: ApiResponse<T>, fallbackMessage: string) => {
  if (!response.success || response.data === null) {
    throw new Error(response.error?.message ?? fallbackMessage)
  }

  return response.data
}
