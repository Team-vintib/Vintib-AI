<script setup lang="ts">
import logoImage from '@/assets/images/logo-white.png'
import LoginForm from '@/domains/auth/components/LoginForm.vue'
import { ROUTE_NAMES } from '@/shared/constants/routes'
import AuthLayout from '@/shared/layouts/AuthLayout.vue'
</script>

<template>
  <AuthLayout>
    <article
      class="login-card rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-8 shadow-sm"
      aria-labelledby="login-title"
    >
      <header class="login-header">
        <RouterLink
          class="login-header__logo-link"
          :to="{ name: ROUTE_NAMES.HOME }"
          aria-label="VinTib 홈"
        >
          <img class="login-header__logo" :src="logoImage" alt="VinTib" />
        </RouterLink>
        <h1 id="login-title" class="login-header__title text-[var(--color-text-primary)]">
          이메일 로그인
        </h1>
        <p class="login-header__description text-[var(--color-text-secondary)]">
          VinTib 계정으로 로그인하고 서비스를 이용해보세요.
        </p>
      </header>

      <LoginForm />
    </article>
  </AuthLayout>
</template>

<style scoped lang="scss">
.login-card {
  width: 100%;
  padding: var(--space-8);
}

.login-header {
  margin-bottom: var(--space-10);
}

.login-header__logo-link {
  display: block;
  width: min(180px, 52vw);
  margin-right: auto;
  margin-bottom: var(--space-2);
  margin-left: auto;
  border-radius: var(--radius-control);
}

.login-header__logo {
  display: block;
  width: 100%;
  height: auto;
  object-fit: contain;
}

.login-header__logo-link:focus-visible {
  outline: var(--focus-ring-width) solid var(--color-primary);
  outline-offset: var(--focus-ring-offset);
}

.login-header__title {
  font-size: var(--font-size-4xl);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-4xl);
}

.login-header__description {
  margin-top: var(--space-3);
  font-size: var(--font-size-body);
  line-height: var(--line-height-body);
}

@media (max-width: 560px) {
  .login-card {
    padding: var(--space-6);
  }

  .login-header {
    margin-bottom: var(--space-8);
  }

  .login-header__title {
    font-size: var(--font-size-3xl);
    line-height: var(--line-height-3xl);
  }
}
</style>
