<script setup lang="ts">
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

      <form class="space-y-6" novalidate>
        <section class="space-y-4" aria-label="가입 정보">
          <div class="space-y-2">
            <label
              class="block text-sm font-semibold text-[var(--color-text-primary)]"
              for="signup-name"
            >
              이름
            </label>
            <input
              id="signup-name"
              class="h-12 w-full rounded-[var(--radius-control)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-4 text-[var(--color-text-primary)] outline-none transition focus:border-[var(--color-primary)] focus:ring-4 focus:ring-[var(--color-primary-soft)]"
              type="text"
              autocomplete="name"
              placeholder="성함을 입력해주세요."
            />
          </div>

          <div class="space-y-2">
            <label
              class="block text-sm font-semibold text-[var(--color-text-primary)]"
              for="signup-email"
            >
              이메일
            </label>
            <div class="flex gap-2">
              <input
                id="signup-email"
                class="h-12 min-w-0 flex-1 rounded-[var(--radius-control)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-4 text-[var(--color-text-primary)] outline-none transition focus:border-[var(--color-primary)] focus:ring-4 focus:ring-[var(--color-primary-soft)]"
                type="email"
                autocomplete="email"
                placeholder="이메일을 입력해주세요."
              />
              <button
                class="h-12 shrink-0 rounded-[var(--radius-control)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-4 text-sm font-semibold text-[var(--color-text-primary)] transition hover:bg-[var(--color-surface-secondary)] focus:outline-none focus:ring-4 focus:ring-[var(--color-primary-soft)]"
                type="button"
              >
                인증코드 발송
              </button>
            </div>
          </div>

          <div class="space-y-2">
            <label
              class="block text-sm font-semibold text-[var(--color-text-primary)]"
              for="signup-verification-code"
            >
              인증코드
            </label>
            <div class="flex gap-2">
              <input
                id="signup-verification-code"
                class="h-12 min-w-0 flex-1 rounded-[var(--radius-control)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-4 text-[var(--color-text-primary)] outline-none transition focus:border-[var(--color-primary)] focus:ring-4 focus:ring-[var(--color-primary-soft)]"
                type="text"
                inputmode="numeric"
                autocomplete="one-time-code"
                placeholder="6자리 인증코드"
              />
              <button
                class="h-12 shrink-0 rounded-[var(--radius-control)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-4 text-sm font-semibold text-[var(--color-text-primary)] transition hover:bg-[var(--color-surface-secondary)] focus:outline-none focus:ring-4 focus:ring-[var(--color-primary-soft)]"
                type="button"
              >
                확인
              </button>
            </div>
          </div>

          <div class="space-y-2">
            <label
              class="block text-sm font-semibold text-[var(--color-text-primary)]"
              for="signup-password"
            >
              비밀번호
            </label>
            <div class="relative">
              <input
                id="signup-password"
                class="h-12 w-full rounded-[var(--radius-control)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-4 pr-20 text-[var(--color-text-primary)] outline-none transition focus:border-[var(--color-primary)] focus:ring-4 focus:ring-[var(--color-primary-soft)]"
                type="password"
                autocomplete="new-password"
                placeholder="비밀번호를 입력해주세요."
              />
              <button
                class="absolute right-2 top-1/2 h-9 -translate-y-1/2 rounded-[var(--radius-control)] px-3 text-sm font-semibold text-[var(--color-text-secondary)] transition hover:bg-[var(--color-surface-secondary)] focus:outline-none focus:ring-4 focus:ring-[var(--color-primary-soft)]"
                type="button"
              >
                보기
              </button>
            </div>
            <p class="text-[13px] leading-5 text-[var(--color-text-muted)]">
              8~20자, 영문과 숫자를 포함해 입력해주세요.
            </p>
          </div>

          <div class="space-y-2">
            <label
              class="block text-sm font-semibold text-[var(--color-text-primary)]"
              for="signup-password-confirm"
            >
              비밀번호 확인
            </label>
            <input
              id="signup-password-confirm"
              class="h-12 w-full rounded-[var(--radius-control)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-4 text-[var(--color-text-primary)] outline-none transition focus:border-[var(--color-primary)] focus:ring-4 focus:ring-[var(--color-primary-soft)]"
              type="password"
              autocomplete="new-password"
              placeholder="비밀번호를 다시 입력해주세요."
            />
          </div>
        </section>

        <section
          class="rounded-[var(--radius-control)] border border-[var(--color-border)] p-4"
          aria-labelledby="agreement-title"
        >
          <div class="mb-4 flex items-center justify-between gap-4">
            <h2
              id="agreement-title"
              class="text-base font-semibold text-[var(--color-text-primary)]"
            >
              약관 동의
            </h2>
            <label
              class="flex items-center gap-2 text-sm font-semibold text-[var(--color-primary)]"
            >
              <input class="size-4 accent-[var(--color-primary)]" type="checkbox" />
              전체 동의
            </label>
          </div>

          <div class="space-y-3">
            <div class="flex items-center justify-between gap-3">
              <label
                class="flex min-w-0 items-center gap-2 text-sm text-[var(--color-text-primary)]"
              >
                <input class="size-4 accent-[var(--color-primary)]" type="checkbox" />
                <span>[필수] 서비스 이용약관 동의</span>
              </label>
              <button
                class="shrink-0 text-sm font-semibold text-[var(--color-text-secondary)]"
                type="button"
              >
                보기
              </button>
            </div>

            <div class="flex items-center justify-between gap-3">
              <label
                class="flex min-w-0 items-center gap-2 text-sm text-[var(--color-text-primary)]"
              >
                <input class="size-4 accent-[var(--color-primary)]" type="checkbox" />
                <span>[필수] 개인정보 수집 및 이용 동의</span>
              </label>
              <button
                class="shrink-0 text-sm font-semibold text-[var(--color-text-secondary)]"
                type="button"
              >
                보기
              </button>
            </div>

            <div class="flex items-center justify-between gap-3">
              <label
                class="flex min-w-0 items-center gap-2 text-sm text-[var(--color-text-primary)]"
              >
                <input class="size-4 accent-[var(--color-primary)]" type="checkbox" />
                <span>[선택] 마케팅 정보 수신 동의</span>
              </label>
              <button
                class="shrink-0 text-sm font-semibold text-[var(--color-text-secondary)]"
                type="button"
              >
                보기
              </button>
            </div>
          </div>
        </section>

        <section class="space-y-3" aria-label="회원가입 실행">
          <button
            class="h-[var(--button-height-major)] w-full rounded-[var(--radius-control)] bg-[var(--color-primary)] px-5 text-[15px] font-semibold text-[var(--color-text-inverse)] transition hover:bg-[var(--color-primary-hover)] focus:outline-none focus:ring-4 focus:ring-[var(--color-primary-soft)]"
            type="submit"
          >
            가입하기
          </button>

          <button
            class="h-12 w-full rounded-[var(--radius-control)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-5 text-[15px] font-semibold text-[var(--color-text-primary)] transition hover:bg-[var(--color-surface-secondary)] focus:outline-none focus:ring-4 focus:ring-[var(--color-primary-soft)]"
            type="button"
          >
            싸피어스로 가입하기
          </button>
        </section>
      </form>

      <footer class="mt-6 text-center text-sm text-[var(--color-text-secondary)]">
        이미 계정이 있나요?
        <a class="font-semibold text-[var(--color-primary)]" href="/auth/login">로그인하기</a>
      </footer>
    </article>
  </AuthLayout>
</template>
