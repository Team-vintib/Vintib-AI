<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'

import logoImage from '@/assets/images/logo.png'
import { getSsafySsoStartUrl } from '@/domains/auth/api/authApi'
import { ROUTE_NAMES } from '@/shared/constants/routes'

const SSO_SOURCE_STORAGE_KEY = 'vintib_ssafy_sso_source'

const props = defineProps<{
  source: 'login' | 'signup'
  title: string
  description: string
  primaryLabel: string
  returnLabel: string
  returnTo: string
}>()

const route = useRoute()
const isStartingSso = ref(false)

const statusMessage = computed(() => {
  const error = getQueryValue(route.query.error)
  const cancelled = getQueryValue(route.query.cancelled)

  if (cancelled === 'true' || error === 'access_denied') {
    return '싸피어스 인증이 취소되었습니다. 다시 시도하거나 이전 화면으로 돌아가 주세요.'
  }

  if (error) {
    return '싸피어스 인증을 시작하지 못했습니다. 잠시 후 다시 시도해 주세요.'
  }

  return ''
})

const handleStartSso = () => {
  if (isStartingSso.value) {
    return
  }

  isStartingSso.value = true
  window.sessionStorage.setItem(SSO_SOURCE_STORAGE_KEY, props.source)
  window.location.assign(getSsafySsoStartUrl())
}

function getQueryValue(value: unknown) {
  if (Array.isArray(value)) {
    return value[0] ? String(value[0]) : ''
  }

  return value ? String(value) : ''
}
</script>

<template>
  <article
    class="ssafy-card rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-8 shadow-sm"
    aria-labelledby="ssafy-title"
  >
    <header class="ssafy-header">
      <RouterLink
        class="ssafy-header__logo-link"
        :to="{ name: ROUTE_NAMES.HOME }"
        aria-label="VinTib 홈"
      >
        <img class="ssafy-header__logo" :src="logoImage" alt="VinTib" />
      </RouterLink>
      <p class="ssafy-header__eyebrow">SSAFYERS SSO</p>
      <h1 id="ssafy-title" class="ssafy-header__title text-[var(--color-text-primary)]">
        {{ title }}
      </h1>
      <p class="ssafy-header__description text-[var(--color-text-secondary)]">
        {{ description }}
      </p>
    </header>

    <p v-if="statusMessage" class="ssafy-error" role="alert">
      {{ statusMessage }}
    </p>

    <section class="ssafy-actions" aria-label="싸피어스 인증 실행">
      <button
        class="ssafy-primary-button"
        type="button"
        :disabled="isStartingSso"
        @click="handleStartSso"
      >
        {{ isStartingSso ? '인증 연결 중' : primaryLabel }}
      </button>

      <RouterLink class="ssafy-secondary-button" :to="returnTo">
        {{ returnLabel }}
      </RouterLink>
    </section>
  </article>
</template>

<style scoped lang="scss">
.ssafy-card {
  width: 100%;
  padding: var(--space-8);
}

.ssafy-header {
  text-align: center;
}

.ssafy-header__logo-link {
  display: block;
  width: min(180px, 52vw);
  margin-right: auto;
  margin-bottom: var(--space-2);
  margin-left: auto;
  border-radius: var(--radius-control);
}

.ssafy-header__logo {
  display: block;
  width: 100%;
  height: auto;
  object-fit: contain;
}

.ssafy-header__eyebrow {
  margin-top: var(--space-4);
  color: var(--color-primary);
  font-size: 12px;
  font-weight: 700;
  line-height: 16px;
}

.ssafy-header__title {
  margin-top: var(--space-2);
  font-size: 32px;
  font-weight: 700;
  line-height: 44px;
}

.ssafy-header__description {
  margin-top: var(--space-3);
  font-size: 15px;
  line-height: 24px;
}

.ssafy-error {
  margin-top: var(--space-5);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-control);
  background: var(--color-error-soft);
  color: var(--color-error);
  font-size: 13px;
  font-weight: 600;
  line-height: 18px;
}

.ssafy-actions {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  margin-top: var(--space-8);
}

.ssafy-primary-button,
.ssafy-secondary-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: var(--button-height-major);
  padding: 0 var(--space-5);
  border-radius: var(--radius-control);
  font-size: 15px;
  font-weight: 600;
  line-height: 20px;
  transition:
    background-color 160ms ease,
    border-color 160ms ease,
    color 160ms ease,
    transform 160ms ease;
}

.ssafy-primary-button {
  border: 1px solid transparent;
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

.ssafy-primary-button:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.ssafy-secondary-button {
  border: 1px solid var(--color-border-strong);
  background: var(--color-surface);
  color: var(--color-text-primary);
}

.ssafy-secondary-button:hover {
  background: var(--color-surface-secondary);
}

.ssafy-primary-button:focus-visible,
.ssafy-header__logo-link:focus-visible,
.ssafy-secondary-button:focus-visible {
  outline: 3px solid var(--color-primary);
  outline-offset: 3px;
}

.ssafy-primary-button:active:not(:disabled),
.ssafy-secondary-button:active {
  transform: translateY(1px);
}

.ssafy-primary-button:disabled {
  background: var(--color-surface-secondary);
  color: var(--color-text-muted);
}

@media (max-width: 560px) {
  .ssafy-card {
    padding: var(--space-6);
  }

  .ssafy-header__title {
    font-size: 28px;
    line-height: 38px;
  }
}
</style>
