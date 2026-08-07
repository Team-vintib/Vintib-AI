import { getGoogleOAuthUrl } from '@/domains/auth/api/authApi'
import { ROUTE_PATHS } from '@/shared/constants/routes'

const GOOGLE_OAUTH_SOURCE_STORAGE_KEY = 'vintib_google_oauth_source'

export type GoogleOAuthSource = 'login' | 'signup'

// signInWithGoogle에 넘기는 redirectUri와 정확히 같은 값이어야 한다(036 참고) — 한 곳에서만
// 계산해서 시작(리다이렉트)과 콜백(토큰 교환) 양쪽이 항상 같은 값을 쓰게 한다.
export const getGoogleOAuthRedirectUri = () =>
  `${window.location.origin}${ROUTE_PATHS.AUTH_GOOGLE_CALLBACK}`

export const startGoogleOAuth = (source: GoogleOAuthSource) => {
  window.sessionStorage.setItem(GOOGLE_OAUTH_SOURCE_STORAGE_KEY, source)
  window.location.assign(getGoogleOAuthUrl(getGoogleOAuthRedirectUri()))
}

export const readGoogleOAuthSource = (): GoogleOAuthSource =>
  window.sessionStorage.getItem(GOOGLE_OAUTH_SOURCE_STORAGE_KEY) === 'login' ? 'login' : 'signup'

export const clearGoogleOAuthSource = () => {
  window.sessionStorage.removeItem(GOOGLE_OAUTH_SOURCE_STORAGE_KEY)
}
