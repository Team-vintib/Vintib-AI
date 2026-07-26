<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import logoImage from '@/assets/images/logo.png'
import { ROUTE_NAMES, ROUTE_PATHS } from '@/shared/constants/routes'
import AuthLayout from '@/shared/layouts/AuthLayout.vue'

const LINK_ACCOUNT_STORAGE_KEY = 'vintib_ssafy_link_account'

interface LinkAccountInfo {
  email?: string
}

const router = useRouter()

const accountInfo = ref<LinkAccountInfo | null>(null)

const displayEmail = computed(() => accountInfo.value?.email || '가입된 이메일 계정')

onMounted(() => {
  accountInfo.value = readAccountInfo()
})

const handleRetrySso = async () => {
  window.sessionStorage.removeItem(LINK_ACCOUNT_STORAGE_KEY)
  await router.push({ name: ROUTE_NAMES.AUTH_SSAFY, query: { from: 'signup' } })
}

function readAccountInfo() {
  const rawInfo = window.sessionStorage.getItem(LINK_ACCOUNT_STORAGE_KEY)

  if (!rawInfo) {
    return null
  }

  try {
    return JSON.parse(rawInfo) as LinkAccountInfo
  } catch {
    return null
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
        <h1 id="link-title" class="link-header__title">
          이미 가입된 계정입니다
        </h1>
        <p class="link-header__description">
          싸피어스 인증 이메일과 동일한 VinTib 계정이 확인되었습니다.
        </p>
      </header>

      <section class="link-account" aria-label="가입 계정 정보">
        <span class="link-account__label">가입 계정</span>
        <strong class="link-account__value">{{ displayEmail }}</strong>
      </section>

      <section class="link-actions" aria-label="기존 계정 안내 실행">
        <a class="link-primary" :href="ROUTE_PATHS.AUTH_LOGIN">
          로그인으로 이동
        </a>
        <a class="link-secondary" :href="ROUTE_PATHS.AUTH_SIGNUP">
          이메일 회원가입으로 돌아가기
        </a>
        <button class="link-text-button" type="button" @click="handleRetrySso">
          다시 인증하기
        </button>
      </section>
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

.link-primary:hover {
  background: var(--color-primary-hover);
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
