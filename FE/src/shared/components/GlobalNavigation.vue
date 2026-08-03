<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import logoImage from '@/assets/images/logo.png'
import { useAuthStore } from '@/domains/auth/stores/authStore'
import { getMyProfile } from '@/domains/my/api/myApi'
import NotificationPopup from '@/domains/notification/components/NotificationPopup.vue'
import { useNotificationStore } from '@/domains/notification/stores/notificationStore'
import { getPointBalance } from '@/domains/point/api/pointApi'
import { ROUTE_NAMES, ROUTE_PATHS, type RoutePath } from '@/shared/constants/routes'

import type { NotificationItem } from '@/domains/notification/types/notification.types'
import type { PointBalance } from '@/domains/point/types/point.types'

interface UserActionItem {
  label: string
  icon: string
  path: RoutePath
  query?: Record<string, string>
  badge: string | number
}

interface ProfileMenuItem {
  label: string
  path: RoutePath
  query?: Record<string, string>
}

const authStore = useAuthStore()
const notificationStore = useNotificationStore()
const route = useRoute()
const router = useRouter()

authStore.hydrateSession()

const isAuthenticated = computed(() => authStore.isAuthenticated)
const canShowNotificationAction = computed(() => isAuthenticated.value)
const profileNickname = ref('')
const displayName = computed(() => authStore.user?.nickname || profileNickname.value || '회원')
const profileInitial = computed(() => displayName.value.slice(0, 1).toUpperCase())
const pointBalance = ref<PointBalance | null>(null)
const isLoggingOut = ref(false)
const isNotificationPopupOpen = ref(false)
let pointBalanceRequestId = 0

const currentUserId = computed(() => authStore.user?.id ?? null)
const pointLabel = computed(() =>
  pointBalance.value ? `${pointBalance.value.available.toLocaleString('ko-KR')}P` : '0P',
)

const primaryMenuItems = [
  { label: '라이브', path: ROUTE_PATHS.LIVE_LIST, authRequired: false },
  { label: '상품', path: ROUTE_PATHS.PRODUCT_LIST, authRequired: false },
  { label: '상품 등록', path: ROUTE_PATHS.PRODUCT_CREATE, authRequired: true },
  { label: '라이브 시작', path: ROUTE_PATHS.LIVE_CREATE, authRequired: true },
] satisfies Array<{
  label: string
  path: RoutePath
  authRequired: boolean
}>

const userActionItems = computed<UserActionItem[]>(() => [
  { label: '찜', icon: 'heart', path: ROUTE_PATHS.MY, query: { section: 'wishlist' }, badge: '' },
])

const profileMenuItems = computed<ProfileMenuItem[]>(() => [
  { label: '마이페이지', path: ROUTE_PATHS.MY },
  { label: '시착 정보', path: ROUTE_PATHS.MY, query: { section: 'tryon' } },
  { label: '구매 내역', path: ROUTE_PATHS.MY, query: { section: 'orders' } },
  { label: '판매 내역', path: ROUTE_PATHS.MY, query: { section: 'sales' } },
  { label: '찜한 상품', path: ROUTE_PATHS.MY, query: { section: 'wishlist' } },
  { label: '포인트', path: ROUTE_PATHS.POINT },
])

const getRouteSection = () => {
  const section = route.query.section

  return typeof section === 'string' ? section : ''
}

const isSameQuery = (query?: Record<string, string>) => {
  if (!query) {
    return getRouteSection() === ''
  }

  return Object.entries(query).every(([key, value]) => route.query[key] === value)
}

const isActivePath = (path: RoutePath, query?: Record<string, string>) => {
  if (path === ROUTE_PATHS.HOME) {
    return route.path === ROUTE_PATHS.HOME
  }

  if (path === ROUTE_PATHS.LIVE_LIST && route.path === ROUTE_PATHS.LIVE_CREATE) {
    return false
  }

  if (path === ROUTE_PATHS.PRODUCT_LIST && route.path === ROUTE_PATHS.PRODUCT_CREATE) {
    return false
  }

  if (route.path !== path && !route.path.startsWith(`${path}/`)) {
    return false
  }

  if (path === ROUTE_PATHS.MY) {
    return isSameQuery(query)
  }

  return true
}

const goToPath = async (
  path: RoutePath,
  options: { authRequired?: boolean; query?: Record<string, string> } = {},
) => {
  if (options.authRequired && !isAuthenticated.value) {
    await router.push({
      name: ROUTE_NAMES.AUTH_LOGIN,
      query: { redirect: path },
    })
    return
  }

  await router.push({ path, query: options.query })
}

const handleLogout = async () => {
  if (isLoggingOut.value) {
    return
  }

  isLoggingOut.value = true

  try {
    await authStore.logoutSession()
    await router.replace({ name: ROUTE_NAMES.HOME })
  } finally {
    isLoggingOut.value = false
  }
}

const loadPointBalance = async (userId: number) => {
  const requestId = ++pointBalanceRequestId

  try {
    const balance = await getPointBalance(userId)

    if (requestId === pointBalanceRequestId) {
      pointBalance.value = balance
    }
  } catch {
    if (requestId === pointBalanceRequestId) {
      pointBalance.value = null
    }
  }
}

const handleNotificationButtonClick = async () => {
  isNotificationPopupOpen.value = !isNotificationPopupOpen.value

  if (isNotificationPopupOpen.value) {
    await notificationStore.loadNotifications({ page: 1, size: 20 })
  }
}

const handleOpenNotificationCenter = async () => {
  isNotificationPopupOpen.value = false
  await router.push({ name: ROUTE_NAMES.NOTIFICATIONS })
}

const handleSelectNotification = async (notification: NotificationItem) => {
  try {
    await notificationStore.markAsRead(notification.id)
    isNotificationPopupOpen.value = false

    if (notification.route) {
      await router.push(notification.route)
      return
    }

    await router.push({ name: ROUTE_NAMES.NOTIFICATIONS })
  } catch {
    await router.push({ name: ROUTE_NAMES.NOTIFICATIONS })
  }
}

watch(
  isAuthenticated,
  (authenticated) => {
    if (authenticated && notificationStore.loadState === 'idle') {
      void notificationStore.loadNotifications({ page: 1, size: 20 })
    }

    if (!authenticated) {
      isNotificationPopupOpen.value = false
    }
  },
  { immediate: true },
)

watch(
  currentUserId,
  (userId) => {
    pointBalanceRequestId += 1

    if (!userId) {
      pointBalance.value = null
      return
    }

    void loadPointBalance(userId)
  },
  { immediate: true },
)

watch(
  currentUserId,
  async (userId) => {
    profileNickname.value = authStore.user?.nickname?.trim() || ''

    if (!userId) {
      profileNickname.value = ''
      return
    }

    try {
      const profile = await getMyProfile(userId)
      const nickname = profile.nickname.trim()

      if (nickname) {
        profileNickname.value = nickname
        authStore.updateUser({ nickname })
      }
    } catch {
      profileNickname.value = authStore.user?.nickname?.trim() || ''
    }
  },
  { immediate: true },
)
</script>

<template>
  <header class="global-nav">
    <div class="global-nav__inner">
      <RouterLink class="global-nav__brand" :to="{ name: ROUTE_NAMES.HOME }" aria-label="VinTib 홈">
        <img class="global-nav__brand-logo" :src="logoImage" alt="VinTib" />
      </RouterLink>

      <nav class="global-nav__menu" aria-label="주요 메뉴">
        <template v-for="(item, index) in primaryMenuItems" :key="item.path">
          <span v-if="index === 2" class="global-nav__divider" aria-hidden="true"></span>
          <button
            class="global-nav__menu-item"
            :class="{ 'global-nav__menu-item--active': isActivePath(item.path) }"
            type="button"
            @click="goToPath(item.path, { authRequired: item.authRequired })"
          >
            {{ item.label }}
          </button>
        </template>

        <span v-if="isAuthenticated" class="global-nav__divider" aria-hidden="true"></span>

        <button
          v-if="isAuthenticated"
          class="global-nav__menu-item"
          :class="{ 'global-nav__menu-item--active': isActivePath(ROUTE_PATHS.TRYON) }"
          type="button"
          @click="goToPath(ROUTE_PATHS.TRYON, { authRequired: true })"
        >
          AI 시착
        </button>

        <button
          v-if="isAuthenticated"
          class="global-nav__points"
          :class="{ 'global-nav__points--active': isActivePath(ROUTE_PATHS.POINT) }"
          type="button"
          :aria-label="`보유 포인트 ${pointLabel}`"
          @click="goToPath(ROUTE_PATHS.POINT, { authRequired: true })"
        >
          {{ pointLabel }}
        </button>
      </nav>

      <div v-if="canShowNotificationAction" class="global-nav__actions" aria-label="사용자 메뉴">
        <template v-if="isAuthenticated">
          <button
            v-for="item in userActionItems"
            :key="item.label"
            class="global-nav__action global-nav__action--badge"
            :class="{ 'global-nav__action--active': isActivePath(item.path, item.query) }"
            type="button"
            @click="goToPath(item.path, { authRequired: true, query: item.query })"
          >
            <span class="global-nav__icon" aria-hidden="true">
              <svg
                v-if="item.icon === 'heart'"
                class="global-nav__icon-svg"
                viewBox="0 0 24 24"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  d="M20.3 5.7a5.1 5.1 0 0 0-7.2 0L12 6.8l-1.1-1.1a5.1 5.1 0 0 0-7.2 7.2L12 21l8.3-8.1a5.1 5.1 0 0 0 0-7.2Z"
                  stroke="currentColor"
                  stroke-width="1.8"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                />
              </svg>
              <template v-else>{{ item.icon }}</template>
            </span>
            {{ item.label }}
            <span v-if="Number(item.badge) > 0" class="global-nav__badge">{{ item.badge }}</span>
          </button>
        </template>

        <div class="global-nav__notification-menu">
          <button
            class="global-nav__action global-nav__action--badge"
            :class="{ 'global-nav__action--active': isActivePath(ROUTE_PATHS.NOTIFICATIONS) }"
            type="button"
            aria-haspopup="dialog"
            :aria-expanded="isNotificationPopupOpen"
            @click="handleNotificationButtonClick"
          >
            <span class="global-nav__icon" aria-hidden="true">
              <svg
                class="global-nav__icon-svg"
                viewBox="0 0 24 24"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  d="M18 9.8a6 6 0 1 0-12 0c0 5.7-2.2 6.7-2.2 6.7h16.4S18 15.5 18 9.8Z"
                  stroke="currentColor"
                  stroke-width="1.8"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                />
                <path
                  d="M14.1 19a2.3 2.3 0 0 1-4.2 0"
                  stroke="currentColor"
                  stroke-width="1.8"
                  stroke-linecap="round"
                />
              </svg>
            </span>
            알림
            <span v-if="notificationStore.unreadCount > 0" class="global-nav__badge">
              {{ notificationStore.unreadCount }}
            </span>
          </button>

          <NotificationPopup
            :is-open="isNotificationPopupOpen"
            @close="isNotificationPopupOpen = false"
            @open-center="handleOpenNotificationCenter"
            @select="handleSelectNotification"
          />
        </div>

        <div v-if="isAuthenticated" class="global-nav__profile-menu">
          <button
            class="global-nav__profile"
            :class="{ 'global-nav__profile--active': isActivePath(ROUTE_PATHS.MY) }"
            type="button"
            aria-haspopup="menu"
            :aria-expanded="isLoggingOut ? 'true' : undefined"
          >
            <span class="global-nav__avatar" aria-hidden="true">{{ profileInitial }}</span>
            <span class="global-nav__profile-name">{{ displayName }}</span>
            <span class="global-nav__chevron" aria-hidden="true">
              <svg
                class="global-nav__chevron-svg"
                viewBox="0 0 24 24"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  d="m6 9 6 6 6-6"
                  stroke="currentColor"
                  stroke-width="1.8"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                />
              </svg>
            </span>
          </button>

          <div class="global-nav__profile-panel" role="menu">
            <button
              v-for="item in profileMenuItems"
              :key="`${item.path}-${item.query?.section ?? 'root'}`"
              class="global-nav__profile-menu-item"
              type="button"
              role="menuitem"
              @click="goToPath(item.path, { authRequired: true, query: item.query })"
            >
              {{ item.label }}
            </button>

            <button
              class="global-nav__logout"
              type="button"
              role="menuitem"
              :disabled="isLoggingOut"
              @click="handleLogout"
            >
              로그아웃
            </button>
          </div>
        </div>
      </div>

      <div v-else class="global-nav__guest-actions">
        <RouterLink class="global-nav__guest-link" :to="{ name: ROUTE_NAMES.AUTH_LOGIN }">
          로그인
        </RouterLink>
        <RouterLink class="global-nav__guest-primary" :to="{ name: ROUTE_NAMES.AUTH_SIGNUP }">
          회원가입
        </RouterLink>
      </div>
    </div>
  </header>
</template>

<style scoped lang="scss">
.global-nav {
  position: sticky;
  top: 0;
  z-index: 50;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-surface);
}

.global-nav__inner {
  display: flex;
  align-items: center;
  width: 100%;
  max-width: var(--layout-content-max-width);
  height: 64px;
  margin: 0 auto;
  padding: 0 var(--space-12);
  gap: 0;
}

.global-nav__brand {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  margin-right: var(--space-6);
  transition: opacity 160ms ease;
}

.global-nav__brand:hover {
  opacity: 0.8;
}

.global-nav__brand-logo {
  width: 116px;
  height: 40px;
  object-fit: contain;
}

.global-nav__menu {
  display: flex;
  align-items: center;
  align-self: stretch;
  min-width: 0;
}

.global-nav__menu-item,
.global-nav__points {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  align-self: stretch;
  gap: 6px;
  padding: 0 var(--space-3);
  border: 0;
  border-bottom: 2px solid transparent;
  background: transparent;
  color: var(--color-text-secondary);
  font-size: 14px;
  font-weight: 600;
  line-height: 20px;
  white-space: nowrap;
  transition:
    border-color 160ms ease,
    color 160ms ease,
    opacity 160ms ease;
}

.global-nav__menu-item:hover,
.global-nav__menu-item--active {
  border-bottom-color: var(--color-primary);
  color: var(--color-primary);
}

.global-nav__points {
  color: var(--color-primary);
  font-variant-numeric: tabular-nums;
}

.global-nav__points:hover,
.global-nav__points--active {
  opacity: 0.8;
}

.global-nav__divider {
  flex: 0 0 auto;
  width: 1px;
  height: 16px;
  margin: 0 var(--space-2);
  background: var(--color-border);
}

.global-nav__actions,
.global-nav__guest-actions {
  display: flex;
  align-items: center;
  flex: 0 0 auto;
  gap: 2px;
  margin-left: auto;
}

.global-nav__action,
.global-nav__profile,
.global-nav__guest-link,
.global-nav__guest-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 36px;
  border: 0;
  border-radius: var(--radius-control);
  background: transparent;
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: 500;
  line-height: 20px;
  white-space: nowrap;
  transition:
    background-color 160ms ease,
    color 160ms ease;
}

.global-nav__action {
  position: relative;
  gap: 6px;
  padding: 0 10px;
}

.global-nav__action:hover,
.global-nav__action--active,
.global-nav__profile:hover,
.global-nav__profile--active,
.global-nav__guest-link:hover {
  background: var(--color-surface-secondary);
  color: var(--color-text-primary);
}

.global-nav__badge {
  position: absolute;
  top: 2px;
  right: 2px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 16px;
  height: 16px;
  padding: 0 2px;
  border-radius: var(--radius-chip);
  background: var(--color-live);
  color: var(--color-text-inverse);
  font-size: 9px;
  font-weight: 700;
  line-height: 1;
}

.global-nav__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  color: currentColor;
  font-size: 15px;
  line-height: 1;
}

.global-nav__icon-svg {
  width: 18px;
  height: 18px;
}

.global-nav__profile {
  gap: var(--space-2);
  margin-left: var(--space-1);
  padding: 0 10px;
  color: var(--color-text-primary);
  font-size: 14px;
  font-weight: 600;
}

.global-nav__profile-menu {
  position: relative;
  display: inline-flex;
  align-items: center;
}

.global-nav__notification-menu {
  position: relative;
  display: inline-flex;
  align-items: center;
}

.global-nav__profile-menu::after {
  position: absolute;
  top: 100%;
  right: 0;
  width: 100%;
  min-width: 180px;
  height: 10px;
  content: '';
}

.global-nav__profile-panel {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  display: grid;
  width: 184px;
  padding: var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  box-shadow: 0 18px 48px rgb(23 24 21 / 14%);
  opacity: 0;
  pointer-events: none;
  transform: translateY(-4px);
  transition:
    opacity 140ms ease,
    transform 140ms ease;
}

.global-nav__profile-menu:hover .global-nav__profile-panel,
.global-nav__profile-menu:focus-within .global-nav__profile-panel {
  opacity: 1;
  pointer-events: auto;
  transform: translateY(0);
}

.global-nav__profile-menu:hover .global-nav__chevron-svg,
.global-nav__profile-menu:focus-within .global-nav__chevron-svg {
  transform: rotate(180deg);
}

.global-nav__profile-menu-item,
.global-nav__logout {
  display: flex;
  align-items: center;
  width: 100%;
  min-height: 36px;
  padding: 0 var(--space-3);
  border: 0;
  border-radius: var(--radius-control);
  background: transparent;
  color: var(--color-text-primary);
  font-size: 13px;
  font-weight: 600;
  line-height: 20px;
  text-align: left;
  transition:
    background-color 140ms ease,
    color 140ms ease;
}

.global-nav__profile-menu-item:hover,
.global-nav__profile-menu-item:focus-visible {
  background: var(--color-surface-secondary);
  color: var(--color-primary);
}

.global-nav__logout {
  margin-top: var(--space-2);
  border-top: 1px solid var(--color-border);
  border-radius: 0 0 var(--radius-control) var(--radius-control);
  color: var(--color-error);
}

.global-nav__logout:hover,
.global-nav__logout:focus-visible {
  background: var(--color-error-soft);
}

.global-nav__logout:disabled {
  color: var(--color-text-muted);
  cursor: wait;
}

.global-nav__avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: var(--radius-chip);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-size: 11px;
  font-weight: 700;
}

.global-nav__chevron {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  color: var(--color-text-muted);
}

.global-nav__chevron-svg {
  width: 16px;
  height: 16px;
  transition: transform 140ms ease;
}

.global-nav__guest-link {
  padding: 0 var(--space-4);
  color: var(--color-text-primary);
  font-weight: 600;
}

.global-nav__guest-primary {
  padding: 0 var(--space-5);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-weight: 700;
}

.global-nav__guest-primary:hover {
  background: var(--color-primary-hover);
}

.global-nav__brand:focus-visible,
.global-nav__menu-item:focus-visible,
.global-nav__points:focus-visible,
.global-nav__action:focus-visible,
.global-nav__profile:focus-visible,
.global-nav__guest-link:focus-visible,
.global-nav__guest-primary:focus-visible {
  outline: 3px solid var(--color-primary);
  outline-offset: 3px;
}

@media (max-width: 1120px) {
  .global-nav__inner {
    padding: 0 var(--space-8);
  }

  .global-nav__action span:not(.global-nav__icon, .global-nav__badge),
  .global-nav__profile-name {
    display: none;
  }
}

@media (max-width: 860px) {
  .global-nav__inner {
    padding: 0 var(--space-5);
  }

  .global-nav__brand {
    margin-right: var(--space-4);
  }

  .global-nav__menu-item:nth-of-type(n + 3),
  .global-nav__divider,
  .global-nav__points {
    display: none;
  }
}

@media (max-width: 640px) {
  .global-nav__inner {
    height: 60px;
  }

  .global-nav__brand-logo {
    width: 96px;
    height: 34px;
  }

  .global-nav__menu {
    display: none;
  }

  .global-nav__guest-link {
    display: none;
  }
}
</style>
