<script setup lang="ts">
import SignupForm from '@/domains/auth/components/SignupForm.vue'
import AuthLayout from '@/shared/layouts/AuthLayout.vue'
</script>

<template>
  <AuthLayout>
    <article
      class="rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-8 shadow-sm"
      aria-labelledby="signup-title"
    >
      <header class="mb-8">
        <p class="mb-2 text-sm font-semibold text-[var(--color-primary)]">VinTib</p>
        <h1
          id="signup-title"
          class="text-3xl font-bold leading-10 text-[var(--color-text-primary)]"
        >
          이메일 회원가입
        </h1>
        <p class="mt-3 text-[15px] leading-6 text-[var(--color-text-secondary)]">
          VinTib 서비스 이용을 위해 정보를 입력해주세요.
        </p>
      </header>

      <SignupForm />
    </article>
  </AuthLayout>
</template>
