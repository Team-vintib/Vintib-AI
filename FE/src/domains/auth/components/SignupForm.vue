<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { RouterLink } from 'vue-router'

import { ROUTE_NAMES } from '@/shared/constants/routes'

type SignupField = 'name' | 'email' | 'verificationCode' | 'password' | 'passwordConfirm'
type AgreementField = 'serviceTerms' | 'privacyPolicy' | 'marketing'

interface SignupFormState {
  name: string
  email: string
  verificationCode: string
  password: string
  passwordConfirm: string
}

interface SignupAgreements {
  serviceTerms: boolean
  privacyPolicy: boolean
  marketing: boolean
}

const form = reactive<SignupFormState>({
  name: '',
  email: '',
  verificationCode: '',
  password: '',
  passwordConfirm: '',
})

const agreements = reactive<SignupAgreements>({
  serviceTerms: false,
  privacyPolicy: false,
  marketing: false,
})

const touched = reactive<Record<SignupField, boolean>>({
  name: false,
  email: false,
  verificationCode: false,
  password: false,
  passwordConfirm: false,
})

const isPasswordVisible = ref(false)

const agreementItems: {
  key: AgreementField
  label: string
  required: boolean
}[] = [
  {
    key: 'serviceTerms',
    label: '서비스 이용약관 동의',
    required: true,
  },
  {
    key: 'privacyPolicy',
    label: '개인정보 수집 및 이용 동의',
    required: true,
  },
  {
    key: 'marketing',
    label: '마케팅 정보 수신 동의',
    required: false,
  },
]

const isAllAgreed = computed(
  () => agreements.serviceTerms && agreements.privacyPolicy && agreements.marketing,
)

const isRequiredAgreementChecked = computed(
  () => agreements.serviceTerms && agreements.privacyPolicy,
)

const canRequestVerificationCode = computed(() => form.email.trim().length > 0)
const canConfirmVerificationCode = computed(() => form.verificationCode.trim().length > 0)

const canSubmit = computed(
  () =>
    form.name.trim().length > 0 &&
    form.email.trim().length > 0 &&
    form.verificationCode.trim().length > 0 &&
    form.password.length > 0 &&
    form.passwordConfirm.length > 0 &&
    isRequiredAgreementChecked.value,
)

const handleFieldBlur = (field: SignupField) => {
  touched[field] = true
}

const togglePasswordVisibility = () => {
  isPasswordVisible.value = !isPasswordVisible.value
}

const handleAllAgreementChange = (event: Event) => {
  const isChecked = (event.target as HTMLInputElement).checked

  agreements.serviceTerms = isChecked
  agreements.privacyPolicy = isChecked
  agreements.marketing = isChecked
}

const handleAgreementChange = (key: AgreementField, event: Event) => {
  agreements[key] = (event.target as HTMLInputElement).checked
}

const handleVerificationCodeInput = (event: Event) => {
  form.verificationCode = (event.target as HTMLInputElement).value.replace(/\D/g, '').slice(0, 6)
}

const markAllTouched = () => {
  Object.keys(touched).forEach((field) => {
    touched[field as SignupField] = true
  })
}

const handleSubmit = () => {
  markAllTouched()
}
</script>

<template>
  <form class="space-y-6" novalidate @submit.prevent="handleSubmit">
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
          v-model="form.name"
          class="h-12 w-full rounded-[var(--radius-control)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-4 text-[var(--color-text-primary)] outline-none transition focus:border-[var(--color-primary)] focus:ring-4 focus:ring-[var(--color-primary-soft)]"
          type="text"
          autocomplete="name"
          placeholder="성함을 입력해주세요."
          @blur="handleFieldBlur('name')"
        />
      </div>

      <div class="space-y-2">
        <label
          class="block text-sm font-semibold text-[var(--color-text-primary)]"
          for="signup-email"
        >
          이메일
        </label>
        <div class="flex gap-2 max-sm:flex-col">
          <input
            id="signup-email"
            v-model="form.email"
            class="h-12 min-w-0 flex-1 rounded-[var(--radius-control)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-4 text-[var(--color-text-primary)] outline-none transition focus:border-[var(--color-primary)] focus:ring-4 focus:ring-[var(--color-primary-soft)]"
            type="email"
            autocomplete="email"
            placeholder="이메일을 입력해주세요."
            @blur="handleFieldBlur('email')"
          />
          <button
            class="h-12 shrink-0 rounded-[var(--radius-control)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-4 text-sm font-semibold text-[var(--color-text-primary)] transition hover:bg-[var(--color-surface-secondary)] focus:outline-none focus:ring-4 focus:ring-[var(--color-primary-soft)] disabled:cursor-not-allowed disabled:opacity-50"
            type="button"
            :disabled="!canRequestVerificationCode"
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
        <div class="flex gap-2 max-sm:flex-col">
          <input
            id="signup-verification-code"
            class="h-12 min-w-0 flex-1 rounded-[var(--radius-control)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-4 text-[var(--color-text-primary)] outline-none transition focus:border-[var(--color-primary)] focus:ring-4 focus:ring-[var(--color-primary-soft)]"
            type="text"
            inputmode="numeric"
            autocomplete="one-time-code"
            placeholder="6자리 인증코드"
            :value="form.verificationCode"
            @input="handleVerificationCodeInput"
            @blur="handleFieldBlur('verificationCode')"
          />
          <button
            class="h-12 shrink-0 rounded-[var(--radius-control)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-4 text-sm font-semibold text-[var(--color-text-primary)] transition hover:bg-[var(--color-surface-secondary)] focus:outline-none focus:ring-4 focus:ring-[var(--color-primary-soft)] disabled:cursor-not-allowed disabled:opacity-50"
            type="button"
            :disabled="!canConfirmVerificationCode"
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
            v-model="form.password"
            class="h-12 w-full rounded-[var(--radius-control)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-4 pr-20 text-[var(--color-text-primary)] outline-none transition focus:border-[var(--color-primary)] focus:ring-4 focus:ring-[var(--color-primary-soft)]"
            :type="isPasswordVisible ? 'text' : 'password'"
            autocomplete="new-password"
            placeholder="비밀번호를 입력해주세요."
            @blur="handleFieldBlur('password')"
          />
          <button
            class="absolute right-2 top-1/2 h-9 -translate-y-1/2 rounded-[var(--radius-control)] px-3 text-sm font-semibold text-[var(--color-text-secondary)] transition hover:bg-[var(--color-surface-secondary)] focus:outline-none focus:ring-4 focus:ring-[var(--color-primary-soft)]"
            type="button"
            :aria-pressed="isPasswordVisible"
            @click="togglePasswordVisibility"
          >
            {{ isPasswordVisible ? '숨기기' : '보기' }}
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
          v-model="form.passwordConfirm"
          class="h-12 w-full rounded-[var(--radius-control)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-4 text-[var(--color-text-primary)] outline-none transition focus:border-[var(--color-primary)] focus:ring-4 focus:ring-[var(--color-primary-soft)]"
          :type="isPasswordVisible ? 'text' : 'password'"
          autocomplete="new-password"
          placeholder="비밀번호를 다시 입력해주세요."
          @blur="handleFieldBlur('passwordConfirm')"
        />
      </div>
    </section>

    <section
      class="rounded-[var(--radius-control)] border border-[var(--color-border)] p-4"
      aria-labelledby="agreement-title"
    >
      <div class="mb-4 flex items-center justify-between gap-4">
        <h2 id="agreement-title" class="text-base font-semibold text-[var(--color-text-primary)]">
          약관 동의
        </h2>
        <label class="flex items-center gap-2 text-sm font-semibold text-[var(--color-primary)]">
          <input
            class="size-4 accent-[var(--color-primary)]"
            type="checkbox"
            :checked="isAllAgreed"
            @change="handleAllAgreementChange"
          />
          전체 동의
        </label>
      </div>

      <div class="space-y-3">
        <div
          v-for="agreement in agreementItems"
          :key="agreement.key"
          class="flex items-center justify-between gap-3"
        >
          <label class="flex min-w-0 items-center gap-2 text-sm text-[var(--color-text-primary)]">
            <input
              class="size-4 accent-[var(--color-primary)]"
              type="checkbox"
              :checked="agreements[agreement.key]"
              @change="handleAgreementChange(agreement.key, $event)"
            />
            <span>{{ agreement.required ? '[필수]' : '[선택]' }} {{ agreement.label }}</span>
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
        class="h-[var(--button-height-major)] w-full rounded-[var(--radius-control)] bg-[var(--color-primary)] px-5 text-[15px] font-semibold text-[var(--color-text-inverse)] transition hover:bg-[var(--color-primary-hover)] focus:outline-none focus:ring-4 focus:ring-[var(--color-primary-soft)] disabled:cursor-not-allowed disabled:opacity-50"
        type="submit"
        :disabled="!canSubmit"
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
    <RouterLink
      class="font-semibold text-[var(--color-primary)]"
      :to="{ name: ROUTE_NAMES.AUTH_LOGIN }"
    >
      로그인하기
    </RouterLink>
  </footer>
</template>
