import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import type {
  AuthUser,
  LinkAccountResponse,
  LoginResponse,
  SsafySsoCallbackResponse,
} from '@/domains/auth/types/auth.types'
import {
  clearStoredAuthSession,
  readStoredAuthSession,
  writeStoredAuthSession,
} from '@/shared/api/authTokenStorage'

type AuthSession = LoginResponse | SsafySsoCallbackResponse | LinkAccountResponse

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref('')
  const refreshToken = ref('')
  const user = ref<AuthUser | null>(null)
  const isHydrated = ref(false)

  const isAuthenticated = computed(() => Boolean(accessToken.value))
  const isOnboardingCompleted = computed(() => user.value?.onboardingCompleted === true)

  const setSession = (session: AuthSession, rememberMe = true) => {
    accessToken.value = session.accessToken || ''
    refreshToken.value = session.refreshToken || ''
    user.value = session.user || user.value

    writeStoredAuthSession(
      {
        accessToken: accessToken.value || undefined,
        refreshToken: refreshToken.value || undefined,
        user: user.value || undefined,
      },
      rememberMe ? 'local' : 'session',
    )
  }

  const clearSession = () => {
    accessToken.value = ''
    refreshToken.value = ''
    user.value = null

    clearStoredAuthSession()
  }

  const hydrateSession = () => {
    if (isHydrated.value) {
      return
    }

    const storedSession = readStoredAuthSession()

    accessToken.value = storedSession.accessToken || ''
    refreshToken.value = storedSession.refreshToken || ''
    user.value = (storedSession.user as AuthUser | undefined) || null
    isHydrated.value = true
  }

  return {
    accessToken,
    refreshToken,
    user,
    isAuthenticated,
    isHydrated,
    isOnboardingCompleted,
    setSession,
    clearSession,
    hydrateSession,
  }
})
