<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import logoImage from '@/assets/images/logo.png'
import {
  clearLinkAccountSession,
  readLinkAccountSession,
} from '@/domains/auth/utils/linkAccountSession'
import type { LinkAccountSessionPayload } from '@/domains/auth/types/auth.types'
import { ROUTE_NAMES } from '@/shared/constants/routes'
import AuthLayout from '@/shared/layouts/AuthLayout.vue'

const router = useRouter()

const accountInfo = ref<LinkAccountSessionPayload | null>(null)
const isAgreementChecked = ref(false)
const consentError = ref('')
const pageError = ref('')

const displayEmail = computed(() => accountInfo.value?.email || '가입된 이메일 계정')
const canContinue = computed(() =>
  Boolean(accountInfo.value?.linkToken && isAgreementChecked.value),
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

const handleRetrySso = async () => {
  clearLinkAccountSession()
  await router.push({ name: ROUTE_NAMES.AUTH_SSAFY_SIGNUP })
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
}

const handleContinue = () => {
  if (!isAgreementChecked.value) {
    consentError.value = '계정 연결에 동의해 주세요.'
  }
}
</script>

<template>
  <AuthLayout>
    <article
      class="link-card rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-8 shadow-sm"
      aria-labelledby="link-title"
    >
      <header class="link-header">
        <img class="link-header__logo" :src="logoImage" alt="VinTib" />
        <p class="link-header__eyebrow">SSAFYERS SSO</p>
        <h1 id="link-title" class="link-header__title">기존 계정 연결 안내</h1>
        <p class="link-header__description">
          싸피어스 인증 이메일과 동일한 VinTib 계정이 확인되었습니다.
        </p>
      </header>

      <template v-if="hasValidAccountInfo">
        <section class="link-account" aria-label="가입 계정 정보">
          <span class="link-account__label">가입 계정</span>
          <strong class="link-account__value">{{ displayEmail }}</strong>
        </section>

        <section class="link-guide" aria-label="계정 연결 안내">
          <p class="link-guide__text">
            동의하면 기존 VinTib 계정에 싸피어스 로그인 정보가 연결됩니다.
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
              aria-describedby="link-account-agreement-message"
              @change="handleAgreementChange"
            />
            <span>기존 VinTib 계정에 싸피어스 로그인 정보를 연결하는 데 동의합니다.</span>
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

        <section class="link-actions" aria-label="계정 연결 실행">
          <button
            class="link-primary"
            type="button"
            :disabled="!canContinue"
            @click="handleContinue"
          >
            연결하고 계속하기
          </button>
          <button class="link-secondary" type="button" @click="handleMoveToLogin">
            로그인으로 이동
          </button>
          <button class="link-text-button" type="button" @click="handleRetrySso">
            다시 인증하기
          </button>
          <button class="link-text-button" type="button" @click="handleMoveToSignup">
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

.link-header__logo {
  width: min(180px, 52vw);
  height: auto;
  margin-right: auto;
  margin-bottom: var(--space-2);
  margin-left: auto;
  object-fit: contain;
}

.link-header__eyebrow {
  margin-top: var(--space-4);
  color: var(--color-primary);
  font-size: 12px;
  font-weight: 700;
  line-height: 16px;
}

.link-header__title {
  margin-top: var(--space-2);
  color: var(--color-text-primary);
  font-size: 28px;
  font-weight: 700;
  line-height: 38px;
}

.link-header__description {
  margin-top: var(--space-3);
  color: var(--color-text-secondary);
  font-size: 15px;
  line-height: 24px;
}

.link-account {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  min-height: 52px;
  margin-top: var(--space-8);
  padding: 0 var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface-secondary);
}

.link-account__label {
  flex: 0 0 auto;
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: 600;
  line-height: 18px;
}

.link-account__value {
  min-width: 0;
  overflow-wrap: anywhere;
  color: var(--color-text-primary);
  font-size: 15px;
  font-weight: 600;
  line-height: 20px;
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
  font-size: 14px;
  line-height: 22px;
}

.link-consent {
  margin-top: var(--space-5);
}

.link-consent__label {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  color: var(--color-text-primary);
  font-size: 14px;
  font-weight: 600;
  line-height: 22px;
}

.link-consent__checkbox {
  flex: 0 0 auto;
  width: 18px;
  height: 18px;
  margin-top: 2px;
  accent-color: var(--color-primary);
}

.link-consent__error,
.link-error {
  margin-top: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-control);
  background: var(--color-error-soft);
  color: var(--color-error);
  font-size: 13px;
  font-weight: 600;
  line-height: 18px;
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
  font-size: 15px;
  font-weight: 600;
  line-height: 20px;
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
.link-text-button:focus-visible {
  outline: 3px solid var(--color-primary);
  outline-offset: 3px;
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
