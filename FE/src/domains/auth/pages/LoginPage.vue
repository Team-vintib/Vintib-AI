<script setup lang="ts">
import logoImage from '@/assets/images/logo.png'
import LoginForm from '@/domains/auth/components/LoginForm.vue'
import AuthLayout from '@/shared/layouts/AuthLayout.vue'
</script>

<template>
  <AuthLayout>
    <article
      class="login-card rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-8 shadow-sm"
      aria-labelledby="login-title"
    >
      <header class="login-header">
        <img class="login-header__logo" :src="logoImage" alt="VinTib" />
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

.login-header__logo {
  display: block;
  width: min(180px, 52vw);
  height: auto;
  margin-right: auto;
  margin-bottom: var(--space-2);
  margin-left: auto;
  object-fit: contain;
}

.login-header__title {
  font-size: 32px;
  font-weight: 700;
  line-height: 44px;
}

.login-header__description {
  margin-top: var(--space-3);
  font-size: 15px;
  line-height: 24px;
}

@media (max-width: 560px) {
  .login-card {
    padding: var(--space-6);
  }

  .login-header {
    margin-bottom: var(--space-8);
  }

  .login-header__title {
    font-size: 28px;
    line-height: 38px;
  }
}
</style>
