<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'

import logoImage from '@/assets/images/logo.png'
import { getSsafySsoStartUrl } from '@/domains/auth/api/authApi'
import { ROUTE_PATHS } from '@/shared/constants/routes'
import AuthLayout from '@/shared/layouts/AuthLayout.vue'

const route = useRoute()

const isStartingSso = ref(false)
const isHelpOpen = ref(false)
const requestError = ref('')

const queryErrorMessage = computed(() => {
  const error = getQueryValue(route.query.error)
  const cancelled = getQueryValue(route.query.cancelled)

  if (cancelled === 'true' || error === 'access_denied') {
    return '싸피어스 인증이 취소되었습니다. 다시 시도하거나 이메일 로그인으로 돌아가 주세요.'
  }

  if (error) {
    return '싸피어스 인증을 시작하지 못했습니다. 잠시 후 다시 시도해 주세요.'
  }

  return ''
})

const statusMessage = computed(() => requestError.value || queryErrorMessage.value)

const securityItems = ['SSL 보안 연결', '2단계 인증 지원']

const handleStartSso = () => {
  if (isStartingSso.value) {
    return
  }

  isStartingSso.value = true
  requestError.value = ''
  window.location.assign(getSsafySsoStartUrl())
}

const toggleHelp = () => {
  isHelpOpen.value = !isHelpOpen.value
}

function getQueryValue(value: unknown) {
  if (Array.isArray(value)) {
    return value[0] ? String(value[0]) : ''
  }

  return value ? String(value) : ''
}
</script>

<template>
  <AuthLayout>
    <article
      class="ssafy-card rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-8 shadow-sm"
      aria-labelledby="ssafy-title"
    >
      <header class="ssafy-header">
        <img class="ssafy-header__logo" :src="logoImage" alt="VinTib" />
        <p class="ssafy-header__eyebrow">SSAFYERS SSO</p>
        <h1 id="ssafy-title" class="ssafy-header__title text-[var(--color-text-primary)]">
          싸피어스 인증
        </h1>
        <p class="ssafy-header__description text-[var(--color-text-secondary)]">
          SSAFYERS 통합 계정을 사용하여 VinTib 서비스에 안전하게 접근할 수 있습니다.
        </p>
      </header>

      <section class="ssafy-security" aria-label="싸피어스 인증 보안 안내">
        <div v-for="item in securityItems" :key="item" class="ssafy-security__item">
          <span class="ssafy-security__mark" aria-hidden="true"></span>
          <span>{{ item }}</span>
        </div>
      </section>

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
          {{ isStartingSso ? '인증 연결 중' : '싸피어스로 로그인' }}
        </button>

        <a class="ssafy-secondary-button" :href="ROUTE_PATHS.AUTH_LOGIN">
          이메일 로그인으로 돌아가기
        </a>

        <button
          class="ssafy-help-button"
          type="button"
          :aria-expanded="isHelpOpen"
          aria-controls="ssafy-help"
          @click="toggleHelp"
        >
          인증 도움말
        </button>
      </section>

      <p v-if="isHelpOpen" id="ssafy-help" class="ssafy-help-text">
        싸피어스 계정 인증 창에서 인증을 완료하면 VinTib 회원가입 절차로 돌아옵니다.
      </p>
    </article>
  </AuthLayout>
</template>

<style scoped lang="scss">
.ssafy-card {
  width: 100%;
  padding: var(--space-8);
}

.ssafy-header {
  text-align: center;
}

.ssafy-header__logo {
  width: min(180px, 52vw);
  height: auto;
  margin-right: auto;
  margin-bottom: var(--space-2);
  margin-left: auto;
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

.ssafy-security {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-3);
  margin-top: var(--space-8);
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-primary-soft);
}

.ssafy-security__item {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  color: var(--color-primary);
  font-size: 13px;
  font-weight: 600;
  line-height: 18px;
}

.ssafy-security__mark {
  width: 8px;
  height: 8px;
  border-radius: var(--radius-chip);
  background: var(--color-primary);
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
.ssafy-secondary-button,
.ssafy-help-button {
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

.ssafy-help-button {
  height: var(--button-height-standard);
  border: 0;
  background: transparent;
  color: var(--color-text-secondary);
}

.ssafy-help-button:hover {
  color: var(--color-primary);
}

.ssafy-help-text {
  margin-top: var(--space-4);
  color: var(--color-text-muted);
  font-size: 13px;
  line-height: 18px;
  text-align: center;
}

.ssafy-primary-button:focus-visible,
.ssafy-secondary-button:focus-visible,
.ssafy-help-button:focus-visible {
  outline: 3px solid var(--color-primary);
  outline-offset: 3px;
}

.ssafy-primary-button:active:not(:disabled),
.ssafy-secondary-button:active,
.ssafy-help-button:active {
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

  .ssafy-security {
    grid-template-columns: 1fr;
  }
}
</style>
