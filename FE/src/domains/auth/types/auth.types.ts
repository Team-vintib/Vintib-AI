export interface SendEmailVerificationCodeRequest {
  email: string
}

export interface CheckEmailDuplicateRequest {
  email: string
}

export interface VerifyEmailCodeRequest {
  email: string
  code: string
}

export interface VerifyEmailCodeResponse {
  verificationToken: string
}

export interface SignUpRequest {
  email: string
  password: string
  name: string
  verificationToken: string
}

export interface SignUpResponse {
  id: number
  email: string
  name: string
  onboardingCompleted: boolean
}

export interface AuthUser {
  id: number
  email: string
  name?: string
  nickname?: string
  onboardingCompleted?: boolean
}

export interface LoginRequest {
  email: string
  password: string
}

export interface ReissueTokenRequest {
  refreshToken: string
}

// BE TokenResponse(signin/reissue 공용)와 동일한 형태(docs/requests/FE/037). user 객체나
// nextStep은 내려주지 않는다 — 프로필(닉네임/온보딩 상태 등)이 필요하면 이 id로
// GET /api/users/{id}(authStore.establishSession)를 따로 호출한다.
export interface LoginResponse {
  accessToken?: string
  refreshToken?: string
  id?: number
}

export interface LinkAccountSessionPayload {
  email?: string
  linkToken: string
}

// docs/requests/FE/036-google-oauth-signin-contract.md
export interface GoogleOAuthConfigResponse {
  clientId: string
}

export interface GoogleAuthRequest {
  code: string
  redirectUri: string
}

export interface GoogleAuthResponse {
  status: 'LOGIN' | 'LINK_REQUIRED'
  accessToken: string | null
  refreshToken: string | null
  id: number | null
  onboardingCompleted: boolean | null
  linkToken: string | null
  email: string | null
}

export interface GoogleLinkRequest {
  linkToken: string
  confirm: boolean
}
