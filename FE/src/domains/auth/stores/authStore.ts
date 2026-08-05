import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { logout, reissueToken } from '@/domains/auth/api/authApi'
import type {
  AuthUser,
  LinkAccountResponse,
  LoginResponse,
  SsafySsoCallbackResponse,
} from '@/domains/auth/types/auth.types'
import { normalizeApiError } from '@/shared/api/http'
import {
  type AuthStorageType,
  clearStoredAuthSession,
  readStoredAuthSession,
  writeStoredAuthSession,
} from '@/shared/api/authTokenStorage'

type AuthSession = LoginResponse | SsafySsoCallbackResponse | LinkAccountResponse
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
