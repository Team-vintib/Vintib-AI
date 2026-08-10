import { createRouter, createWebHistory } from 'vue-router'

import { useAuthStore } from '@/domains/auth/stores/authStore'
import { ROUTE_NAMES, ROUTE_PATHS } from '@/shared/constants/routes'

import { routes } from './routes'

// 온보딩 화면 자체는 온보딩 미완료 가드 대상에서 제외한다 — 그렇지 않으면 온보딩 화면으로
// 보내는 리다이렉트가 자기 자신을 다시 리다이렉트하는 무한 루프가 된다.
const ONBOARDING_ROUTE_NAMES = new Set<string>([
  ROUTE_NAMES.ONBOARD_PROFILE,
  ROUTE_NAMES.ONBOARD_INTERESTS,
  ROUTE_NAMES.ONBOARD_TRYON,
  ROUTE_NAMES.ONBOARD_MEMBER_TYPE,
])

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

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return {
      name: ROUTE_NAMES.AUTH_LOGIN,
      query: {
        redirect: to.fullPath,
      },
    }
  }

  // 온보딩(필수 정보 입력)을 마치지 않은 회원은 온보딩 화면 자신을 제외한 모든 인증 필요
  // 화면에서 온보딩으로 되돌려보낸다. BE의 OnboardingRequiredFilter가 같은 회원을
  // API 레벨에서 이미 403(U004)으로 막고 있어, 이 가드는 그 차단을 화면 레벨에서 앞서
  // 드러내는 역할이다.
  if (
    to.meta.requiresAuth &&
    authStore.isAuthenticated &&
    authStore.user?.onboardingCompleted === false &&
    !ONBOARDING_ROUTE_NAMES.has(to.name as string)
  ) {
    return { name: ROUTE_NAMES.ONBOARD_PROFILE }
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