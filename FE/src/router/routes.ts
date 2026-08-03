import type { RouteRecordRaw } from 'vue-router'

import { ROUTE_NAMES, ROUTE_PATHS } from '@/shared/constants/routes'

export const routes: RouteRecordRaw[] = [
  {
    path: ROUTE_PATHS.HOME,
    name: ROUTE_NAMES.HOME,
    component: () => import('@/domains/home/pages/HomePage.vue'),
  },
  {
    path: ROUTE_PATHS.SEARCH,
    name: ROUTE_NAMES.SEARCH,
    component: () => import('@/domains/search/pages/SearchResultsPage.vue'),
    meta: { title: '검색' },
  },
  {
    path: ROUTE_PATHS.FOLLOWING_HOME,
    name: ROUTE_NAMES.FOLLOWING_HOME,
    component: () => import('@/shared/components/RoutePlaceholder.vue'),
    meta: { requiresAuth: true, title: '팔로잉 홈' },
  },
  {
    path: ROUTE_PATHS.AUTH_LOGIN,
    name: ROUTE_NAMES.AUTH_LOGIN,
    component: () => import('@/domains/auth/pages/LoginPage.vue'),
    meta: { guestOnly: true },
  },
  {
    path: ROUTE_PATHS.AUTH_SIGNUP,
    name: ROUTE_NAMES.AUTH_SIGNUP,
    component: () => import('@/domains/auth/pages/SignupEntryPage.vue'),
    meta: { guestOnly: true },
  },
  {
    path: ROUTE_PATHS.AUTH_SIGNUP_EMAIL,
    name: ROUTE_NAMES.AUTH_SIGNUP_EMAIL,
    component: () => import('@/domains/auth/pages/SignupPage.vue'),
    meta: { guestOnly: true },
  },
  {
    path: ROUTE_PATHS.AUTH_SSAFY,
    name: ROUTE_NAMES.AUTH_SSAFY,
    redirect: (to) => ({
      name:
        to.query.from === 'login' ? ROUTE_NAMES.AUTH_SSAFY_LOGIN : ROUTE_NAMES.AUTH_SSAFY_SIGNUP,
    }),
    meta: { guestOnly: true },
  },
  {
    path: ROUTE_PATHS.AUTH_SSAFY_LOGIN,
    name: ROUTE_NAMES.AUTH_SSAFY_LOGIN,
    component: () => import('@/domains/auth/pages/SsafyLoginPage.vue'),
    meta: { guestOnly: true },
  },
  {
    path: ROUTE_PATHS.AUTH_SSAFY_SIGNUP,
    name: ROUTE_NAMES.AUTH_SSAFY_SIGNUP,
    component: () => import('@/domains/auth/pages/SsafySignupPage.vue'),
    meta: { guestOnly: true },
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
    meta: { guestOnly: true },
  },
  {
    path: ROUTE_PATHS.ONBOARD_PROFILE,
    name: ROUTE_NAMES.ONBOARD_PROFILE,
    component: () => import('@/domains/onboard/pages/OnboardingBasicInfoView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: ROUTE_PATHS.ONBOARD_INTERESTS,
    name: ROUTE_NAMES.ONBOARD_INTERESTS,
    component: () => import('@/domains/onboard/pages/OnboardingInterestsView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: ROUTE_PATHS.ONBOARD_TRYON,
    name: ROUTE_NAMES.ONBOARD_TRYON,
    component: () => import('@/domains/onboard/pages/OnboardingTryOnView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: ROUTE_PATHS.ONBOARD_MEMBER_TYPE,
    name: ROUTE_NAMES.ONBOARD_MEMBER_TYPE,
    component: () => import('@/domains/onboard/pages/OnboardingMemberTypeView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: ROUTE_PATHS.BIZ_VERIFY,
    name: ROUTE_NAMES.BIZ_VERIFY,
    component: () => import('@/domains/biz/pages/BusinessVerificationPage.vue'),
  },
  {
    path: ROUTE_PATHS.BIZ_VERIFY_PENDING,
    name: ROUTE_NAMES.BIZ_VERIFY_PENDING,
    component: () => import('@/domains/biz/pages/BusinessVerificationPendingPage.vue'),
  },
  {
    path: ROUTE_PATHS.LIVE_LIST,
    name: ROUTE_NAMES.LIVE_LIST,
    component: () => import('@/domains/live/pages/LiveListView.vue'),
    meta: { title: '라이브 목록' },
  },
  {
    path: ROUTE_PATHS.PRODUCT_LIST,
    name: ROUTE_NAMES.PRODUCT_LIST,
    component: () => import('@/domains/product/pages/ProductListView.vue'),
    meta: { title: '상품 목록' },
  },
  {
    path: ROUTE_PATHS.PRODUCT_DETAIL,
    name: ROUTE_NAMES.PRODUCT_DETAIL,
    component: () => import('@/domains/product/pages/ProductDetailView.vue'),
    meta: { title: '상품 상세' },
  },
  {
    path: ROUTE_PATHS.PRODUCT_CREATE,
    name: ROUTE_NAMES.PRODUCT_CREATE,
    component: () => import('@/domains/product/pages/ProductRegistrationPage.vue'),
    meta: { requiresAuth: true, title: '상품 등록' },
  },
  {
    path: ROUTE_PATHS.LIVE_CREATE,
    name: ROUTE_NAMES.LIVE_CREATE,
    component: () => import('@/domains/live/pages/LiveCreatePage.vue'),
    meta: { requiresAuth: true, title: '라이브 시작' },
  },
  {
    path: ROUTE_PATHS.LIVE_BROADCAST,
    name: ROUTE_NAMES.LIVE_BROADCAST,
    component: () => import('@/domains/live/pages/LiveBroadcastPage.vue'),
    meta: { requiresAuth: true, title: '라이브 송출' },
  },
  {
    path: ROUTE_PATHS.LIVE_WATCH,
    name: ROUTE_NAMES.LIVE_WATCH,
    component: () => import('@/domains/live/pages/LiveWatchPage.vue'),
    meta: { title: '라이브 시청' },
  },
  {
    path: ROUTE_PATHS.NOTIFICATIONS,
    name: ROUTE_NAMES.NOTIFICATIONS,
    component: () => import('@/domains/notification/pages/NotificationCenterPage.vue'),
    meta: { requiresAuth: true, title: '알림센터' },
  },
  {
    path: ROUTE_PATHS.TRYON,
    name: ROUTE_NAMES.TRYON,
    component: () => import('@/domains/tryon/pages/TryOnPage.vue'),
    meta: { requiresAuth: true, title: 'AI 시착' },
  },
  {
    path: ROUTE_PATHS.MY,
    name: ROUTE_NAMES.MY,
    component: () => import('@/domains/my/pages/MyPage.vue'),
    meta: { requiresAuth: true, title: '마이페이지' },
  },
  {
    path: ROUTE_PATHS.MY_ORDER_DETAIL,
    name: ROUTE_NAMES.MY_ORDER_DETAIL,
    component: () => import('@/domains/my/pages/MyOrderDetailPage.vue'),
    meta: { requiresAuth: true, title: '구매 상세' },
  },
  {
    path: ROUTE_PATHS.MY_SALE_DETAIL,
    name: ROUTE_NAMES.MY_SALE_DETAIL,
    component: () => import('@/domains/my/pages/MySaleDetailPage.vue'),
    meta: { requiresAuth: true, title: '판매 상세' },
  },
  {
    path: ROUTE_PATHS.POINT_HISTORY,
    name: ROUTE_NAMES.POINT_HISTORY,
    component: () => import('@/domains/point/pages/PointHistoryPage.vue'),
    meta: { requiresAuth: true, title: '포인트 내역' },
  },
  {
    path: ROUTE_PATHS.POINT,
    name: ROUTE_NAMES.POINT,
    component: () => import('@/domains/point/pages/PointWalletPage.vue'),
    meta: { requiresAuth: true, title: '포인트' },
  },
]
