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

export type AuthNextStep = 'HOME' | 'ONBOARD_PROFILE' | 'LINK_ACCOUNT'

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

export interface LoginResponse {
  accessToken?: string
  refreshToken?: string
  user?: AuthUser
  nextStep?: AuthNextStep
}

export interface LinkAccountSessionPayload {
  email?: string
  linkToken: string
}

// docs/requests/FE/036-google-oauth-signin-contract.md
export interface GoogleAuthRequest {
  code: string
  redirectUri: string
}

export interface GoogleAuthResponse {
  status: 'LOGIN' | 'LINK_REQUIRED'
  accessToken: string | null
  refreshToken: string | null
  onboardingCompleted: boolean | null
  linkToken: string | null
  email: string | null
}

export interface GoogleLinkRequest {
  linkToken: string
  confirm: boolean
}
