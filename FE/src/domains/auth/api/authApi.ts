import { http } from '@/shared/api/http'

import type {
  CheckEmailDuplicateRequest,
  GoogleAuthRequest,
  GoogleAuthResponse,
  GoogleLinkRequest,
  GoogleOAuthConfigResponse,
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

// 구글 로그인 client_id 조회. 빌드 환경변수로 따로 들고 있지 않고 BE 설정값을 그대로 읽어온다.
// 값의 출처를 BE 한 곳으로 좁혀 배포 빌드에 값이 빠지는 사고를 막는다.
export const getGoogleOAuthConfig = async () => {
  const { data } = await http.get<ApiResponse<GoogleOAuthConfigResponse>>('/auth/google/config', {
    skipAuth: true,
  })

  return data
}

// 구글 동의 화면 URL을 만든다. redirectUri는 호출부가 넘긴다
// 이후 signInWithGoogle에 넘기는 값과 정확히 같아야 한다(다르면 구글이 토큰 교환을 거부한다).
export const getGoogleOAuthUrl = (redirectUri: string, clientId: string) => {
  const params = new URLSearchParams({
    client_id: clientId,
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