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

export type AuthNextStep = 'HOME' | 'ONBOARD_PROFILE' | 'LINK_ACCOUNT'

export interface SsafySsoCallbackRequest {
  authorizationCode: string
  redirectUri: string
}

export interface SsafySsoCallbackResponse {
  accessToken?: string
  email?: string
  linked?: boolean
  nextStep?: AuthNextStep
}
