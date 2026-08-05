<script setup lang="ts">
import logoImage from '@/assets/images/logo.png'
import { ROUTE_NAMES } from '@/shared/constants/routes'
import AuthLayout from '@/shared/layouts/AuthLayout.vue'
</script>

<template>
  <AuthLayout>
    <article
      class="signup-entry-card rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-8 shadow-sm"
      aria-labelledby="signup-entry-title"
    >
      <header class="signup-entry-header">
        <RouterLink
          class="signup-entry-header__logo-link"
          :to="{ name: ROUTE_NAMES.HOME }"
          aria-label="VinTib 홈"
        >
          <img class="signup-entry-header__logo" :src="logoImage" alt="VinTib" />
        </RouterLink>
        <h1
          id="signup-entry-title"
          class="signup-entry-header__title text-[var(--color-text-primary)]"
        >
          회원가입
        </h1>
        <p class="signup-entry-header__description text-[var(--color-text-secondary)]">
          VinTib에서 사용할 가입 방식을 선택해주세요.
        </p>
      </header>

      <section class="signup-entry-actions" aria-label="회원가입 방식 선택">
        <RouterLink class="signup-entry-primary-link" :to="{ name: ROUTE_NAMES.AUTH_SIGNUP_EMAIL }">
          이메일로 가입하기
        </RouterLink>

        <RouterLink
          class="signup-entry-secondary-link"
          :to="{ name: ROUTE_NAMES.AUTH_SSAFY_SIGNUP }"
        >
          싸피어스로 가입하기
        </RouterLink>
      </section>

      <footer class="signup-entry-footer">
        이미 계정이 있나요?
        <RouterLink class="signup-entry-footer__link" :to="{ name: ROUTE_NAMES.AUTH_LOGIN }">
          로그인하기
        </RouterLink>
      </footer>
    </article>
  </AuthLayout>
</template>

<style scoped lang="scss">
.signup-entry-card {
  width: 100%;
  padding: var(--space-8);
}

.signup-entry-header {
  margin-bottom: var(--space-10);
}

.signup-entry-header__logo-link {
  display: block;
  width: min(180px, 52vw);
  margin-right: auto;
  margin-bottom: var(--space-2);
  margin-left: auto;
  border-radius: var(--radius-control);
}

.signup-entry-header__logo {
  display: block;
  width: 100%;
  height: auto;
  object-fit: contain;
}

.signup-entry-header__title {
  font-size: var(--font-size-4xl);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-4xl);
}

.signup-entry-header__description {
  margin-top: var(--space-3);
  font-size: var(--font-size-body);
  line-height: var(--line-height-body);
}

.signup-entry-actions {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.signup-entry-primary-link,
.signup-entry-secondary-link {
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
  transition:
    background-color var(--transition-base),
    border-color var(--transition-base),
    color var(--transition-base),
    transform var(--transition-base);
}

.signup-entry-primary-link {
  border: 1px solid transparent;
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

.signup-entry-primary-link:hover {
  background: var(--color-primary-hover);
}

.signup-entry-secondary-link {
  border: 1px solid var(--color-border-strong);
  background: var(--color-surface);
  color: var(--color-text-primary);
}

.signup-entry-secondary-link:hover {
  background: var(--color-surface-secondary);
}

.signup-entry-primary-link:focus-visible,
.signup-entry-secondary-link:focus-visible,
.signup-entry-header__logo-link:focus-visible,
.signup-entry-footer__link:focus-visible {
  outline: var(--focus-ring-width) solid var(--color-primary);
  outline-offset: var(--focus-ring-offset);
}

.signup-entry-primary-link:active,
.signup-entry-secondary-link:active {
  transform: translateY(1px);
}

.signup-entry-footer {
  margin-top: var(--space-6);
  color: var(--color-text-secondary);
  font-size: var(--font-size-button-small);
  line-height: var(--line-height-control);
  text-align: center;
}

.signup-entry-footer__link {
  color: var(--color-primary);
  font-weight: var(--font-weight-bold);
}

@media (max-width: 560px) {
  .signup-entry-card {
    padding: var(--space-6);
  }

  .signup-entry-header {
    margin-bottom: var(--space-8);
  }

  .signup-entry-header__title {
    font-size: var(--font-size-3xl);
    line-height: var(--line-height-3xl);
  }
}
</style>
