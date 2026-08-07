<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import logoImage from '@/assets/images/logo-white.png'
import { confirmGoogleLink } from '@/domains/auth/api/authApi'
import { useAuthStore } from '@/domains/auth/stores/authStore'
import { startGoogleOAuth } from '@/domains/auth/utils/googleOAuth'
import {
  clearLinkAccountSession,
  readLinkAccountSession,
} from '@/domains/auth/utils/linkAccountSession'
import type { LinkAccountSessionPayload } from '@/domains/auth/types/auth.types'
import { normalizeApiError } from '@/shared/api/http'
import { ROUTE_NAMES, ROUTE_PATHS } from '@/shared/constants/routes'
import AuthLayout from '@/shared/layouts/AuthLayout.vue'

const router = useRouter()
const authStore = useAuthStore()

const accountInfo = ref<LinkAccountSessionPayload | null>(null)
const isAgreementChecked = ref(false)
const isSubmitting = ref(false)
const consentError = ref('')
const pageError = ref('')
const submitError = ref('')

const displayEmail = computed(() => accountInfo.value?.email || '가입된 이메일 계정')
const canContinue = computed(() =>
  Boolean(accountInfo.value?.linkToken && isAgreementChecked.value && !isSubmitting.value),
)
const hasValidAccountInfo = computed(() => Boolean(accountInfo.value?.linkToken))

onMounted(() => {
  const payload = readLinkAccountSession()

  if (!payload?.linkToken) {
    clearLinkAccountSession()
    pageError.value = '계정 연결 정보가 없거나 인증 시간이 만료되었습니다.'
    return
  }

  accountInfo.value = payload
})

const handleRetrySso = () => {
  clearLinkAccountSession()
  startGoogleOAuth('signup')
}

const handleMoveToLogin = async () => {
  clearLinkAccountSession()
  await router.push({ name: ROUTE_NAMES.AUTH_LOGIN })
}

const handleMoveToSignup = async () => {
  clearLinkAccountSession()
  await router.push({ name: ROUTE_NAMES.AUTH_SIGNUP })
}

const handleAgreementChange = (event: Event) => {
  isAgreementChecked.value = (event.target as HTMLInputElement).checked
  consentError.value = ''
  submitError.value = ''
}

const handleContinue = async () => {
  if (isSubmitting.value) {
    return
  }

  submitError.value = ''

  if (!isAgreementChecked.value) {
    consentError.value = '계정 연결에 동의해 주세요.'
    return
  }

  if (!accountInfo.value?.linkToken) {
    clearLinkAccountSession()
    pageError.value = '계정 연결 정보가 없거나 인증 시간이 만료되었습니다.'
    return
  }

  isSubmitting.value = true

  try {
    const response = await confirmGoogleLink({
      linkToken: accountInfo.value.linkToken,
      confirm: true,
    })

    if (!response.success) {
      applyLinkAccountError(response.error?.code, response.error?.message)
      return
    }

    if (!response.data?.accessToken) {
      submitError.value = '계정 연결 결과를 확인하지 못했습니다. 잠시 후 다시 시도해 주세요.'
      return
    }

    authStore.setSession({
      accessToken: response.data.accessToken,
      refreshToken: response.data.refreshToken,
      user: { onboardingCompleted: response.data.onboardingCompleted ?? undefined },
    })
    clearLinkAccountSession()
    await moveAfterLink(response.data.onboardingCompleted)
  } catch (error: unknown) {
    const apiError = normalizeApiError(error)

    applyLinkAccountError(apiError.code, apiError.message)
  } finally {
    isSubmitting.value = false
  }
}

const applyLinkAccountError = (code?: string, message?: string) => {
  if (code === 'U016') {
    submitError.value = message || '계정 연결 인증 시간이 만료되었습니다. 다시 인증해 주세요.'
    clearLinkAccountSession()
    accountInfo.value = null
    pageError.value = submitError.value
    return
  }

  if (code === 'C001') {
    submitError.value = message || '계정 연결 정보를 다시 확인해 주세요.'
    return
  }

  if (code === 'NETWORK_ERROR' || code === 'REQUEST_TIMEOUT') {
    submitError.value = message || '네트워크 연결을 확인한 뒤 다시 시도해 주세요.'
    return
  }

  submitError.value = message || '계정 연결을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.'
}

const moveAfterLink = async (onboardingCompleted: boolean | null) => {
  if (onboardingCompleted === false) {
    await router.replace({ name: ROUTE_NAMES.ONBOARD_PROFILE })
    return
  }

  await router.replace(ROUTE_PATHS.HOME)
}
</script>

<template>
  <AuthLayout>
    <article
      class="link-card rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-8 shadow-sm"
      aria-labelledby="link-title"
    >
      <header class="link-header">
        <RouterLink
          class="link-header__logo-link"
          :to="{ name: ROUTE_NAMES.HOME }"
          aria-label="VinTib 홈"
        >
          <img class="link-header__logo" :src="logoImage" alt="VinTib" />
        </RouterLink>
        <p class="link-header__eyebrow">GOOGLE SIGN-IN</p>
        <h1 id="link-title" class="link-header__title">기존 계정 연결 안내</h1>
        <p class="link-header__description">
          Google 인증 이메일과 동일한 VinTib 계정이 확인되었습니다.
        </p>
      </header>

      <template v-if="hasValidAccountInfo">
        <section class="link-account" aria-label="가입 계정 정보">
          <span class="link-account__label">가입 계정</span>
          <strong class="link-account__value">{{ displayEmail }}</strong>
        </section>

        <section class="link-guide" aria-label="계정 연결 안내">
          <p class="link-guide__text">
            동의하면 기존 VinTib 계정에 Google 로그인 정보가 연결됩니다.
          </p>
          <p class="link-guide__text">
            연결 후에는 같은 계정으로 로그인하고 서비스를 이어서 이용할 수 있습니다.
          </p>
        </section>

        <section class="link-consent" aria-label="계정 연결 동의">
          <label class="link-consent__label" for="link-account-agreement">
            <input
              id="link-account-agreement"
              class="link-consent__checkbox"
              type="checkbox"
              :checked="isAgreementChecked"
              :disabled="isSubmitting"
              aria-describedby="link-account-agreement-message"
              @change="handleAgreementChange"
            />
            <span>기존 VinTib 계정에 Google 로그인 정보를 연결하는 데 동의합니다.</span>
          </label>
          <p
            v-if="consentError"
            id="link-account-agreement-message"
            class="link-consent__error"
            role="alert"
          >
            {{ consentError }}
          </p>
        </section>

        <p v-if="submitError" class="link-submit-error" role="alert">
          {{ submitError }}
        </p>

        <section class="link-actions" aria-label="계정 연결 실행">
          <button
            class="link-primary"
            type="button"
            :disabled="!canContinue"
            @click="handleContinue"
          >
            {{ isSubmitting ? '연결 중' : '연결하고 계속하기' }}
          </button>
          <button
            class="link-secondary"
            type="button"
            :disabled="isSubmitting"
            @click="handleMoveToLogin"
          >
            로그인으로 이동
          </button>
          <button
            class="link-text-button"
            type="button"
            :disabled="isSubmitting"
            @click="handleRetrySso"
          >
            다시 인증하기
          </button>
          <button
            class="link-text-button"
            type="button"
            :disabled="isSubmitting"
            @click="handleMoveToSignup"
          >
            회원가입 선택으로 돌아가기
          </button>
        </section>
      </template>

      <template v-else>
        <p class="link-error" role="alert">
          {{ pageError || '계정 연결 정보를 확인하지 못했습니다.' }}
        </p>

        <section class="link-actions" aria-label="계정 연결 재시도">
          <button class="link-primary" type="button" @click="handleRetrySso">
            다시 인증하기
          </button>
          <button class="link-secondary" type="button" @click="handleMoveToSignup">
            회원가입 선택으로 돌아가기
          </button>
        </section>
      </template>
    </article>
  </AuthLayout>
</template>

<style scoped lang="scss">
.link-card {
  width: 100%;
  padding: var(--space-8);
}

.link-header {
  text-align: center;
}

.link-header__logo-link {
  display: block;
  width: min(180px, 52vw);
  margin-right: auto;
  margin-bottom: var(--space-2);
  margin-left: auto;
  border-radius: var(--radius-control);
}

.link-header__logo {
  display: block;
  width: 100%;
  height: auto;
  object-fit: contain;
}

.link-header__eyebrow {
  margin-top: var(--space-4);
  color: var(--color-primary);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-xs);
}

.link-header__title {
  margin-top: var(--space-2);
  color: var(--color-text-primary);
  font-size: var(--font-size-3xl);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-3xl);
}

.link-header__description {
  margin-top: var(--space-3);
  color: var(--color-text-secondary);
  font-size: var(--font-size-body);
  line-height: var(--line-height-body);
}

.link-account {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  min-height: var(--button-height-major);
  margin-top: var(--space-8);
  padding: 0 var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface-secondary);
}

.link-account__label {
  flex: 0 0 auto;
  color: var(--color-text-secondary);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-snug);
}

.link-account__value {
  min-width: 0;
  overflow-wrap: anywhere;
  color: var(--color-text-primary);
  font-size: var(--font-size-body);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-control);
  text-align: right;
}

.link-guide {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin-top: var(--space-5);
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
}

.link-guide__text {
  color: var(--color-text-secondary);
  font-size: var(--font-size-button-small);
  line-height: var(--line-height-relaxed);
}

.link-consent {
  margin-top: var(--space-5);
}

.link-consent__label {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  color: var(--color-text-primary);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-relaxed);
}

.link-consent__checkbox {
  flex: 0 0 auto;
  width: var(--icon-size-sm);
  height: var(--icon-size-sm);
  margin-top: 2px;
  accent-color: var(--color-primary);
}

.link-consent__error,
.link-submit-error,
.link-error {
  margin-top: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-control);
  background: var(--color-error-soft);
  color: var(--color-error);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-snug);
}

.link-actions {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  margin-top: var(--space-8);
}

.link-primary,
.link-secondary,
.link-text-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: var(--button-height-major);
  padding: 0 var(--space-5);
  border-radius: var(--radius-control);
  font-size: var(--font-size-body);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-control);
}

.link-primary {
  border: 1px solid transparent;
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

.link-primary:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.link-primary:disabled {
  background: var(--color-surface-secondary);
  color: var(--color-text-muted);
  cursor: not-allowed;
}

.link-secondary {
  border: 1px solid var(--color-border-strong);
  background: var(--color-surface);
  color: var(--color-text-primary);
}

.link-secondary:hover {
  background: var(--color-surface-secondary);
}

.link-secondary:disabled,
.link-text-button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.link-text-button {
  height: var(--button-height-standard);
  border: 0;
  background: transparent;
  color: var(--color-text-secondary);
}

.link-text-button:hover {
  color: var(--color-primary);
}

.link-primary:focus-visible,
.link-secondary:focus-visible,
.link-header__logo-link:focus-visible,
.link-text-button:focus-visible {
  outline: var(--focus-ring-width) solid var(--color-primary);
  outline-offset: var(--focus-ring-offset);
}

@media (max-width: 560px) {
  .link-card {
    padding: var(--space-6);
  }

  .link-account {
    align-items: flex-start;
    flex-direction: column;
    justify-content: center;
    padding: var(--space-3) var(--space-4);
  }

  .link-account__value {
    text-align: left;
  }
}
</style>
