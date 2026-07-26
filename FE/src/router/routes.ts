import type { RouteRecordRaw } from 'vue-router'

import { ROUTE_NAMES, ROUTE_PATHS } from '@/shared/constants/routes'

export const routes: RouteRecordRaw[] = [
  {
    path: ROUTE_PATHS.AUTH_SIGNUP,
    name: ROUTE_NAMES.AUTH_SIGNUP,
    component: () => import('@/domains/auth/pages/SignupPage.vue'),
  },
  {
    path: ROUTE_PATHS.AUTH_SSAFY,
    name: ROUTE_NAMES.AUTH_SSAFY,
    component: () => import('@/domains/auth/pages/SsafySsoPage.vue'),
  },
  {
    path: ROUTE_PATHS.AUTH_SSAFY_CALLBACK,
    name: ROUTE_NAMES.AUTH_SSAFY_CALLBACK,
    component: () => import('@/domains/auth/pages/SsafySsoCallbackPage.vue'),
  },
  {
    path: ROUTE_PATHS.AUTH_LINK_ACCOUNT,
    name: ROUTE_NAMES.AUTH_LINK_ACCOUNT,
    component: () => import('@/domains/auth/pages/AuthLinkAccountPage.vue'),
  },
  {
    path: ROUTE_PATHS.ONBOARD_PROFILE,
    name: ROUTE_NAMES.ONBOARD_PROFILE,
    component: () => import('@/domains/onboard/pages/OnboardingBasicInfoView.vue'),
  },
  {
    path: ROUTE_PATHS.ONBOARD_INTERESTS,
    name: ROUTE_NAMES.ONBOARD_INTERESTS,
    component: () => import('@/domains/onboard/pages/OnboardingInterestsView.vue'),
  },
  {
    path: ROUTE_PATHS.ONBOARD_TRYON,
    name: ROUTE_NAMES.ONBOARD_TRYON,
    component: () => import('@/domains/onboard/pages/OnboardingTryOnView.vue'),
  },
]
