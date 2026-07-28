import { http } from '@/shared/api/http'

import type {
  CheckEmailDuplicateRequest,
  LinkAccountRequest,
  LinkAccountResponse,
  LoginRequest,
  LoginResponse,
  SendEmailVerificationCodeRequest,
  SignUpRequest,
  SignUpResponse,
  SsafySsoCallbackRequest,
  SsafySsoCallbackResponse,
  VerifyEmailCodeRequest,
  VerifyEmailCodeResponse,
} from '@/domains/auth/types/auth.types'
import type { ApiResponse } from '@/shared/types/api.types'

const SSAFY_SSO_START_PATH = '/auth/sso/ssafy'

export const checkEmailDuplicate = async (request: CheckEmailDuplicateRequest) => {
  const { data } = await http.post<ApiResponse<null>>('/auth/email/check-duplicate', request)

  return data
}

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

export const login = async (request: LoginRequest) => {
  const { data } = await http.post<ApiResponse<LoginResponse>>('/auth/login', request)

  return data
}

export const completeSsafySsoCallback = async (request: SsafySsoCallbackRequest) => {
  const { data } = await http.post<ApiResponse<SsafySsoCallbackResponse>>(
    '/auth/ssafy/callback',
    request,
  )

  return data
}

export const linkSsafyAccount = async (request: LinkAccountRequest) => {
  const { data } = await http.post<ApiResponse<LinkAccountResponse>>(
    '/auth/ssafy/link-account',
    request,
  )

  return data
}

export const getSsafySsoStartUrl = () => {
  const baseUrl = import.meta.env.VITE_API_BASE_URL ?? '/api'

  return `${baseUrl.replace(/\/$/, '')}${SSAFY_SSO_START_PATH}`
}
