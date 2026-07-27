<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'

import logoImage from '@/assets/images/logo.png'
import { useAuthStore } from '@/domains/auth/stores/authStore'
import { ROUTE_NAMES, ROUTE_PATHS } from '@/shared/constants/routes'

const authStore = useAuthStore()
const router = useRouter()

authStore.hydrateSession()

const isAuthenticated = computed(() => authStore.isAuthenticated)
const displayName = computed(() => authStore.user?.name || '회원')
const profileInitial = computed(() => displayName.value.slice(0, 1).toUpperCase())

const goToPublicPath = async (path: string) => {
  await router.push(path)
}

const goToProtectedPath = async (path: string) => {
  if (!isAuthenticated.value) {
    await router.push({
      name: ROUTE_NAMES.AUTH_LOGIN,
      query: { redirect: path },
    })
    return
  }

  await router.push(path)
}
</script>

<template>
  <header class="global-nav">
    <div class="global-nav__inner">
      <RouterLink class="global-nav__brand" :to="{ name: ROUTE_NAMES.HOME }" aria-label="VinTib 홈">
        <img class="global-nav__brand-logo" :src="logoImage" alt="VinTib" />
      </RouterLink>

      <nav class="global-nav__menu" aria-label="주요 메뉴">
        <button class="global-nav__menu-item" type="button" @click="goToPublicPath('/lives')">
          라이브
        </button>
        <button class="global-nav__menu-item" type="button" @click="goToPublicPath(ROUTE_PATHS.PRODUCT_LIST)">
          상품
        </button>

        <span class="global-nav__divider" aria-hidden="true"></span>

        <button class="global-nav__menu-item" type="button" @click="goToProtectedPath(ROUTE_PATHS.PRODUCT_CREATE)">
          상품 등록
        </button>
        <button class="global-nav__menu-item" type="button" @click="goToProtectedPath(ROUTE_PATHS.LIVE_CREATE)">
          라이브 시작
        </button>

        <span v-if="isAuthenticated" class="global-nav__divider" aria-hidden="true"></span>

        <button
          v-if="isAuthenticated"
          class="global-nav__points"
          type="button"
          aria-label="사용 가능 포인트 125,000P"
          @click="goToProtectedPath(ROUTE_PATHS.POINT)"
        >
          <span class="global-nav__icon" aria-hidden="true">₩</span>
          125,000P
        </button>
      </nav>

      <div v-if="isAuthenticated" class="global-nav__actions" aria-label="사용자 메뉴">
        <button class="global-nav__action" type="button" @click="goToProtectedPath('/my/wishlist')">
          <span class="global-nav__icon" aria-hidden="true">♡</span>
          찜
        </button>

        <button class="global-nav__action global-nav__action--badge" type="button" @click="goToProtectedPath('/orders')">
          <span class="global-nav__icon" aria-hidden="true">▢</span>
          장바구니
          <span class="global-nav__badge">2</span>
        </button>

        <button
          class="global-nav__action global-nav__action--badge"
          type="button"
          @click="goToProtectedPath(ROUTE_PATHS.NOTIFICATIONS)"
        >
          <span class="global-nav__icon" aria-hidden="true">◦</span>
          알림
          <span class="global-nav__badge">3</span>
        </button>

        <button class="global-nav__profile" type="button" @click="goToProtectedPath(ROUTE_PATHS.MY)">
          <span class="global-nav__avatar" aria-hidden="true">{{ profileInitial }}</span>
          <span class="global-nav__profile-name">{{ displayName }}</span>
          <span class="global-nav__chevron" aria-hidden="true">⌄</span>
        </button>
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
    color 160ms ease,
    opacity 160ms ease;
}

.global-nav__menu-item:hover {
  color: var(--color-text-primary);
}

.global-nav__points {
  color: var(--color-primary);
  font-variant-numeric: tabular-nums;
}

.global-nav__points:hover {
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
.global-nav__profile:hover,
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

.global-nav__profile {
  gap: var(--space-2);
  margin-left: var(--space-1);
  padding: 0 10px;
  color: var(--color-text-primary);
  font-size: 14px;
  font-weight: 600;
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
  color: var(--color-text-muted);
  font-size: 14px;
  line-height: 1;
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
