<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { ROUTE_NAMES } from '@/shared/constants/routes'
import { isEmail, isRequired } from '@/shared/utils/validators'

type LoginField = 'email' | 'password'

interface LoginFormState {
  email: string
  password: string
  rememberMe: boolean
}

const form = reactive<LoginFormState>({
  email: '',
  password: '',
  rememberMe: true,
})

const touched = reactive<Record<LoginField, boolean>>({
  email: false,
  password: false,
})

const errors = reactive<Record<LoginField, string>>({
  email: '',
  password: '',
})

const router = useRouter()
const isPasswordVisible = ref(false)
const submitError = ref('')

const getFieldError = (field: LoginField) => {
  if (field === 'email') {
    if (!isRequired(form.email)) {
      return '이메일을 입력해 주세요.'
    }

    if (!isEmail(form.email)) {
      return '이메일 형식을 확인해 주세요.'
    }
  }

  if (field === 'password' && !isRequired(form.password)) {
    return '비밀번호를 입력해 주세요.'
  }

  return ''
}

const validateField = (field: LoginField) => {
  errors[field] = getFieldError(field)

  return !errors[field]
}

const handleFieldBlur = (field: LoginField) => {
  touched[field] = true

  if (field === 'email') {
    form.email = form.email.trim()
  }

  validateField(field)
}

const handleFieldInput = (field: LoginField) => {
  submitError.value = ''

  if (touched[field]) {
    validateField(field)
  }
}

const markAllTouched = () => {
  Object.keys(touched).forEach((field) => {
    touched[field as LoginField] = true
  })
}

const validateForm = () => {
  markAllTouched()

  return (Object.keys(errors) as LoginField[]).map((field) => validateField(field)).every(Boolean)
}

const togglePasswordVisibility = () => {
  isPasswordVisible.value = !isPasswordVisible.value
}

const handleRememberMeChange = (event: Event) => {
  form.rememberMe = (event.target as HTMLInputElement).checked
}

const handleSubmit = () => {
  submitError.value = ''

  if (!validateForm()) {
    return
  }
}

const handleSsafyLogin = async () => {
  await router.push({ name: ROUTE_NAMES.AUTH_SSAFY, query: { from: 'login' } })
}
</script>

<template>
  <form class="login-form" novalidate @submit.prevent="handleSubmit">
    <p v-if="submitError" class="login-form__error" role="alert">
      {{ submitError }}
    </p>

    <section class="login-form__fields" aria-label="로그인 정보">
      <div class="login-form__field">
        <label class="login-form__label" for="login-email"> 이메일 </label>
        <input
          id="login-email"
          v-model="form.email"
          class="login-form__input"
          :class="{ 'login-form__input--error': errors.email }"
          type="email"
          autocomplete="email"
          placeholder="이메일을 입력해주세요."
          :aria-invalid="errors.email ? 'true' : 'false'"
          aria-describedby="login-email-error"
          @input="handleFieldInput('email')"
          @blur="handleFieldBlur('email')"
        />
        <p v-if="errors.email" id="login-email-error" class="login-form__field-error">
          {{ errors.email }}
        </p>
      </div>

      <div class="login-form__field">
        <label class="login-form__label" for="login-password"> 비밀번호 </label>
        <div class="login-form__password">
          <input
            id="login-password"
            v-model="form.password"
            class="login-form__input login-form__input--password"
            :class="{ 'login-form__input--error': errors.password }"
            :type="isPasswordVisible ? 'text' : 'password'"
            autocomplete="current-password"
            placeholder="비밀번호를 입력해주세요."
            :aria-invalid="errors.password ? 'true' : 'false'"
            aria-describedby="login-password-error"
            @input="handleFieldInput('password')"
            @blur="handleFieldBlur('password')"
          />
          <button
            class="login-form__password-toggle"
            type="button"
            :aria-pressed="isPasswordVisible"
            @click="togglePasswordVisibility"
          >
            {{ isPasswordVisible ? '숨기기' : '보기' }}
          </button>
        </div>
        <p v-if="errors.password" id="login-password-error" class="login-form__field-error">
          {{ errors.password }}
        </p>
      </div>
    </section>

    <div class="login-form__options">
      <label class="login-form__remember">
        <input
          class="login-form__checkbox"
          type="checkbox"
          :checked="form.rememberMe"
          @change="handleRememberMeChange"
        />
        로그인 상태 유지
      </label>
      <button class="login-form__text-button" type="button" disabled>비밀번호 찾기</button>
    </div>

    <section class="login-form__actions" aria-label="로그인 실행">
      <button class="login-form__submit" type="submit">로그인</button>

      <button class="login-form__secondary" type="button" @click="handleSsafyLogin">
        싸피어스로 로그인
      </button>
    </section>
  </form>

  <footer class="login-form__footer">
    아직 계정이 없나요?
    <RouterLink class="login-form__link" :to="{ name: ROUTE_NAMES.AUTH_SIGNUP }">
      회원가입
    </RouterLink>
  </footer>
</template>

<style scoped lang="scss">
.login-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.login-form__error {
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-control);
  background: var(--color-error-soft);
  color: var(--color-error);
  font-size: 13px;
  font-weight: 600;
  line-height: 18px;
}

.login-form__fields,
.login-form__actions {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.login-form__actions {
  gap: var(--space-3);
}

.login-form__field {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.login-form__label {
  color: var(--color-text-primary);
  font-size: 14px;
  font-weight: 600;
  line-height: 20px;
}

.login-form__input {
  width: 100%;
  height: var(--button-height-standard);
  padding: 0 var(--space-4);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-primary);
  outline: none;
  transition:
    border-color 160ms ease,
    box-shadow 160ms ease;
}

.login-form__input:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 4px var(--color-primary-soft);
}

.login-form__input--error {
  border-color: var(--color-error);
}

.login-form__input--password {
  padding-right: 80px;
}

.login-form__password {
  position: relative;
}

.login-form__password-toggle {
  position: absolute;
  top: 50%;
  right: var(--space-2);
  height: 36px;
  padding: 0 var(--space-3);
  border: 0;
  border-radius: var(--radius-control);
  background: transparent;
  color: var(--color-text-secondary);
  font-size: 14px;
  font-weight: 600;
  transform: translateY(-50%);
  transition: background-color 160ms ease;
}

.login-form__password-toggle:hover {
  background: var(--color-surface-secondary);
}

.login-form__field-error {
  color: var(--color-error);
  font-size: 13px;
  line-height: 20px;
}

.login-form__options {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
}

.login-form__remember {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--color-text-primary);
  font-size: 14px;
  font-weight: 600;
  line-height: 20px;
}

.login-form__checkbox {
  width: 16px;
  height: 16px;
  accent-color: var(--color-primary);
}

.login-form__text-button {
  border: 0;
  background: transparent;
  color: var(--color-text-muted);
  font-size: 14px;
  font-weight: 600;
}

.login-form__submit,
.login-form__secondary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: var(--button-height-major);
  padding: 0 var(--space-5);
  border-radius: var(--radius-control);
  font-size: 15px;
  font-weight: 600;
  line-height: 20px;
  transition:
    background-color 160ms ease,
    border-color 160ms ease,
    color 160ms ease,
    transform 160ms ease;
}

.login-form__submit {
  border: 1px solid transparent;
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

.login-form__submit:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.login-form__submit:disabled {
  background: var(--color-surface-secondary);
  color: var(--color-text-muted);
}

.login-form__secondary {
  border: 1px solid var(--color-border-strong);
  background: var(--color-surface);
  color: var(--color-text-primary);
}

.login-form__secondary:hover {
  background: var(--color-surface-secondary);
}

.login-form__submit:focus-visible,
.login-form__secondary:focus-visible,
.login-form__password-toggle:focus-visible,
.login-form__text-button:focus-visible,
.login-form__link:focus-visible {
  outline: 3px solid var(--color-primary);
  outline-offset: 3px;
}

.login-form__submit:active:not(:disabled),
.login-form__secondary:active {
  transform: translateY(1px);
}

.login-form__footer {
  margin-top: var(--space-6);
  color: var(--color-text-secondary);
  font-size: 14px;
  line-height: 20px;
  text-align: center;
}

.login-form__link {
  color: var(--color-primary);
  font-weight: 700;
}

@media (max-width: 400px) {
  .login-form__options {
    align-items: flex-start;
    flex-direction: column;
    gap: var(--space-3);
  }
}
</style>
