import { http } from '@/shared/api/http'

import type {
  SendEmailVerificationCodeRequest,
  SignUpRequest,
  SignUpResponse,
  VerifyEmailCodeRequest,
  VerifyEmailCodeResponse,
} from '@/domains/auth/types/auth.types'
import type { ApiResponse } from '@/shared/types/api.types'

export const sendEmailVerificationCode = async (request: SendEmailVerificationCodeRequest) => {
  const { data } = await http.post<ApiResponse<null>>('/auth/email/send-code', request)

  return data
}

export const verifyEmailCode = async (request: VerifyEmailCodeRequest) => {
  const { data } = await http.post<ApiResponse<VerifyEmailCodeResponse>>(
    '/auth/email/verify-code',
    request,
  )

  return data
}

export const signUp = async (request: SignUpRequest) => {
  const { data } = await http.post<ApiResponse<SignUpResponse>>('/auth/signup', request)

  return data
}
