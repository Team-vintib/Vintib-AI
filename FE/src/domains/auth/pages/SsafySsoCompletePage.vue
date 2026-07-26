<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import logoImage from '@/assets/images/logo.png'
import type { AuthNextStep } from '@/domains/auth/types/auth.types'
import { ROUTE_NAMES, ROUTE_PATHS } from '@/shared/constants/routes'
import AuthLayout from '@/shared/layouts/AuthLayout.vue'

const SSO_RESULT_STORAGE_KEY = 'vintib_ssafy_sso_result'

interface SsafySsoResult {
  email: string
  linked?: boolean
  name: string
  nextStep: AuthNextStep
}

const router = useRouter()

const ssoResult = ref<SsafySsoResult | null>(null)
const loadError = ref('')

const displayName = computed(() => ssoResult.value?.name || '이름 정보 없음')
const displayEmail = computed(() => ssoResult.value?.email || '이메일 정보 없음')
const isResultMissing = computed(() => !ssoResult.value || Boolean(loadError.value))

onMounted(() => {
  ssoResult.value = readSsoResult()

  if (!ssoResult.value) {
    loadError.value = '싸피어스 인증 정보가 만료되었거나 확인되지 않습니다.'
  }
})

const handleContinue = async () => {
  if (!ssoResult.value) {
    await router.push({ name: ROUTE_NAMES.AUTH_SSAFY })
    return
  }

  if (ssoResult.value.nextStep === 'HOME') {
    window.sessionStorage.removeItem(SSO_RESULT_STORAGE_KEY)
    await router.push(ROUTE_PATHS.HOME)
    return
  }

  if (ssoResult.value.nextStep === 'LINK_ACCOUNT') {
    window.sessionStorage.removeItem(SSO_RESULT_STORAGE_KEY)
    await router.push(ROUTE_PATHS.AUTH_LINK_ACCOUNT)
    return
  }

  window.sessionStorage.removeItem(SSO_RESULT_STORAGE_KEY)
  await router.push({ name: ROUTE_NAMES.ONBOARD_PROFILE })
}

const handleRetry = async () => {
  window.sessionStorage.removeItem(SSO_RESULT_STORAGE_KEY)
  await router.push({ name: ROUTE_NAMES.AUTH_SSAFY })
}

function readSsoResult() {
  const rawResult = window.sessionStorage.getItem(SSO_RESULT_STORAGE_KEY)

  if (!rawResult) {
    return null
  }

  try {
    const parsedResult = JSON.parse(rawResult) as Partial<SsafySsoResult>

    return {
      email: parsedResult.email || '',
      linked: parsedResult.linked,
      name: parsedResult.name || '',
      nextStep: parsedResult.nextStep || 'ONBOARD_PROFILE',
    }
  } catch {
    return null
  }
}
</script>

<template>
  <AuthLayout>
    <article
      class="complete-card rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-8 shadow-sm"
      aria-labelledby="complete-title"
    >
      <header class="complete-header">
        <img class="complete-header__logo" :src="logoImage" alt="VinTib" />
        <div class="complete-header__badge" aria-hidden="true"></div>
        <h1 id="complete-title" class="complete-header__title">
          SSAFYERS 인증에 성공했습니다
        </h1>
        <p class="complete-header__description">
          아래의 정보로 회원가입을 완료합니다.
        </p>
      </header>

      <p v-if="loadError" class="complete-error" role="alert">
        {{ loadError }}
      </p>

      <section v-else class="complete-profile" aria-label="싸피어스 인증 정보">
        <div class="complete-profile__row">
          <span class="complete-profile__label">이름</span>
          <strong class="complete-profile__value">{{ displayName }}</strong>
        </div>
        <div class="complete-profile__row">
          <span class="complete-profile__label">이메일</span>
          <strong class="complete-profile__value">{{ displayEmail }}</strong>
        </div>
      </section>

      <p class="complete-help">
        정보가 올바르지 않나요?
      </p>

      <section class="complete-actions" aria-label="싸피어스 인증 완료 실행">
        <button
          class="complete-primary-button"
          type="button"
          :disabled="isResultMissing"
          @click="handleContinue"
        >
          계속하기
        </button>
        <button class="complete-secondary-button" type="button" @click="handleRetry">
          다시 인증하기
        </button>
      </section>
    </article>
  </AuthLayout>
</template>

<style scoped lang="scss">
.complete-card {
  width: 100%;
  padding: var(--space-8);
}

.complete-header {
  text-align: center;
}

.complete-header__logo {
  width: min(180px, 52vw);
  height: auto;
  margin-right: auto;
  margin-bottom: var(--space-4);
  margin-left: auto;
  object-fit: contain;
}

.complete-header__badge {
  width: 48px;
  height: 48px;
  margin: 0 auto var(--space-5);
  border: 12px solid var(--color-primary-soft);
  border-radius: var(--radius-chip);
  background: var(--color-primary);
}

.complete-header__title {
  color: var(--color-text-primary);
  font-size: 28px;
  font-weight: 700;
  line-height: 38px;
}

.complete-header__description {
  margin-top: var(--space-3);
  color: var(--color-text-secondary);
  font-size: 15px;
  line-height: 24px;
}

.complete-error {
  margin-top: var(--space-8);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-control);
  background: var(--color-error-soft);
  color: var(--color-error);
  font-size: 13px;
  font-weight: 600;
  line-height: 18px;
}

.complete-profile {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  margin-top: var(--space-8);
}

.complete-profile__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  min-height: 52px;
  padding: 0 var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface-secondary);
}

.complete-profile__label {
  flex: 0 0 auto;
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: 600;
  line-height: 18px;
}

.complete-profile__value {
  min-width: 0;
  overflow-wrap: anywhere;
  color: var(--color-text-primary);
  font-size: 15px;
  font-weight: 600;
  line-height: 20px;
  text-align: right;
}

.complete-help {
  margin-top: var(--space-5);
  color: var(--color-text-muted);
  font-size: 13px;
  line-height: 18px;
  text-align: center;
}

.complete-actions {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  margin-top: var(--space-8);
}

.complete-primary-button,
.complete-secondary-button {
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
}

.complete-primary-button {
  border: 1px solid transparent;
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

.complete-primary-button:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.complete-secondary-button {
  border: 1px solid var(--color-border-strong);
  background: var(--color-surface);
  color: var(--color-text-primary);
}

.complete-secondary-button:hover {
  background: var(--color-surface-secondary);
}

.complete-primary-button:focus-visible,
.complete-secondary-button:focus-visible {
  outline: 3px solid var(--color-primary);
  outline-offset: 3px;
}

.complete-primary-button:disabled {
  background: var(--color-surface-secondary);
  color: var(--color-text-muted);
}

@media (max-width: 560px) {
  .complete-card {
    padding: var(--space-6);
  }

  .complete-profile__row {
    align-items: flex-start;
    flex-direction: column;
    justify-content: center;
    padding: var(--space-3) var(--space-4);
  }

  .complete-profile__value {
    text-align: left;
  }
}
</style>
