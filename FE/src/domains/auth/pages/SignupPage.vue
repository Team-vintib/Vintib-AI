<script setup lang="ts">
import logoImage from '@/assets/images/logo-white.png'
import SignupForm from '@/domains/auth/components/SignupForm.vue'
import { ROUTE_NAMES } from '@/shared/constants/routes'
import AuthLayout from '@/shared/layouts/AuthLayout.vue'
</script>

<template>
  <AuthLayout>
    <article
      class="signup-card rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-8 shadow-sm"
      aria-labelledby="signup-title"
    >
      <header class="signup-header">
        <RouterLink
          class="signup-header__logo-link"
          :to="{ name: ROUTE_NAMES.HOME }"
          aria-label="VinTib 홈"
        >
          <img class="signup-header__logo" :src="logoImage" alt="VinTib" />
        </RouterLink>
        <h1 id="signup-title" class="signup-header__title text-[var(--color-text-primary)]">
          이메일 회원가입
        </h1>
        <p class="signup-header__description text-[var(--color-text-secondary)]">
          VinTib 서비스 이용을 위해 정보를 입력해주세요.
        </p>
      </header>

      <SignupForm />
    </article>
  </AuthLayout>
</template>

<style scoped lang="scss">
.signup-card {
  width: 100%;
  padding: var(--space-8);
}

.signup-header {
  margin-bottom: var(--space-10);
}

.signup-header__logo-link {
  display: block;
  width: min(180px, 52vw);
  margin-right: auto;
  margin-bottom: var(--space-2);
  margin-left: auto;
  border-radius: var(--radius-control);
}

.signup-header__logo {
  display: block;
  width: 100%;
  height: auto;
  object-fit: contain;
}

.signup-header__logo-link:focus-visible {
  outline: var(--focus-ring-width) solid var(--color-primary);
  outline-offset: var(--focus-ring-offset);
}

.signup-header__title {
  font-size: var(--font-size-4xl);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-4xl);
}

.signup-header__description {
  margin-top: var(--space-3);
  font-size: var(--font-size-body);
  line-height: var(--line-height-body);
}

@media (max-width: 560px) {
  .signup-card {
    padding: var(--space-6);
  }

  .signup-header {
    margin-bottom: var(--space-8);
  }

  .signup-header__title {
    font-size: var(--font-size-3xl);
    line-height: var(--line-height-3xl);
  }
}
</style>
