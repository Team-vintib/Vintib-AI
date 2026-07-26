export interface SendEmailVerificationCodeRequest {
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

export type AuthNextStep = 'HOME' | 'ONBOARD_PROFILE' | 'LINK_ACCOUNT' | 'SIGNUP_COMPLETE'

export interface SsafySsoCallbackRequest {
  authorizationCode: string
  redirectUri: string
}

export interface SsafySsoUser {
  id?: number
  email?: string
  name?: string
}

export interface SsafySsoCallbackResponse {
  accessToken?: string
  refreshToken?: string
  linked?: boolean
  nextStep?: AuthNextStep
  user?: SsafySsoUser
}
