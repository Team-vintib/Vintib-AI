import { http } from '@/shared/api/http'

import type {
  CheckEmailDuplicateRequest,
  GoogleAuthRequest,
  GoogleAuthResponse,
  GoogleLinkRequest,
  LoginRequest,
  LoginResponse,
  ReissueTokenRequest,
  SendEmailVerificationCodeRequest,
  SignUpRequest,
  SignUpResponse,
  VerifyEmailCodeRequest,
  VerifyEmailCodeResponse,
} from '@/domains/auth/types/auth.types'
import type { ApiResponse } from '@/shared/types/api.types'

const GOOGLE_OAUTH_ENDPOINT = 'https://accounts.google.com/o/oauth2/v2/auth'

export const checkEmailDuplicate = async (request: CheckEmailDuplicateRequest) => {
  const { data } = await http.post<ApiResponse<null>>('/auth/email/check-duplicate', request, {
    skipAuth: true,
  })

  return data
}

export const sendEmailVerificationCode = async (request: SendEmailVerificationCodeRequest) => {
  const { data } = await http.post<ApiResponse<null>>('/auth/email/send-code', request, {
    skipAuth: true,
  })

  return data
}

export const verifyEmailCode = async (request: VerifyEmailCodeRequest) => {
  const { data } = await http.post<ApiResponse<VerifyEmailCodeResponse>>(
    '/auth/email/verify-code',
    request,
    {
      skipAuth: true,
    },
  )

  return data
}

export const signUp = async (request: SignUpRequest) => {
  const { data } = await http.post<ApiResponse<SignUpResponse>>('/auth/signup', request, {
    skipAuth: true,
  })

  return data
}

export const login = async (request: LoginRequest) => {
  const { data } = await http.post<ApiResponse<LoginResponse>>('/auth/signin', request, {
    skipAuth: true,
  })

  return data
}

export const reissueToken = async (request: ReissueTokenRequest) => {
  const { data } = await http.post<ApiResponse<LoginResponse>>('/auth/reissue', request, {
    skipAuth: true,
  })

  return data
}

export const logout = async () => {
  const { data } = await http.post<ApiResponse<null>>('/auth/logout')

  return data
}

// 구글 동의 화면 URL을 만든다(docs/requests/FE/036) — client_id는 공개값이라 FE가 직접 들고
// 있는다. redirectUri는 호출부가 넘긴다 — 이 값이 이후 signInWithGoogle에 넘기는 값과 정확히
// 같아야 한다(다르면 구글이 토큰 교환을 거부한다).
export const getGoogleOAuthUrl = (redirectUri: string) => {
  const params = new URLSearchParams({
    client_id: import.meta.env.VITE_GOOGLE_CLIENT_ID ?? '',
    redirect_uri: redirectUri,
    response_type: 'code',
    scope: 'openid email profile',
  })

  return `${GOOGLE_OAUTH_ENDPOINT}?${params.toString()}`
}

export const signInWithGoogle = async (request: GoogleAuthRequest) => {
  const { data } = await http.post<ApiResponse<GoogleAuthResponse>>('/auth/google', request, {
    skipAuth: true,
  })

  return data
}

export const confirmGoogleLink = async (request: GoogleLinkRequest) => {
  const { data } = await http.post<ApiResponse<GoogleAuthResponse>>('/auth/google/link', request)

  return data
}
