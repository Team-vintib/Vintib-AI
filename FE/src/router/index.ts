import { createRouter, createWebHistory } from 'vue-router'

import { useAuthStore } from '@/domains/auth/stores/authStore'
import { ROUTE_NAMES, ROUTE_PATHS } from '@/shared/constants/routes'

import { routes } from './routes'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior() {
    return { top: 0 }
  },
})

router.beforeEach((to) => {
  const authStore = useAuthStore()

  authStore.hydrateSession()

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
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

export default router
