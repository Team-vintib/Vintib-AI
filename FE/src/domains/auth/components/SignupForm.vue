<script setup lang="ts">
import { computed, reactive, ref } from 'vue'

import EmailVerificationField from '@/domains/auth/components/EmailVerificationField.vue'
import {
  isEmail,
  isRequired,
  isSameValue,
  isSignupPassword,
  isVerificationCode,
} from '@/shared/utils/validators'

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

const errors = reactive<Record<SignupField, string>>({
  name: '',
  email: '',
  verificationCode: '',
  password: '',
  passwordConfirm: '',
})

const isPasswordVisible = ref(false)
const isAgreementTouched = ref(false)
const isSendingVerificationCode = ref(false)
const isVerifyingEmailCode = ref(false)
const isEmailVerificationCodeSent = ref(false)
const isEmailVerified = ref(false)
const emailVerificationMessage = ref('')
const verifiedEmail = ref('')

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

const agreementError = computed(() => {
  if (!isAgreementTouched.value || isRequiredAgreementChecked.value) {
    return ''
  }

  return '필수 약관에 모두 동의해 주세요.'
})

const canRequestVerificationCode = computed(() => isEmail(form.email))
const canConfirmVerificationCode = computed(() => isVerificationCode(form.verificationCode))

const isFormValid = computed(
  () =>
    isRequired(form.name) &&
    form.name.trim().length <= 30 &&
    isEmail(form.email) &&
    isEmailVerified.value &&
    verifiedEmail.value === form.email.trim() &&
    isVerificationCode(form.verificationCode) &&
    isSignupPassword(form.password) &&
    isSameValue(form.passwordConfirm, form.password) &&
    isRequiredAgreementChecked.value,
)

const getFieldError = (field: SignupField) => {
  if (field === 'name') {
    if (!isRequired(form.name)) {
      return '이름을 입력해 주세요.'
    }

    if (form.name.trim().length > 30) {
      return '이름은 30자 이내로 입력해 주세요.'
    }
  }

  if (field === 'email') {
    if (!isRequired(form.email)) {
      return '이메일을 입력해 주세요.'
    }

    if (!isEmail(form.email)) {
      return '이메일 형식을 확인해 주세요.'
    }
  }

  if (field === 'verificationCode') {
    if (!isRequired(form.verificationCode)) {
      return '인증코드를 입력해 주세요.'
    }

    if (!isVerificationCode(form.verificationCode)) {
      return '인증코드는 숫자 6자리로 입력해 주세요.'
    }
  }

  if (field === 'password') {
    if (!form.password) {
      return '비밀번호를 입력해 주세요.'
    }

    if (!isSignupPassword(form.password)) {
      return '비밀번호는 영문과 숫자를 포함해 8~20자로 입력해 주세요.'
    }
  }

  if (field === 'passwordConfirm') {
    if (!form.passwordConfirm) {
      return '비밀번호 확인을 입력해 주세요.'
    }

    if (!isSameValue(form.passwordConfirm, form.password)) {
      return '비밀번호가 일치하지 않습니다.'
    }
  }

  return ''
}

const validateField = (field: SignupField) => {
  errors[field] = getFieldError(field)

  return !errors[field]
}

const handleFieldBlur = (field: SignupField) => {
  touched[field] = true

  if (field === 'name' || field === 'email') {
    form[field] = form[field].trim()
  }

  validateField(field)
}

const handleFieldInput = (field: SignupField) => {
  if (touched[field]) {
    validateField(field)
  }

  if (field === 'email') {
    resetEmailVerification()
  }

  if (field === 'password' && touched.passwordConfirm) {
    validateField('passwordConfirm')
  }
}

const togglePasswordVisibility = () => {
  isPasswordVisible.value = !isPasswordVisible.value
}

const handleAllAgreementChange = (event: Event) => {
  const isChecked = (event.target as HTMLInputElement).checked

  agreements.serviceTerms = isChecked
  agreements.privacyPolicy = isChecked
  agreements.marketing = isChecked
  isAgreementTouched.value = true
}

const handleAgreementChange = (key: AgreementField, event: Event) => {
  agreements[key] = (event.target as HTMLInputElement).checked
  isAgreementTouched.value = true
}

const handleVerificationCodeUpdate = (verificationCode: string) => {
  form.verificationCode = verificationCode
  handleFieldInput('verificationCode')
}

const resetEmailVerification = () => {
  form.verificationCode = ''
  isEmailVerificationCodeSent.value = false
  isEmailVerified.value = false
  emailVerificationMessage.value = ''
  verifiedEmail.value = ''

  if (touched.verificationCode) {
    errors.verificationCode = ''
  }
}

const handleSendVerificationCode = async () => {
  touched.email = true

  if (!validateField('email') || isSendingVerificationCode.value) {
    return
  }

  isSendingVerificationCode.value = true
  emailVerificationMessage.value = ''

  await new Promise((resolve) => window.setTimeout(resolve, 300))

  isEmailVerificationCodeSent.value = true
  isSendingVerificationCode.value = false
  emailVerificationMessage.value = '인증코드를 발송했습니다. 이메일을 확인해 주세요.'
}

const handleVerifyEmailCode = async () => {
  touched.verificationCode = true

  if (!isEmailVerificationCodeSent.value) {
    errors.verificationCode = '먼저 인증코드를 발송해 주세요.'
    return
  }

  if (!validateField('verificationCode') || isVerifyingEmailCode.value) {
    return
  }

  isVerifyingEmailCode.value = true
  emailVerificationMessage.value = ''

  await new Promise((resolve) => window.setTimeout(resolve, 300))

  isEmailVerified.value = true
  verifiedEmail.value = form.email.trim()
  isVerifyingEmailCode.value = false
  emailVerificationMessage.value = '이메일 인증이 완료되었습니다.'
}

const markAllTouched = () => {
  Object.keys(touched).forEach((field) => {
    touched[field as SignupField] = true
  })

  isAgreementTouched.value = true
}

const validateForm = () => {
  markAllTouched()

  return (
    (Object.keys(errors) as SignupField[]).map((field) => validateField(field)).every(Boolean) &&
    isRequiredAgreementChecked.value
  )
}

const handleSubmit = () => {
  if (!validateForm()) {
    return
  }
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
          class="h-12 w-full rounded-[var(--radius-control)] border bg-[var(--color-surface)] px-4 text-[var(--color-text-primary)] outline-none transition focus:border-[var(--color-primary)] focus:ring-4 focus:ring-[var(--color-primary-soft)]"
          :class="
            errors.name ? 'border-[var(--color-error)]' : 'border-[var(--color-border-strong)]'
          "
          type="text"
          autocomplete="name"
          placeholder="성함을 입력해주세요."
          :aria-invalid="errors.name ? 'true' : 'false'"
          aria-describedby="signup-name-error"
          @input="handleFieldInput('name')"
          @blur="handleFieldBlur('name')"
        />
        <p
          v-if="errors.name"
          id="signup-name-error"
          class="text-[13px] leading-5 text-[var(--color-error)]"
        >
          {{ errors.name }}
        </p>
      </div>

      <EmailVerificationField
        v-model:email="form.email"
        :verification-code="form.verificationCode"
        :email-error="errors.email"
        :verification-code-error="errors.verificationCode"
        :status-message="emailVerificationMessage"
        :is-sending-code="isSendingVerificationCode"
        :is-verifying-code="isVerifyingEmailCode"
        :can-send-code="canRequestVerificationCode"
        :can-verify-code="canConfirmVerificationCode"
        :is-verified="isEmailVerified"
        @update:email="handleFieldInput('email')"
        @update:verification-code="handleVerificationCodeUpdate"
        @email-blur="handleFieldBlur('email')"
        @verification-code-blur="handleFieldBlur('verificationCode')"
        @send-code="handleSendVerificationCode"
        @verify-code="handleVerifyEmailCode"
      />

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
            class="h-12 w-full rounded-[var(--radius-control)] border bg-[var(--color-surface)] px-4 pr-20 text-[var(--color-text-primary)] outline-none transition focus:border-[var(--color-primary)] focus:ring-4 focus:ring-[var(--color-primary-soft)]"
            :class="
              errors.password
                ? 'border-[var(--color-error)]'
                : 'border-[var(--color-border-strong)]'
            "
            :type="isPasswordVisible ? 'text' : 'password'"
            autocomplete="new-password"
            placeholder="비밀번호를 입력해주세요."
            :aria-invalid="errors.password ? 'true' : 'false'"
            aria-describedby="signup-password-message"
            @input="handleFieldInput('password')"
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
        <p
          id="signup-password-message"
          class="text-[13px] leading-5"
          :class="errors.password ? 'text-[var(--color-error)]' : 'text-[var(--color-text-muted)]'"
        >
          {{ errors.password || '8~20자, 영문과 숫자를 포함해 입력해주세요.' }}
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
          class="h-12 w-full rounded-[var(--radius-control)] border bg-[var(--color-surface)] px-4 text-[var(--color-text-primary)] outline-none transition focus:border-[var(--color-primary)] focus:ring-4 focus:ring-[var(--color-primary-soft)]"
          :class="
            errors.passwordConfirm
              ? 'border-[var(--color-error)]'
              : 'border-[var(--color-border-strong)]'
          "
          :type="isPasswordVisible ? 'text' : 'password'"
          autocomplete="new-password"
          placeholder="비밀번호를 다시 입력해주세요."
          :aria-invalid="errors.passwordConfirm ? 'true' : 'false'"
          aria-describedby="signup-password-confirm-error"
          @input="handleFieldInput('passwordConfirm')"
          @blur="handleFieldBlur('passwordConfirm')"
        />
        <p
          v-if="errors.passwordConfirm"
          id="signup-password-confirm-error"
          class="text-[13px] leading-5 text-[var(--color-error)]"
        >
          {{ errors.passwordConfirm }}
        </p>
      </div>
    </section>

    <section
      class="rounded-[var(--radius-control)] border p-4"
      :class="agreementError ? 'border-[var(--color-error)]' : 'border-[var(--color-border)]'"
      aria-labelledby="agreement-title"
      aria-describedby="agreement-error"
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

      <p
        v-if="agreementError"
        id="agreement-error"
        class="mt-3 text-[13px] leading-5 text-[var(--color-error)]"
      >
        {{ agreementError }}
      </p>
    </section>

    <section class="space-y-3" aria-label="회원가입 실행">
      <button
        class="h-[var(--button-height-major)] w-full rounded-[var(--radius-control)] px-5 text-[15px] font-semibold transition focus:outline-none focus:ring-4 focus:ring-[var(--color-primary-soft)]"
        :class="
          isFormValid
            ? 'bg-[var(--color-primary)] text-[var(--color-text-inverse)] hover:bg-[var(--color-primary-hover)]'
            : 'bg-[var(--color-surface-secondary)] text-[var(--color-text-muted)]'
        "
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
    <a class="font-semibold text-[var(--color-primary)]" href="/auth/login"> 로그인하기 </a>
  </footer>
</template>
