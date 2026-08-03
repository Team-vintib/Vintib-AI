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

export interface LinkAccountRequest {
  linkToken: string
  agree: boolean
}

export interface LinkAccountResponse {
  accessToken?: string
  refreshToken?: string
  user?: AuthUser
  nextStep?: AuthNextStep
}

export interface LinkAccountSessionPayload {
  email?: string
  linkToken: string
}

export interface SsafySsoCallbackRequest {
  authorizationCode: string
  redirectUri: string
}

export interface SsafySsoCallbackResponse {
  accessToken?: string
  refreshToken?: string
  email?: string
  linked?: boolean
  linkToken?: string
  nextStep?: AuthNextStep
  user?: AuthUser
}
