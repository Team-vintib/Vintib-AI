<script setup lang="ts">
import { computed, onBeforeUnmount, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import {
  checkEmailDuplicate,
  login,
  sendEmailVerificationCode,
  signUp,
  verifyEmailCode,
} from '@/domains/auth/api/authApi'
import EmailVerificationField from '@/domains/auth/components/EmailVerificationField.vue'
import { useAuthStore } from '@/domains/auth/stores/authStore'
import type { LoginResponse, SignUpResponse } from '@/domains/auth/types/auth.types'
import { normalizeApiError } from '@/shared/api/http'
import { ROUTE_NAMES } from '@/shared/constants/routes'
import type { ApiErrorBody } from '@/shared/types/api.types'
import {
  isEmail,
  isRequired,
  isSameValue,
  isSignupPassword,
  isVerificationCode,
} from '@/shared/utils/validators'

type SignupField = 'name' | 'email' | 'verificationCode' | 'password' | 'passwordConfirm'
type AgreementField = 'serviceTerms' | 'privacyPolicy' | 'marketing'
type ServerSignupField = Extract<SignupField, 'name' | 'email' | 'password'>

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

const authStore = useAuthStore()

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
const isCheckingEmailDuplicate = ref(false)
const isEmailDuplicateChecked = ref(false)
const isSendingVerificationCode = ref(false)
const isVerifyingEmailCode = ref(false)
const isEmailVerificationCodeSent = ref(false)
const isEmailVerified = ref(false)
const isSubmitting = ref(false)
const emailVerificationMessage = ref('')
const submitError = ref('')
const duplicateEmail = ref('')
const duplicateCheckedEmail = ref('')
const verificationToken = ref('')
const verifiedEmail = ref('')
const verificationCodeRemainingSeconds = ref(0)
const router = useRouter()

const VERIFICATION_CODE_TTL_SECONDS = 300
let verificationCodeTimerId: number | undefined

const stopVerificationCodeTimer = () => {
  window.clearInterval(verificationCodeTimerId)
  verificationCodeTimerId = undefined
}

const startVerificationCodeTimer = () => {
  stopVerificationCodeTimer()
  verificationCodeRemainingSeconds.value = VERIFICATION_CODE_TTL_SECONDS

  verificationCodeTimerId = window.setInterval(() => {
    verificationCodeRemainingSeconds.value -= 1

    if (verificationCodeRemainingSeconds.value <= 0) {
      stopVerificationCodeTimer()
      verificationCodeRemainingSeconds.value = 0
      isEmailVerificationCodeSent.value = false
      emailVerificationMessage.value = ''
      errors.verificationCode = '인증코드가 만료되었습니다. 인증코드를 다시 받아주세요.'
    }
  }, 1000)
}

onBeforeUnmount(() => {
  stopVerificationCodeTimer()
})

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

const normalizedEmail = computed(() => form.email.trim())
const isCurrentEmailDuplicateChecked = computed(
  () => isEmailDuplicateChecked.value && duplicateCheckedEmail.value === normalizedEmail.value,
)
const canRequestVerificationCode = computed(
  () =>
    isEmail(form.email) &&
    !(isEmailVerificationCodeSent.value && verificationCodeRemainingSeconds.value > 0),
)
const canConfirmVerificationCode = computed(() => isVerificationCode(form.verificationCode))
const codeExpiresInLabel = computed(() => {
  if (
    !isEmailVerificationCodeSent.value ||
    isEmailVerified.value ||
    verificationCodeRemainingSeconds.value <= 0
  ) {
    return ''
  }

  const minutes = Math.floor(verificationCodeRemainingSeconds.value / 60)
  const seconds = verificationCodeRemainingSeconds.value % 60

  return `${minutes}:${String(seconds).padStart(2, '0')}`
})
const serverFieldMap: Partial<Record<string, ServerSignupField | 'verificationCode'>> = {
  name: 'name',
  email: 'email',
  password: 'password',
  verificationToken: 'verificationCode',
}

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
  submitError.value = ''

  if (field === 'email') {
    duplicateEmail.value = ''
  }

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

  submitError.value = ''
  agreements.serviceTerms = isChecked
  agreements.privacyPolicy = isChecked
  agreements.marketing = isChecked
  isAgreementTouched.value = true
}

const handleAgreementChange = (key: AgreementField, event: Event) => {
  submitError.value = ''
  agreements[key] = (event.target as HTMLInputElement).checked
  isAgreementTouched.value = true
}

const handleVerificationCodeUpdate = (verificationCode: string) => {
  form.verificationCode = verificationCode
  handleFieldInput('verificationCode')
}

const resetEmailVerification = () => {
  stopVerificationCodeTimer()
  verificationCodeRemainingSeconds.value = 0
  form.verificationCode = ''
  isEmailDuplicateChecked.value = false
  isEmailVerificationCodeSent.value = false
  isEmailVerified.value = false
  emailVerificationMessage.value = ''
  duplicateCheckedEmail.value = ''
  verificationToken.value = ''
  verifiedEmail.value = ''

  if (touched.verificationCode) {
    errors.verificationCode = ''
  }
}

const handleRequestVerificationCode = async () => {
  touched.email = true

  if (
    !validateField('email') ||
    isCheckingEmailDuplicate.value ||
    isSendingVerificationCode.value ||
    isVerifyingEmailCode.value ||
    !canRequestVerificationCode.value
  ) {
    return
  }

  isCheckingEmailDuplicate.value = true
  submitError.value = ''
  emailVerificationMessage.value = ''
  errors.email = ''
  errors.verificationCode = ''

  try {
    const duplicateResponse = await checkEmailDuplicate({ email: normalizedEmail.value })

    if (!duplicateResponse.success) {
      applyEmailDuplicateCheckError(duplicateResponse.error?.code, duplicateResponse.error?.message)
      return
    }

    isEmailDuplicateChecked.value = true
    duplicateCheckedEmail.value = normalizedEmail.value
  } catch (error: unknown) {
    const apiError = normalizeApiError(error)

    applyEmailDuplicateCheckError(apiError.code, apiError.message)
    return
  } finally {
    isCheckingEmailDuplicate.value = false
  }

  isSendingVerificationCode.value = true
  form.verificationCode = ''
  verificationToken.value = ''
  verifiedEmail.value = ''
  isEmailVerified.value = false

  try {
    const response = await sendEmailVerificationCode({ email: normalizedEmail.value })

    if (!response.success) {
      applyEmailVerificationError(response.error?.code, response.error?.message)
      return
    }

    isEmailVerificationCodeSent.value = true
    isEmailVerified.value = false
    verificationToken.value = ''
    verifiedEmail.value = ''
    emailVerificationMessage.value = '인증코드를 발송했습니다. 이메일을 확인해 주세요.'
    startVerificationCodeTimer()
  } catch (error: unknown) {
    const apiError = normalizeApiError(error)

    applyEmailVerificationError(apiError.code, apiError.message)
  } finally {
    isSendingVerificationCode.value = false
  }
}

const handleVerifyEmailCode = async () => {
  touched.verificationCode = true

  if (!isCurrentEmailDuplicateChecked.value) {
    errors.email = '이메일 중복 확인을 먼저 완료해 주세요.'
    return
  }

  if (!isEmailVerificationCodeSent.value) {
    errors.verificationCode = '먼저 인증코드를 발송해 주세요.'
    return
  }

  if (
    !validateField('verificationCode') ||
    isVerifyingEmailCode.value ||
    isSendingVerificationCode.value
  ) {
    return
  }

  isVerifyingEmailCode.value = true
  emailVerificationMessage.value = ''
  errors.verificationCode = ''

  try {
    const response = await verifyEmailCode({
      email: normalizedEmail.value,
      code: form.verificationCode,
    })

    if (!response.success || !response.data?.verificationToken) {
      applyEmailVerificationError(response.error?.code, response.error?.message)
      return
    }

    isEmailVerified.value = true
    verificationToken.value = response.data.verificationToken
    verifiedEmail.value = normalizedEmail.value
    emailVerificationMessage.value = '이메일 인증이 완료되었습니다.'
    stopVerificationCodeTimer()
  } catch (error: unknown) {
    const apiError = normalizeApiError(error)

    applyEmailVerificationError(apiError.code, apiError.message)
  } finally {
    isVerifyingEmailCode.value = false
  }
}

const applyEmailDuplicateCheckError = (code?: string, message?: string) => {
  emailVerificationMessage.value = ''

  if (code === 'U003') {
    applyDuplicateEmailError(message)
    return
  }

  errors.email = message || '이메일 중복 확인을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.'
}

const applyEmailVerificationError = (code?: string, message?: string) => {
  emailVerificationMessage.value = ''

  if (code === 'U003') {
    applyDuplicateEmailError(message)
    return
  }

  if (code === 'U008') {
    errors.email = message || '인증코드 요청이 너무 많습니다. 잠시 후 다시 시도해주세요.'
    return
  }

  if (code === 'U005' || code === 'U007') {
    errors.verificationCode =
      message || '인증 코드가 일치하지 않거나 만료되었습니다. 인증코드를 다시 확인해 주세요.'
    return
  }

  errors.verificationCode =
    message || '이메일 인증을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.'
}

const markAllTouched = () => {
  Object.keys(touched).forEach((field) => {
    touched[field as SignupField] = true
  })

  isAgreementTouched.value = true
}

const validateForm = () => {
  markAllTouched()

  const isValid =
    (Object.keys(errors) as SignupField[]).map((field) => validateField(field)).every(Boolean) &&
    isRequiredAgreementChecked.value

  if (
    !isEmailVerified.value ||
    verifiedEmail.value !== normalizedEmail.value ||
    !verificationToken.value
  ) {
    errors.verificationCode = '이메일 인증을 완료해 주세요.'
    return false
  }

  return isValid
}

const handleSubmit = async () => {
  if (isSubmitting.value) {
    return
  }

  submitError.value = ''

  if (!validateForm()) {
    return
  }

  isSubmitting.value = true

  try {
    const response = await signUp({
      name: form.name.trim(),
      email: normalizedEmail.value,
      password: form.password,
      verificationToken: verificationToken.value,
    })

    if (!response.success) {
      applySignUpError(response.error)
      return
    }

    if (!response.data) {
      submitError.value = '회원가입 결과를 확인하지 못했습니다. 잠시 후 다시 시도해 주세요.'
      return
    }

    const loginResponse = await login({
      email: normalizedEmail.value,
      password: form.password,
    })

    if (!loginResponse.success) {
      submitError.value =
        loginResponse.error?.message ||
        '회원가입은 완료됐지만 로그인 세션을 만들지 못했습니다. 로그인 후 온보딩을 이어가 주세요.'
      return
    }

    if (!loginResponse.data?.accessToken) {
      submitError.value =
        '회원가입은 완료됐지만 로그인 토큰을 받지 못했습니다. 로그인 후 온보딩을 이어가 주세요.'
      return
    }

    authStore.setSession(buildSignupSession(loginResponse.data, response.data), true)
    await router.replace({ name: ROUTE_NAMES.ONBOARD_PROFILE })
  } catch (error: unknown) {
    const apiError = normalizeApiError(error)

    applySignUpError(apiError)
  } finally {
    isSubmitting.value = false
  }
}

const buildSignupSession = (
  loginResult: LoginResponse,
  signupResult: SignUpResponse,
): LoginResponse => ({
  ...loginResult,
  user: {
    id: loginResult.user?.id ?? signupResult.id,
    email: loginResult.user?.email ?? signupResult.email,
    name: loginResult.user?.name ?? signupResult.name,
    onboardingCompleted:
      loginResult.user?.onboardingCompleted ?? signupResult.onboardingCompleted ?? false,
  },
})

const handleSsafySignUp = async () => {
  if (isSubmitting.value) {
    return
  }

  await router.push({ name: ROUTE_NAMES.AUTH_SSAFY_SIGNUP })
}

const handleMoveToLogin = async () => {
  await router.push({ name: ROUTE_NAMES.AUTH_LOGIN })
}

const applySignUpError = (apiError?: ApiErrorBody | null) => {
  const code = apiError?.code
  const message = apiError?.message

  if (code === 'U003') {
    applyDuplicateEmailError(message)
    return
  }

  if (code === 'U006') {
    errors.verificationCode = message || '이메일 인증이 필요합니다.'
    resetEmailVerification()
    return
  }

  if (code === 'C001') {
    applySignUpFieldErrors(apiError)
    return
  }

  submitError.value = message || '회원가입을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.'
}

const applySignUpFieldErrors = (apiError?: ApiErrorBody | null) => {
  const mappedFields: SignupField[] = []
  const unmappedReasons: string[] = []

  apiError?.errors?.forEach((fieldError) => {
    const field = serverFieldMap[fieldError.field]

    if (!field) {
      unmappedReasons.push(fieldError.reason)
      return
    }

    touched[field] = true
    errors[field] = fieldError.reason
    mappedFields.push(field)
  })

  if (mappedFields.length === 0) {
    submitError.value = unmappedReasons[0] || apiError?.message || '입력값을 다시 확인해 주세요.'
    return
  }

  submitError.value = unmappedReasons[0] || apiError?.message || ''
}

const applyDuplicateEmailError = (message?: string) => {
  duplicateEmail.value = normalizedEmail.value
  errors.email = message || '이미 가입된 이메일입니다.'
  submitError.value = '이미 가입된 이메일입니다. 기존 계정으로 로그인해 주세요.'
  resetEmailVerification()
}
</script>

<template>
  <form class="space-y-6" novalidate @submit.prevent="handleSubmit">
    <p
      v-if="submitError"
      class="rounded-[var(--radius-control)] bg-[var(--color-error-soft)] px-4 py-3 text-sm font-medium text-[var(--color-error)]"
      role="alert"
    >
      {{ submitError }}
    </p>

    <button
      v-if="duplicateEmail"
      class="h-11 w-full rounded-[var(--radius-control)] border border-[var(--color-border-input)] bg-transparent px-5 text-[var(--font-size-body)] font-semibold text-[var(--color-text-primary)] transition hover:bg-[var(--color-surface-secondary)] focus:outline-none"
      type="button"
      :disabled="isSubmitting"
      @click="handleMoveToLogin"
    >
      로그인하기
    </button>

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
          class="h-12 w-full rounded-[var(--radius-control)] border bg-transparent px-4 text-[var(--color-text-primary)] outline-none transition focus:border-[var(--color-primary)]"
          :class="
            errors.name ? 'border-[var(--color-error)]' : 'border-[var(--color-border-input)]'
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
          class="text-[var(--font-size-caption)] leading-5 text-[var(--color-error)]"
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
        :is-sending-code="isCheckingEmailDuplicate || isSendingVerificationCode"
        :is-verifying-code="isVerifyingEmailCode"
        :can-send-code="canRequestVerificationCode"
        :can-verify-code="canConfirmVerificationCode"
        :is-code-sent="isEmailVerificationCodeSent"
        :is-verified="isEmailVerified"
        :disabled="isSubmitting"
        :code-expires-in-label="codeExpiresInLabel"
        @update:email="handleFieldInput('email')"
        @update:verification-code="handleVerificationCodeUpdate"
        @email-blur="handleFieldBlur('email')"
        @verification-code-blur="handleFieldBlur('verificationCode')"
        @send-code="handleRequestVerificationCode"
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
            class="h-12 w-full rounded-[var(--radius-control)] border bg-transparent px-4 pr-20 text-[var(--color-text-primary)] outline-none transition focus:border-[var(--color-primary)]"
            :class="
              errors.password
                ? 'border-[var(--color-error)]'
                : 'border-[var(--color-border-input)]'
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
            class="absolute right-2 top-1/2 h-9 -translate-y-1/2 rounded-[var(--radius-control)] px-3 text-sm font-semibold text-[var(--color-text-secondary)] transition hover:bg-[var(--color-surface-secondary)] focus:outline-none"
            type="button"
            :aria-pressed="isPasswordVisible"
            @click="togglePasswordVisibility"
          >
            {{ isPasswordVisible ? '숨기기' : '보기' }}
          </button>
        </div>
        <p
          id="signup-password-message"
          class="text-[var(--font-size-caption)] leading-5"
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
          class="h-12 w-full rounded-[var(--radius-control)] border bg-transparent px-4 text-[var(--color-text-primary)] outline-none transition focus:border-[var(--color-primary)]"
          :class="
            errors.passwordConfirm
              ? 'border-[var(--color-error)]'
              : 'border-[var(--color-border-input)]'
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
          class="text-[var(--font-size-caption)] leading-5 text-[var(--color-error)]"
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
            :disabled="isSubmitting"
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
              :disabled="isSubmitting"
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
        class="mt-3 text-[var(--font-size-caption)] leading-5 text-[var(--color-error)]"
      >
        {{ agreementError }}
      </p>
    </section>

    <section class="space-y-3" aria-label="회원가입 실행">
      <button
        class="h-[var(--button-height-major)] w-full rounded-[var(--radius-control)] px-5 text-[var(--font-size-body)] font-semibold transition focus:outline-none"
        :class="
          !isSubmitting
            ? 'bg-[var(--color-primary)] text-[var(--color-text-inverse)] hover:bg-[var(--color-primary-hover)]'
            : 'bg-[var(--color-surface-secondary)] text-[var(--color-text-muted)]'
        "
        type="submit"
        :disabled="isSubmitting"
      >
        {{ isSubmitting ? '가입 중' : '가입하기' }}
      </button>

      <button
        class="h-12 w-full rounded-[var(--radius-control)] border border-[var(--color-border-input)] bg-transparent px-5 text-[var(--font-size-body)] font-semibold text-[var(--color-text-primary)] transition hover:bg-[var(--color-surface-secondary)] focus:outline-none"
        type="button"
        :disabled="isSubmitting"
        @click="handleSsafySignUp"
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

<style scoped lang="scss">
form {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.space-y-2,
.space-y-3,
.space-y-4,
.space-y-6 {
  display: flex;
  flex-direction: column;
}

.space-y-2 {
  gap: var(--space-2);
}

.space-y-3 {
  gap: var(--space-3);
}

.space-y-4 {
  gap: var(--space-4);
}

.space-y-6 {
  gap: var(--space-6);
}

input:not([type='checkbox']) {
  padding: 0 var(--space-4);
}

#signup-password {
  padding-right: var(--space-20);
}

section[aria-labelledby='agreement-title'] {
  padding: var(--space-4);
}

.mb-4 {
  margin-bottom: var(--space-4);
}

.mt-3 {
  margin-top: var(--space-3);
}

.mt-6 {
  margin-top: var(--space-6);
}

button {
  padding-right: var(--space-4);
  padding-left: var(--space-4);
}

button[type='submit'] {
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

button[type='submit']:hover {
  background: var(--color-primary-hover);
}

button[type='submit']:disabled {
  background: var(--color-surface-secondary);
  color: var(--color-text-muted);
}
</style>
