import { getGoogleOAuthConfig, getGoogleOAuthUrl } from '@/domains/auth/api/authApi'
import { ROUTE_PATHS } from '@/shared/constants/routes'

const GOOGLE_OAUTH_SOURCE_STORAGE_KEY = 'vintib_google_oauth_source'

export type GoogleOAuthSource = 'login' | 'signup'

// signInWithGoogle에 넘기는 redirectUri와 정확히 같은 값이어야 한다.
// 한 곳에서만 계산해서 시작(리다이렉트)과 콜백(토큰 교환) 양쪽이 항상 같은 값을 쓰게 한다.
export const getGoogleOAuthRedirectUri = () =>
  `${window.location.origin}${ROUTE_PATHS.AUTH_GOOGLE_CALLBACK}`

// client_id를 BE(GET /auth/google/config)에서 읽어온 뒤에만 리다이렉트한다.
// 실패 시, 호출부가 잡아서 사용자에게 안내할 수 있도록 그대로 던진다.
export const startGoogleOAuth = async (source: GoogleOAuthSource) => {
  const response = await getGoogleOAuthConfig()

  if (!response.success || !response.data?.clientId) {
    throw new Error(response.error?.message || 'Google 로그인 설정을 불러오지 못했습니다.')
  }

  window.sessionStorage.setItem(GOOGLE_OAUTH_SOURCE_STORAGE_KEY, source)
  window.location.assign(getGoogleOAuthUrl(getGoogleOAuthRedirectUri(), response.data.clientId))
}

export const readGoogleOAuthSource = (): GoogleOAuthSource =>
  window.sessionStorage.getItem(GOOGLE_OAUTH_SOURCE_STORAGE_KEY) === 'login' ? 'login' : 'signup'

export const clearGoogleOAuthSource = () => {
  window.sessionStorage.removeItem(GOOGLE_OAUTH_SOURCE_STORAGE_KEY)
}