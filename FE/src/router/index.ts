import { createRouter, createWebHistory } from 'vue-router'

import { useAuthStore } from '@/domains/auth/stores/authStore'
import { ROUTE_NAMES, ROUTE_PATHS } from '@/shared/constants/routes'

import { routes } from './routes'

const NOTIFICATION_MOCK_SCENARIOS = ['default', 'loading', 'empty', 'error']

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior() {
    return { top: 0 }
  },
})

router.beforeEach(async (to) => {
  const authStore = useAuthStore()

  await authStore.validateStoredSession()

  if (to.meta.requiresAuth && !authStore.isAuthenticated && !isPublicNotificationMockRoute(to)) {
    return {
      name: ROUTE_NAMES.AUTH_LOGIN,
      query: {
        redirect: to.fullPath,
      },
    }
  }

  if (to.meta.guestOnly && authStore.isAuthenticated) {
    if (authStore.user?.onboardingCompleted === false) {
      return { name: ROUTE_NAMES.ONBOARD_PROFILE }
    }

    return ROUTE_PATHS.HOME
  }

  return true
})

const isPublicNotificationMockRoute = (to: { name: unknown; query: Record<string, unknown> }) => {
  if (to.name !== ROUTE_NAMES.NOTIFICATIONS) {
    return false
  }

  const mock = Array.isArray(to.query.mock) ? to.query.mock[0] : to.query.mock

  return typeof mock === 'string' && NOTIFICATION_MOCK_SCENARIOS.includes(mock)
}

export default router
