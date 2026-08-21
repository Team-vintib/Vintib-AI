import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { logout, reissueToken } from '@/domains/auth/api/authApi'
import type { AuthUser } from '@/domains/auth/types/auth.types'
import { getMyProfile } from '@/domains/my/api/myApi'
import { normalizeApiError } from '@/shared/api/http'
import {
  type AuthStorageType,
  clearStoredAuthSession,
  readStoredAuthSession,
  writeStoredAuthSession,
} from '@/shared/api/authTokenStorage'

// setSession이 받는 user는 이미 알고 있는 낱개 필드만 부분적으로 넘길 때 쓴다(예: 토큰
// 재발급 시 기존 값 유지). 로그인 "직후" 전체 프로필(닉네임/온보딩 상태 등)을 채우려면
// user를 직접 조립하지 말고 establishSession(아래)을 쓴다 — GET /api/users/{id}를 호출해
// 서버가 가진 실제 값으로 채운다(docs/requests/FE/037).
type AuthSession = {
  accessToken?: string | null
  refreshToken?: string | null
  user?: Partial<AuthUser>
}

type LoginTokens = {
  accessToken?: string | null
  refreshToken?: string | null
  id?: number | null
}
type JwtPayload = {
  email?: unknown
  sub?: unknown
}

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref('')
  const refreshToken = ref('')
  const user = ref<AuthUser | null>(null)
  const isHydrated = ref(false)
  const isSessionValidated = ref(false)
  const storageType = ref<AuthStorageType>('local')
  const isValidatingSession = ref(false)
  let sessionValidationPromise: Promise<void> | null = null

  const isAuthenticated = computed(() => Boolean(accessToken.value))
  const isOnboardingCompleted = computed(() => user.value?.onboardingCompleted === true)

  const setSession = (session: AuthSession, rememberMe = true) => {
    accessToken.value = session.accessToken || ''
    refreshToken.value = session.refreshToken || ''
    user.value = resolveSessionUser(session, accessToken.value, user.value)
    storageType.value = rememberMe ? 'local' : 'session'
    isSessionValidated.value = true

    writeStoredAuthSession(
      {
        accessToken: accessToken.value || undefined,
        refreshToken: refreshToken.value || undefined,
        storageType: storageType.value,
        user: user.value || undefined,
      },
      storageType.value,
    )
  }

  const clearSession = () => {
    accessToken.value = ''
    refreshToken.value = ''
    user.value = null
    isSessionValidated.value = true

    clearStoredAuthSession()
  }

  // 로그인/가입/구글 인증 등 "방금 로그인됨"의 단일 진입점이다(037). 토큰부터 저장해 이후
  // API 호출에 Authorization 헤더가 바로 붙게 한 다음, id로 전체 프로필(닉네임/온보딩
  // 상태 등)을 조회해 반영한다. 프로필 조회가 실패해도 로그인 자체(토큰)는 유지한다 —
  // 온보딩 게이트(라우터 가드·403 인터셉터)가 이후 안전망 역할을 한다.
  const establishSession = async (tokens: LoginTokens, rememberMe = true) => {
    setSession({ accessToken: tokens.accessToken, refreshToken: tokens.refreshToken }, rememberMe)

    if (!tokens.id) {
      return
    }

    try {
      const profile = await getMyProfile(tokens.id)

      updateUser({
        id: profile.id,
        email: profile.email,
        name: profile.name,
        nickname: profile.nickname,
        onboardingCompleted: profile.onboardingCompleted,
      })
    } catch {
      // 프로필 조회 실패 — 토큰 기반 세션은 그대로 두고 조용히 넘어간다.
    }
  }

  const updateUser = (nextUser: Partial<AuthUser>) => {
    if (!user.value) {
      return
    }

    user.value = {
      ...user.value,
      ...nextUser,
    }

    writeStoredAuthSession(
      {
        accessToken: accessToken.value || undefined,
        refreshToken: refreshToken.value || undefined,
        storageType: storageType.value,
        user: user.value,
      },
      storageType.value,
    )
  }

  const logoutSession = async () => {
    try {
      await logout()
    } catch {
      // Local session cleanup must still complete when the server logout endpoint is unavailable.
    } finally {
      clearSession()
    }
  }

  const hydrateSession = () => {
    if (isHydrated.value) {
      return
    }

    const storedSession = readStoredAuthSession()

    accessToken.value = storedSession.accessToken || ''
    refreshToken.value = storedSession.refreshToken || ''
    user.value = (storedSession.user as AuthUser | undefined) || null
    storageType.value = storedSession.storageType
    isHydrated.value = true
  }

  const validateStoredSession = async () => {
    hydrateSession()

    if (isSessionValidated.value) {
      return
    }

    if (!refreshToken.value) {
      if (accessToken.value) {
        clearSession()
      }
      isSessionValidated.value = true
      return
    }

    if (sessionValidationPromise) {
      return sessionValidationPromise
    }

    isValidatingSession.value = true
    sessionValidationPromise = reissueToken({ refreshToken: refreshToken.value })
      .then((response) => {
        if (!response.success || !response.data?.accessToken) {
          clearSession()
          isSessionValidated.value = true
          return
        }

        setSession(response.data, storageType.value === 'local')
        isSessionValidated.value = true
      })
      .catch((error: unknown) => {
        const apiError = normalizeApiError(error)

        if (apiError.code !== 'NETWORK_ERROR' && apiError.code !== 'REQUEST_TIMEOUT') {
          clearSession()
          isSessionValidated.value = true
        }
      })
      .finally(() => {
        isValidatingSession.value = false
        sessionValidationPromise = null
      })

    return sessionValidationPromise
  }

  return {
    accessToken,
    refreshToken,
    user,
    isAuthenticated,
    isHydrated,
    isSessionValidated,
    isValidatingSession,
    isOnboardingCompleted,
    setSession,
    establishSession,
    clearSession,
    updateUser,
    logoutSession,
    hydrateSession,
    validateStoredSession,
  }
})

function resolveSessionUser(
  session: AuthSession,
  token: string,
  currentUser: AuthUser | null,
): AuthUser | null {
  const tokenUser = getTokenUser(token)
  const existingUser = tokenUser?.id === currentUser?.id ? currentUser : null
  const resolvedUser = {
    ...existingUser,
    ...tokenUser,
    ...session.user,
  }

  if (typeof resolvedUser.id !== 'number') {
    return null
  }

  return {
    id: resolvedUser.id,
    email: resolvedUser.email ?? '',
    name: resolvedUser.name,
    nickname: resolvedUser.nickname,
    onboardingCompleted: resolvedUser.onboardingCompleted,
  }
}

function getTokenUser(token: string): Partial<AuthUser> | null {
  const payload = parseJwtPayload(token)
  const id = getNumericSubject(payload?.sub)

  if (!id) {
    return null
  }

  return {
    id,
    email: typeof payload?.email === 'string' ? payload.email : '',
  }
}

function parseJwtPayload(token: string): JwtPayload | null {
  const payload = token.split('.')[1]

  if (!payload) {
    return null
  }

  try {
    return JSON.parse(window.atob(toBase64(payload))) as JwtPayload
  } catch {
    return null
  }
}

function toBase64(base64Url: string) {
  const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
  const paddingLength = (4 - (base64.length % 4)) % 4

  return `${base64}${'='.repeat(paddingLength)}`
}

function getNumericSubject(subject: unknown) {
  if (typeof subject !== 'string') {
    return null
  }

  const id = Number(subject)

  return Number.isInteger(id) && id > 0 ? id : null
}
