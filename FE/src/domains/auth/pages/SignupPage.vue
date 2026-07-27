<script setup lang="ts">
import logoImage from '@/assets/images/logo.png'
import SignupForm from '@/domains/auth/components/SignupForm.vue'
import AuthLayout from '@/shared/layouts/AuthLayout.vue'
</script>

<template>
  <AuthLayout>
    <article
      class="signup-card rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-8 shadow-sm"
      aria-labelledby="signup-title"
    >
      <header class="signup-header">
        <img class="signup-header__logo" :src="logoImage" alt="VinTib" />
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

.signup-header__logo {
  display: block;
  width: min(180px, 52vw);
  height: auto;
  margin-right: auto;
  margin-bottom: var(--space-2);
  margin-left: auto;
  object-fit: contain;
}

.signup-header__title {
  font-size: 32px;
  font-weight: 700;
  line-height: 44px;
}

.signup-header__description {
  margin-top: var(--space-3);
  font-size: 15px;
  line-height: 24px;
}

@media (max-width: 560px) {
  .signup-card {
    padding: var(--space-6);
  }

  .signup-header {
    margin-bottom: var(--space-8);
  }

  .signup-header__title {
    font-size: 28px;
    line-height: 38px;
  }
}
</style>
