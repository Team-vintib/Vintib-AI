<script setup lang="ts">
interface Props {
  email: string
  verificationCode: string
  emailError?: string
  verificationCodeError?: string
  statusMessage?: string
  isSendingCode?: boolean
  isVerifyingCode?: boolean
  canSendCode?: boolean
  canVerifyCode?: boolean
  isVerified?: boolean
  disabled?: boolean
}

const {
  emailError = '',
  verificationCodeError = '',
  statusMessage = '',
  isSendingCode = false,
  isVerifyingCode = false,
  canSendCode = false,
  canVerifyCode = false,
  isVerified = false,
  disabled = false,
} = defineProps<Props>()

const emit = defineEmits<{
  'update:email': [value: string]
  'update:verificationCode': [value: string]
  emailBlur: []
  verificationCodeBlur: []
  sendCode: []
  verifyCode: []
}>()

const handleEmailInput = (event: Event) => {
  emit('update:email', (event.target as HTMLInputElement).value)
}

const handleVerificationCodeInput = (event: Event) => {
  const verificationCode = (event.target as HTMLInputElement).value.replace(/\D/g, '').slice(0, 6)

  emit('update:verificationCode', verificationCode)
}
</script>

<template>
  <div class="space-y-4">
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
          class="h-12 min-w-0 flex-1 rounded-[var(--radius-control)] border bg-[var(--color-surface)] px-4 text-[var(--color-text-primary)] outline-none transition focus:border-[var(--color-primary)] focus:ring-4 focus:ring-[var(--color-primary-soft)]"
          :class="
            emailError ? 'border-[var(--color-error)]' : 'border-[var(--color-border-strong)]'
          "
          type="email"
          autocomplete="email"
          placeholder="이메일을 입력해주세요."
          :value="email"
          :readonly="isVerified || disabled"
          :aria-invalid="emailError ? 'true' : 'false'"
          aria-describedby="signup-email-message"
          @input="handleEmailInput"
          @blur="emit('emailBlur')"
        />
        <button
          class="h-12 shrink-0 rounded-[var(--radius-control)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-4 text-sm font-semibold text-[var(--color-text-primary)] transition hover:bg-[var(--color-surface-secondary)] focus:outline-none focus:ring-4 focus:ring-[var(--color-primary-soft)] disabled:cursor-not-allowed disabled:opacity-50"
          type="button"
          :disabled="!canSendCode || isSendingCode || isVerifyingCode || isVerified || disabled"
          @click="emit('sendCode')"
        >
          {{ isSendingCode ? '발송 중' : '인증코드 발송' }}
        </button>
      </div>
      <p
        v-if="emailError || statusMessage"
        id="signup-email-message"
        class="text-[13px] leading-5"
        :class="emailError ? 'text-[var(--color-error)]' : 'text-[var(--color-text-secondary)]'"
      >
        {{ emailError || statusMessage }}
      </p>
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
          class="h-12 min-w-0 flex-1 rounded-[var(--radius-control)] border bg-[var(--color-surface)] px-4 text-[var(--color-text-primary)] outline-none transition focus:border-[var(--color-primary)] focus:ring-4 focus:ring-[var(--color-primary-soft)]"
          :class="
            verificationCodeError
              ? 'border-[var(--color-error)]'
              : 'border-[var(--color-border-strong)]'
          "
          type="text"
          inputmode="numeric"
          autocomplete="one-time-code"
          placeholder="6자리 인증코드"
          :value="verificationCode"
          :readonly="isVerified || disabled"
          :aria-invalid="verificationCodeError ? 'true' : 'false'"
          aria-describedby="signup-verification-code-error"
          @input="handleVerificationCodeInput"
          @blur="emit('verificationCodeBlur')"
        />
        <button
          class="h-12 shrink-0 rounded-[var(--radius-control)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-4 text-sm font-semibold text-[var(--color-text-primary)] transition hover:bg-[var(--color-surface-secondary)] focus:outline-none focus:ring-4 focus:ring-[var(--color-primary-soft)] disabled:cursor-not-allowed disabled:opacity-50"
          type="button"
          :disabled="!canVerifyCode || isSendingCode || isVerifyingCode || isVerified || disabled"
          @click="emit('verifyCode')"
        >
          {{ isVerifyingCode ? '확인 중' : '확인' }}
        </button>
      </div>
      <p
        v-if="verificationCodeError"
        id="signup-verification-code-error"
        class="text-[13px] leading-5 text-[var(--color-error)]"
      >
        {{ verificationCodeError }}
      </p>
    </div>
  </div>
</template>

<style scoped lang="scss">
.space-y-4 {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.space-y-2 {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

input {
  padding: 0 var(--space-4);
}

button {
  padding: 0 var(--space-4);
}

@media (max-width: 640px) {
  .max-sm\:flex-col {
    flex-direction: column;
  }
}
</style>
