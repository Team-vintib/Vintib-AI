<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { submitBusinessVerification } from '@/domains/biz/api/businessVerification'
import BusinessCertificateUploader from '@/domains/biz/components/BusinessCertificateUploader.vue'
import { BUSINESS_REGISTRATION_NUMBER_LENGTH } from '@/domains/biz/constants/businessVerification'
import { useBusinessVerificationStore } from '@/domains/biz/stores/businessVerificationStore'
import { useAuthStore } from '@/domains/auth/stores/authStore'
import BaseButton from '@/domains/onboard/components/BaseButton.vue'
import { normalizeApiError } from '@/shared/api/http'
import { ROUTE_NAMES } from '@/shared/constants/routes'

const router = useRouter()
const authStore = useAuthStore()
const businessVerificationStore = useBusinessVerificationStore()

const businessRegistrationNumber = ref('')
const businessName = ref('')
const representativeName = ref('')
const certificateFile = ref<File | null>(null)
const certificateSelectionError = ref('')
const isSubmitting = ref(false)
const submitError = ref('')

const touched = reactive({
  businessRegistrationNumber: false,
  businessName: false,
  representativeName: false,
  certificateFile: false,
})

const isBusinessRegistrationNumberValid = computed(
  () =>
    businessRegistrationNumber.value.length === BUSINESS_REGISTRATION_NUMBER_LENGTH &&
    /^\d+$/.test(businessRegistrationNumber.value),
)
const isBusinessNameValid = computed(() => businessName.value.trim().length > 0)
const isRepresentativeNameValid = computed(() => representativeName.value.trim().length > 0)
const isCertificateValid = computed(
  () =>
    certificateFile.value !== null &&
    certificateFile.value.type.startsWith('image/') &&
    certificateSelectionError.value === '',
)
const isFormValid = computed(
  () =>
    isBusinessRegistrationNumberValid.value &&
    isBusinessNameValid.value &&
    isRepresentativeNameValid.value &&
    isCertificateValid.value,
)

const businessRegistrationNumberError = computed(() => {
  if (!touched.businessRegistrationNumber) {
    return ''
  }

  if (!businessRegistrationNumber.value) {
    return '사업자등록번호를 입력해 주세요.'
  }

  if (!isBusinessRegistrationNumberValid.value) {
    return '사업자등록번호는 숫자 10자리로 입력해 주세요.'
  }

  return ''
})

const businessNameError = computed(() => {
  if (!touched.businessName || isBusinessNameValid.value) {
    return ''
  }

  return '상호명을 입력해 주세요.'
})

const representativeNameError = computed(() => {
  if (!touched.representativeName || isRepresentativeNameValid.value) {
    return ''
  }

  return '대표자명을 입력해 주세요.'
})

const certificateError = computed(() => {
  if (certificateSelectionError.value) {
    return certificateSelectionError.value
  }

  if (touched.certificateFile && !isCertificateValid.value) {
    return '사업자등록증 이미지를 등록해 주세요.'
  }

  return ''
})

const submitDescription = computed(() => {
  if (isSubmitting.value) {
    return '사업자 정보를 제출하고 있습니다. 잠시만 기다려 주세요.'
  }

  if (isFormValid.value) {
    return '제출하면 사업자 인증 확인 대기 화면으로 이동합니다.'
  }

  return '모든 필수 정보가 유효해야 제출할 수 있습니다.'
})

const handleBusinessRegistrationNumberInput = (event: Event) => {
  const inputElement = event.currentTarget as HTMLInputElement
  const normalizedValue = inputElement.value
    .replace(/\D/g, '')
    .slice(0, BUSINESS_REGISTRATION_NUMBER_LENGTH)

  businessRegistrationNumber.value = normalizedValue
  inputElement.value = normalizedValue
  submitError.value = ''
}

const handleCertificateValidationError = (message: string) => {
  touched.certificateFile = true
  certificateSelectionError.value = message
  submitError.value = ''
}

const handleCertificateUpdate = (file: File | null) => {
  certificateFile.value = file
  touched.certificateFile = true
  certificateSelectionError.value = ''
  submitError.value = ''
}

const goBack = () => {
  if (window.history.length > 1) {
    router.back()
    return
  }

  // 직접 진입(히스토리 없음) 시엔 온보딩 전 단계(회원 유형 선택)로 돌아간다.
  void router.push({ name: ROUTE_NAMES.ONBOARD_MEMBER_TYPE })
}

const handleSubmit = async () => {
  if (isSubmitting.value) {
    return
  }

  touched.businessRegistrationNumber = true
  touched.businessName = true
  touched.representativeName = true
  touched.certificateFile = true
  submitError.value = ''

  if (!isFormValid.value || !certificateFile.value) {
    return
  }

  isSubmitting.value = true

  try {
    const userId = authStore.user?.id

    if (!userId) {
      submitError.value = '로그인 후 사업자 인증을 진행해 주세요.'
      return
    }

    const response = await submitBusinessVerification(userId, {
      businessRegistrationNumber: businessRegistrationNumber.value,
      businessName: businessName.value.trim(),
      representativeName: representativeName.value.trim(),
      certificate: certificateFile.value,
    })

    if (!response.success || !response.data) {
      submitError.value = response.error?.message || '사업자 정보를 제출하지 못했습니다. 잠시 후 다시 시도해 주세요.'
      return
    }

    businessVerificationStore.setSubmission({
      id: userId,
      businessRegistrationNumber: businessRegistrationNumber.value,
      businessName: businessName.value.trim(),
      representativeName: representativeName.value.trim(),
      certificateFile: certificateFile.value,
      status: response.data.status,
      submittedAt: new Date(response.data.submittedAt),
    })

    await router.push({ name: ROUTE_NAMES.BIZ_VERIFY_PENDING })
  } catch (error) {
    const apiError = normalizeApiError(error)
    submitError.value =
      apiError.code === 'UNKNOWN_ERROR' && error instanceof Error ? error.message : apiError.message
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <main class="business-verification">
    <section
      class="business-verification__container"
      aria-labelledby="business-verification-title"
    >
      <header class="business-verification__header">
        <span class="business-verification__icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" focusable="false">
            <path d="M12 3.5 19 6v5.4c0 4.3-2.6 7.4-7 9.1-4.4-1.7-7-4.8-7-9.1V6l7-2.5Z" />
            <path d="m9 12 2 2 4-4" />
          </svg>
        </span>
        <p class="business-verification__eyebrow">마이페이지 사업자 인증</p>
        <h1 id="business-verification-title">사업자 인증하기</h1>
        <p>사업자 회원 이용을 위해 정보를 제출해 주세요.</p>
      </header>

      <form class="business-form" novalidate @submit.prevent="handleSubmit">
        <section class="business-form__section" aria-labelledby="business-details-title">
          <div class="business-form__section-header">
            <div>
              <h2 id="business-details-title">사업자 정보 입력</h2>
              <p>사업자등록증에 기재된 정보와 동일하게 입력해 주세요.</p>
            </div>
            <span>필수 입력</span>
          </div>

          <div class="business-form__fields">
            <label class="business-field business-field--full">
              <span class="business-field__label">
                사업자등록번호
                <span aria-hidden="true">*</span>
              </span>
              <input
                :value="businessRegistrationNumber"
                type="text"
                inputmode="numeric"
                autocomplete="off"
                maxlength="10"
                placeholder="사업자등록번호를 입력해 주세요"
                :disabled="isSubmitting"
                :aria-invalid="businessRegistrationNumberError ? 'true' : 'false'"
                aria-describedby="business-registration-number-help business-registration-number-error"
                @input="handleBusinessRegistrationNumberInput"
                @blur="touched.businessRegistrationNumber = true"
              />
              <span id="business-registration-number-help" class="business-field__help">
                하이픈 없이 숫자 10자리를 입력해 주세요.
              </span>
              <span
                v-if="businessRegistrationNumberError"
                id="business-registration-number-error"
                class="business-field__error"
                role="alert"
              >
                {{ businessRegistrationNumberError }}
              </span>
            </label>

            <label class="business-field">
              <span class="business-field__label">
                상호명
                <span aria-hidden="true">*</span>
              </span>
              <input
                v-model="businessName"
                type="text"
                autocomplete="organization"
                placeholder="상호명을 입력해 주세요"
                :disabled="isSubmitting"
                :aria-invalid="businessNameError ? 'true' : 'false'"
                aria-describedby="business-name-error"
                @input="submitError = ''"
                @blur="touched.businessName = true"
              />
              <span
                v-if="businessNameError"
                id="business-name-error"
                class="business-field__error"
                role="alert"
              >
                {{ businessNameError }}
              </span>
            </label>

            <label class="business-field">
              <span class="business-field__label">
                대표자명
                <span aria-hidden="true">*</span>
              </span>
              <input
                v-model="representativeName"
                type="text"
                autocomplete="name"
                placeholder="대표자명을 입력해 주세요"
                :disabled="isSubmitting"
                :aria-invalid="representativeNameError ? 'true' : 'false'"
                aria-describedby="representative-name-error"
                @input="submitError = ''"
                @blur="touched.representativeName = true"
              />
              <span
                v-if="representativeNameError"
                id="representative-name-error"
                class="business-field__error"
                role="alert"
              >
                {{ representativeNameError }}
              </span>
            </label>
          </div>
        </section>

        <section class="business-form__section" aria-labelledby="certificate-title">
          <div class="business-form__section-header">
            <div>
              <h2 id="certificate-title">사업자등록증</h2>
              <p>확인 가능한 사업자등록증 이미지를 등록해 주세요.</p>
            </div>
            <span>필수 등록</span>
          </div>

          <BusinessCertificateUploader
            :model-value="certificateFile"
            :disabled="isSubmitting"
            :error-message="certificateError"
            @update:model-value="handleCertificateUpdate"
            @validation-error="handleCertificateValidationError"
          />
        </section>

        <aside class="business-privacy-notice" aria-label="개인정보 이용 안내">
          <span class="business-privacy-notice__icon" aria-hidden="true">i</span>
          <p>
            입력하신 정보는 회원 식별 및 서비스 제공을 위한 용도로만 사용됩니다.
            개인정보 보호 정책에 따라 안전하게 보관되니 안심하고 입력해 주세요.
          </p>
        </aside>

        <p v-if="submitError" class="business-form__submit-error" role="alert">
          {{ submitError }}
        </p>

        <div class="business-form__actions">
          <BaseButton
            class="business-form__action"
            type="button"
            variant="secondary"
            size="major"
            :disabled="isSubmitting"
            @click="goBack"
          >
            이전 단계
          </BaseButton>

          <BaseButton
            class="business-form__action"
            type="submit"
            size="major"
            :disabled="!isFormValid || isSubmitting"
            aria-describedby="business-submit-description"
          >
            {{ isSubmitting ? '제출 중' : '사업자 인증하기' }}
          </BaseButton>
        </div>
        <p id="business-submit-description" class="business-form__submit-description">
          {{ submitDescription }}
        </p>
      </form>
    </section>
  </main>
</template>

<style scoped lang="scss">
.business-verification {
  min-height: 100vh;
  padding: var(--space-12);
  background: var(--color-page);
}

.business-verification__container {
  width: 100%;
  max-width: 880px;
  margin: 0 auto;
}

.business-verification__header {
  display: flex;
  align-items: center;
  flex-direction: column;
  text-align: center;
}

.business-verification__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: var(--color-primary-soft);
  color: var(--color-primary);
}

.business-verification__icon svg {
  width: 26px;
  height: 26px;
  fill: none;
  stroke: currentcolor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.8;
}

.business-verification__eyebrow {
  margin-top: var(--space-4);
  color: var(--color-primary);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-snug);
}

.business-verification__header h1 {
  margin-top: var(--space-2);
  font-size: 36px;
  font-weight: var(--font-weight-bold);
  line-height: 48px;
}

.business-verification__header > p:last-child {
  margin-top: var(--space-2);
  color: var(--color-text-secondary);
  line-height: var(--line-height-body);
}

.business-form {
  padding: var(--space-8);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  margin-top: var(--space-10);
  background: var(--color-surface);
}

.business-form__section + .business-form__section {
  padding-top: var(--space-8);
  border-top: 1px solid var(--color-border);
  margin-top: var(--space-8);
}

.business-form__section-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
  margin-bottom: var(--space-6);
}

.business-form__section-header h2 {
  font-size: var(--font-size-lg-plus);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-lg-plus);
}

.business-form__section-header p {
  margin-top: var(--space-1);
  color: var(--color-text-secondary);
  font-size: var(--font-size-caption);
  line-height: var(--line-height-snug);
}

.business-form__section-header > span {
  flex: 0 0 auto;
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-badge);
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-xs);
}

.business-form__fields {
  display: grid;
  gap: var(--space-5);
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.business-field {
  display: flex;
  min-width: 0;
  flex-direction: column;
}

.business-field--full {
  grid-column: 1 / -1;
}

.business-field__label {
  margin-bottom: var(--space-2);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-control);
}

.business-field__label > span {
  color: var(--color-error);
}

.business-field input {
  width: 100%;
  height: var(--button-height-standard);
  padding: 0 var(--space-4);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-primary);
  font: inherit;
  font-size: var(--font-size-body);
  transition:
    border-color var(--transition-base),
    box-shadow var(--transition-base);
}

.business-field input::placeholder {
  color: var(--color-text-muted);
}

.business-field input:focus {
  border-color: var(--color-primary);
  box-shadow: none;
  outline: none;
}

.business-field input[aria-invalid='true'] {
  border-color: var(--color-error);
}

.business-field input:disabled {
  background: var(--color-surface-secondary);
  cursor: not-allowed;
  opacity: 0.72;
}

.business-field__help,
.business-field__error {
  margin-top: var(--space-2);
  font-size: var(--font-size-caption);
  line-height: var(--line-height-snug);
}

.business-field__help {
  color: var(--color-text-muted);
}

.business-field__error {
  color: var(--color-error);
}

.business-privacy-notice {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  margin-top: var(--space-8);
  background: var(--color-surface-secondary);
}

.business-privacy-notice__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border: 1px solid var(--color-text-secondary);
  border-radius: 50%;
  color: var(--color-text-secondary);
  flex: 0 0 auto;
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-bold);
}

.business-privacy-notice p {
  color: var(--color-text-secondary);
  font-size: var(--font-size-caption);
  line-height: var(--line-height-control);
}

.business-form__actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  margin-top: var(--space-6);
}

.business-form__action {
  min-width: 160px;
}

.business-form__submit-error {
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-control);
  margin-top: var(--space-6);
  background: var(--color-error-soft);
  color: var(--color-error);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-control);
}

.business-form__submit-error + .business-form__actions {
  margin-top: var(--space-4);
}

.business-form__submit-description {
  margin-top: var(--space-2);
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  line-height: var(--line-height-snug);
  text-align: center;
}

@media (max-width: 720px) {
  .business-verification {
    padding: var(--space-8) var(--space-4);
  }

  .business-form {
    padding: var(--space-5);
  }

  .business-form__fields {
    grid-template-columns: 1fr;
  }

  .business-field--full {
    grid-column: auto;
  }

  .business-form__actions {
    align-items: stretch;
    flex-direction: column;
  }

  .business-form__action {
    width: 100%;
  }
}
</style>
