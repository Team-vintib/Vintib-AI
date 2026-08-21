import axios, { AxiosError } from 'axios'

import {
  clearStoredAuthSession,
  getStoredAccessToken,
  readStoredAuthSession,
  writeStoredAuthSession,
} from '@/shared/api/authTokenStorage'
import { ROUTE_PATHS } from '@/shared/constants/routes'
import type { ApiErrorBody, ApiResponse } from '@/shared/types/api.types'

const DEFAULT_TIMEOUT_MS = 10_000

declare module 'axios' {
  export interface AxiosRequestConfig {
    skipAuth?: boolean
    retryAfterTokenRefresh?: boolean
  }

  export interface InternalAxiosRequestConfig {
    skipAuth?: boolean
    retryAfterTokenRefresh?: boolean
  }
}

interface TokenResponse {
  accessToken?: string
  refreshToken?: string
}

let tokenRefreshPromise: Promise<TokenResponse> | null = null

export const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api',
  timeout: DEFAULT_TIMEOUT_MS,
  headers: {
    'Content-Type': 'application/json',
  },
})

http.interceptors.request.use((config) => {
  if (config.skipAuth) {
    return config
  }

  const accessToken = getStoredAccessToken()

  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`
  }

  return config
})

http.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ApiResponse<unknown> | ApiErrorBody>) => {
    const originalRequest = error.config
    const apiError = getAxiosErrorBody(error)

    // 온보딩 미완료 회원이 화이트리스트 밖 API를 호출하면 BE(OnboardingRequiredFilter)가
    // 403 U004를 준다. 로그인 자체는 유효하므로 세션은 지우지 않고 온보딩 화면으로만 보낸다
    // 라우터 가드가 화면 이동은 대부분 막아주지만, 공개 화면 안의
    // 개별 액션(예: 상품 목록에서 찜하기)처럼 화면 자체는 requiresAuth가 아닌 경우를 위한
    // 안전망이다.
    if (error.response?.status === 403 && apiError.code === 'U004') {
      redirectToOnboarding()
      throw error
    }

    if (
      !originalRequest ||
      originalRequest.skipAuth ||
      originalRequest.retryAfterTokenRefresh ||
      error.response?.status !== 401 ||
      (apiError.code !== 'U010' && apiError.code !== 'U011')
    ) {
      throw error
    }

    try {
      const nextTokens = await refreshStoredToken()

      if (!nextTokens.accessToken) {
        throw error
      }

      originalRequest.retryAfterTokenRefresh = true
      originalRequest.headers.Authorization = `Bearer ${nextTokens.accessToken}`

      return http(originalRequest)
    } catch {
      clearStoredAuthSession()
      redirectToLogin()
      throw error
    }
  },
)

export function normalizeApiError(error: unknown): ApiErrorBody {
  if (axios.isAxiosError<ApiResponse<unknown> | ApiErrorBody>(error)) {
    return getAxiosErrorBody(error)
  }

  return {
    code: 'UNKNOWN_ERROR',
    message: '알 수 없는 오류가 발생했습니다.',
  }
}

function getAxiosErrorBody(error: AxiosError<ApiResponse<unknown> | ApiErrorBody>): ApiErrorBody {
  if (isApiResponse(error.response?.data) && error.response.data.error) {
    return error.response.data.error
  }

  if (isApiErrorBody(error.response?.data)) {
    return error.response.data
  }

  if (error.code === 'ECONNABORTED') {
    return {
      code: 'REQUEST_TIMEOUT',
      message: '요청 시간이 초과되었습니다.',
    }
  }

  return {
    code: 'NETWORK_ERROR',
    message: '네트워크 연결을 확인해주세요.',
  }
}

async function refreshStoredToken() {
  const storedSession = readStoredAuthSession()

  if (!storedSession.refreshToken) {
    clearStoredAuthSession()
    redirectToLogin()
    return {}
  }

  tokenRefreshPromise ??= axios
    .post<ApiResponse<TokenResponse>>(
      '/auth/reissue',
      { refreshToken: storedSession.refreshToken },
      {
        baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api',
        timeout: DEFAULT_TIMEOUT_MS,
        headers: {
          'Content-Type': 'application/json',
        },
      },
    )
    .then((response) => {
      const data = response.data.data ?? {}

      if (!response.data.success || !data.accessToken) {
        clearStoredAuthSession()
        redirectToLogin()
        return {}
      }

      writeStoredAuthSession(
        {
          accessToken: data.accessToken,
          refreshToken: data.refreshToken || storedSession.refreshToken,
          storageType: storedSession.storageType,
          user: storedSession.user,
        },
        storedSession.storageType,
      )

      return data
    })
    .finally(() => {
      tokenRefreshPromise = null
    })

  return tokenRefreshPromise
}

function redirectToLogin() {
  if (typeof window === 'undefined' || window.location.pathname === '/auth/login') {
    return
  }

  const redirect = `${window.location.pathname}${window.location.search}`
  window.location.assign(`/auth/login?redirect=${encodeURIComponent(redirect)}`)
}

const ONBOARDING_PATHS: string[] = [
  ROUTE_PATHS.ONBOARD_PROFILE,
  ROUTE_PATHS.ONBOARD_INTERESTS,
  ROUTE_PATHS.ONBOARD_TRYON,
  ROUTE_PATHS.ONBOARD_MEMBER_TYPE,
]

function redirectToOnboarding() {
  if (typeof window === 'undefined' || ONBOARDING_PATHS.includes(window.location.pathname)) {
    return
  }

  window.location.assign(ROUTE_PATHS.ONBOARD_PROFILE)
}

function isApiResponse(data: unknown): data is ApiResponse<unknown> {
  return Boolean(data && typeof data === 'object' && 'success' in data)
}

function isApiErrorBody(data: unknown): data is ApiErrorBody {
  return Boolean(
    data &&
    typeof data === 'object' &&
    'code' in data &&
    'message' in data &&
    typeof data.code === 'string' &&
    typeof data.message === 'string',
  )
}