<script setup lang="ts">
import axios from 'axios'
import { computed, nextTick, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/domains/auth/stores/authStore'
import { saveOnboardingTryOnProfile } from '@/domains/onboard/api/onboarding'
import BaseField from '@/domains/onboard/components/BaseField.vue'
import BaseInput from '@/domains/onboard/components/BaseInput.vue'
import FullBodyPhotoUploader from '@/domains/onboard/components/FullBodyPhotoUploader.vue'
import OnboardingLayout from '@/domains/onboard/components/OnboardingLayout.vue'
import { ROUTE_NAMES } from '@/shared/constants/routes'

import type { SaveOnboardingTryOnProfileRequest } from '@/domains/onboard/api/onboarding'
import type { ApiErrorBody as ApiError, ApiResponse } from '@/shared/types/api.types'

type BodyFieldId = 'heightCm' | 'weightKg' | 'chest' | 'waist' | 'hip'
type BodyForm = Record<BodyFieldId, string>
type BodyFieldState = Record<BodyFieldId, boolean>
type BodyFieldErrors = Record<BodyFieldId, string>

interface BodyField {
  id: BodyFieldId
  label: string
  unit?: string
  placeholder: string
}

const bodyFields: BodyField[] = [
  { id: 'heightCm', label: '키', unit: 'cm', placeholder: '예: 170' },
  { id: 'weightKg', label: '몸무게', unit: 'kg', placeholder: '예: 60' },
  { id: 'chest', label: '가슴', placeholder: '선택 입력' },
  { id: 'waist', label: '허리', placeholder: '선택 입력' },
  { id: 'hip', label: '엉덩이', placeholder: '선택 입력' },
]

const positiveIntegerPattern = /^[1-9]\d*$/
const invalidNumberMessage = '0보다 큰 정수로 입력해 주세요.'
const bodyForm = reactive<BodyForm>({
  heightCm: '',
  weightKg: '',
  chest: '',
  waist: '',
  hip: '',
})
const touched = reactive<BodyFieldState>({
  heightCm: false,
  weightKg: false,
  chest: false,
  waist: false,
  hip: false,
})
const fieldErrors = reactive<BodyFieldErrors>({
  heightCm: '',
  weightKg: '',
  chest: '',
  waist: '',
  hip: '',
})
const selectedFullBodyPhoto = ref<File | null>(null)
const isSubmitting = ref(false)
const submitError = ref('')
const router = useRouter()
const authStore = useAuthStore()

const completedMeasurementCount = computed(
  () => bodyFields.filter((field) => bodyForm[field.id].trim()).length,
)

const hasTryOnData = computed(
  () => Boolean(selectedFullBodyPhoto.value) || completedMeasurementCount.value > 0,
)

const validateField = (fieldId: BodyFieldId) => {
  const value = bodyForm[fieldId].trim()

  if (!value) {
    fieldErrors[fieldId] = ''
    return true
  }

  if (!positiveIntegerPattern.test(value)) {
    fieldErrors[fieldId] = invalidNumberMessage
    return false
  }

  fieldErrors[fieldId] = ''
  return true
}

const handleFieldInput = (fieldId: BodyFieldId, value: string) => {
  bodyForm[fieldId] = value
  submitError.value = ''

  if (touched[fieldId]) {
    validateField(fieldId)
  }
}

const handleFieldBlur = (fieldId: BodyFieldId) => {
  touched[fieldId] = true
  validateField(fieldId)
}

const focusField = async (fieldId: BodyFieldId) => {
  await nextTick()
  document.getElementById(fieldId)?.focus()
}

const validateForm = async () => {
  let firstInvalidField: BodyFieldId | null = null

  bodyFields.forEach((field) => {
    touched[field.id] = true

    if (!validateField(field.id) && !firstInvalidField) {
      firstInvalidField = field.id
    }
  })

  if (firstInvalidField) {
    await focusField(firstInvalidField)
    return false
  }

  return true
}

const goToMemberType = async () => {
  await router.push({ name: ROUTE_NAMES.ONBOARD_MEMBER_TYPE })
}

const handlePrevious = async () => {
  if (isSubmitting.value) {
    return
  }

  await router.push({ name: ROUTE_NAMES.ONBOARD_INTERESTS })
}

const handleSkip = async () => {
  if (isSubmitting.value) {
    return
  }

  await goToMemberType()
}

const handlePhotoChange = (file: File | null) => {
  selectedFullBodyPhoto.value = file
  submitError.value = ''
}

const createSaveRequest = (): SaveOnboardingTryOnProfileRequest => {
  const request: SaveOnboardingTryOnProfileRequest = {}

  if (selectedFullBodyPhoto.value) {
    request.bodyPhoto = selectedFullBodyPhoto.value
  }

  bodyFields.forEach((field) => {
    const value = bodyForm[field.id].trim()

    if (value) {
      request[field.id] = value
    }
  })

  return request
}

const isBodyFieldId = (field: string): field is BodyFieldId =>
  bodyFields.some((bodyField) => bodyField.id === field)

const applyApiError = async (apiError: ApiError | null) => {
  let firstInvalidField: BodyFieldId | null = null
  let unmappedFieldError = ''

  apiError?.errors?.forEach((error) => {
    if (isBodyFieldId(error.field)) {
      touched[error.field] = true
      fieldErrors[error.field] = error.reason
      firstInvalidField ??= error.field
      return
    }

    unmappedFieldError ||= error.reason
  })

  submitError.value =
    unmappedFieldError ||
    apiError?.message ||
    'AI 시착 정보를 저장하지 못했습니다. 잠시 후 다시 시도해 주세요.'

  if (firstInvalidField) {
    await focusField(firstInvalidField)
  }
}

const handleSave = async () => {
  if (isSubmitting.value || !(await validateForm())) {
    return
  }

  submitError.value = ''

  if (!hasTryOnData.value) {
    await goToMemberType()
    return
  }

  isSubmitting.value = true

  try {
    const response = await saveOnboardingTryOnProfile(createSaveRequest(), {
      userId: authStore.user?.id,
    })

    if (!response.success) {
      await applyApiError(response.error ?? null)
      return
    }

    await goToMemberType()
  } catch (error: unknown) {
    if (axios.isAxiosError<ApiResponse<unknown>>(error)) {
      if (!error.response) {
        submitError.value =
          '서버에 연결하지 못했습니다. 네트워크 상태를 확인하고 다시 시도해 주세요.'
      } else {
        await applyApiError(error.response.data?.error ?? null)
      }
    } else {
      await applyApiError(null)
    }
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <OnboardingLayout
    :current-step="3"
    title="AI 시착 정보를 등록해 주세요"
    description="전신 사진과 신체 정보를 등록하면 더 정확한 가상 시착 결과를 확인할 수 있습니다."
    show-skip
    :previous-disabled="isSubmitting"
    :skip-disabled="isSubmitting"
    :next-disabled="isSubmitting"
    :next-label="isSubmitting ? '저장 중' : '다음 단계'"
    @previous="handlePrevious"
    @skip="handleSkip"
    @next="handleSave"
  >
    <div class="try-on-registration">
      <header class="try-on-registration__header">
        <div>
          <h2 class="try-on-registration__title">AI 시착 정보</h2>
          <p class="try-on-registration__description">
            모든 항목은 선택 사항이며 가입 후 마이페이지에서 변경할 수 있습니다.
          </p>
        </div>

        <span class="try-on-registration__optional">선택 사항</span>
      </header>

      <section class="registration-section" aria-labelledby="full-body-photo-title">
        <div class="registration-section__heading">
          <div>
            <h3 id="full-body-photo-title" class="registration-section__title">전신 사진</h3>
            <p class="registration-section__description">
              AI 시착에 사용할 정면 전신 사진을 등록해 주세요.
            </p>
          </div>

          <span
            class="registration-section__status"
            :class="{ 'registration-section__status--complete': selectedFullBodyPhoto }"
          >
            {{ selectedFullBodyPhoto ? '등록 완료' : '등록 전' }}
          </span>
        </div>

        <div class="photo-registration">
          <FullBodyPhotoUploader
            :model-value="selectedFullBodyPhoto"
            :disabled="isSubmitting"
            @update:model-value="handlePhotoChange"
          />

          <aside class="photo-guide" aria-labelledby="photo-guide-title">
            <div class="photo-guide__heading">
              <span class="photo-guide__icon" aria-hidden="true">i</span>
              <h4 id="photo-guide-title">사진 촬영 가이드</h4>
            </div>

            <ul class="photo-guide__list">
              <li>머리부터 발끝까지 전신이 모두 보이도록 촬영해 주세요.</li>
              <li>카메라 정면을 바라보고 몸을 바르게 세워 주세요.</li>
              <li>몸의 형태가 잘 보이는 옷을 착용하는 것을 권장합니다.</li>
            </ul>

            <p class="photo-guide__notice">전신 사진이 없으면 AI 시착 기능을 이용할 수 없습니다.</p>
          </aside>
        </div>
      </section>

      <section
        class="registration-section registration-section--measurements"
        aria-labelledby="body-measurements-title"
      >
        <div class="registration-section__heading">
          <div>
            <h3 id="body-measurements-title" class="registration-section__title">신체 정보</h3>
            <p id="body-measurements-status" class="registration-section__description">
              실제 치수에 가까운 정보를 입력할수록 시착 결과의 정확도가 높아집니다.
            </p>
          </div>

          <span
            class="registration-section__status"
            :class="{ 'registration-section__status--complete': completedMeasurementCount > 0 }"
          >
            {{
              completedMeasurementCount > 0
                ? `${completedMeasurementCount}개 입력`
                : '선택 입력'
            }}
          </span>
        </div>

        <fieldset
          class="body-fields"
          aria-describedby="body-measurements-status body-fields-format-notice"
        >
          <legend class="visually-hidden">신체 정보 입력 항목</legend>

          <BaseField
            v-for="field in bodyFields"
            :id="field.id"
            :key="field.id"
            class="body-field"
            :label="field.label"
            :error="fieldErrors[field.id]"
          >
            <template #default="{ descriptionId, isInvalid }">
              <div class="body-field__control">
                <BaseInput
                  :id="field.id"
                  class="body-field__input"
                  :class="{ 'body-field__input--with-unit': field.unit }"
                  :model-value="bodyForm[field.id]"
                  :placeholder="field.placeholder"
                  inputmode="numeric"
                  :disabled="isSubmitting"
                  :invalid="isInvalid"
                  :described-by="descriptionId"
                  @update:model-value="handleFieldInput(field.id, $event)"
                  @blur="handleFieldBlur(field.id)"
                />

                <span v-if="field.unit" class="body-field__unit" aria-hidden="true">
                  {{ field.unit }}
                </span>
              </div>
            </template>
          </BaseField>
        </fieldset>

        <p id="body-fields-format-notice" class="body-fields__notice" role="note">
          입력하지 않아도 괜찮습니다. 입력할 경우 0보다 큰 정수로 작성해 주세요.
        </p>

        <p
          v-if="submitError"
          class="try-on-registration__submit-error"
          role="alert"
          aria-live="assertive"
        >
          {{ submitError }}
        </p>
      </section>
    </div>
  </OnboardingLayout>
</template>

<style scoped lang="scss">
.try-on-registration {
  width: 100%;
}

.try-on-registration__header,
.registration-section__heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
}

.try-on-registration__header {
  margin-bottom: var(--space-10);
}

.try-on-registration__title {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-2xl-loose);
}

.try-on-registration__description,
.registration-section__description {
  margin-top: var(--space-2);
  color: var(--color-text-secondary);
}

.try-on-registration__optional,
.registration-section__status {
  flex: 0 0 auto;
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-chip);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-control);
}

.try-on-registration__optional {
  background: var(--color-ai-soft);
  color: var(--color-ai);
}

.registration-section__status {
  background: var(--color-surface-secondary);
  color: var(--color-text-secondary);
}

.registration-section__status--complete {
  background: var(--color-ai-soft);
  color: var(--color-ai);
}

.registration-section + .registration-section {
  padding-top: var(--space-10);
  border-top: 1px solid var(--color-border);
  margin-top: var(--space-10);
}

.registration-section__title {
  font-size: var(--font-size-md-plus);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-body);
}

.registration-section__description {
  font-size: var(--font-size-caption);
  line-height: var(--line-height-control);
}

.photo-registration {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(320px, 0.85fr);
  gap: var(--space-6);
  margin-top: var(--space-5);
}

.photo-guide {
  padding: var(--space-6);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
}

.photo-guide__heading {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  font-size: var(--font-size-body);
  font-weight: var(--font-weight-semibold);
}

.photo-guide__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--color-ai-soft);
  color: var(--color-ai);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-bold);
}

.photo-guide__list {
  display: grid;
  gap: var(--space-3);
  margin-top: var(--space-5);
  color: var(--color-text-secondary);
  font-size: var(--font-size-button-small);
  line-height: var(--line-height-relaxed);
  list-style: none;
}

.photo-guide__list li {
  position: relative;
  padding-left: var(--space-5);
}

.photo-guide__list li::before {
  position: absolute;
  top: 8px;
  left: 0;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-ai);
  content: '';
}

.photo-guide__notice,
.body-fields__notice {
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-control);
  background: var(--color-ai-soft);
  color: var(--color-ai);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-control);
}

.photo-guide__notice {
  margin-top: var(--space-6);
}

.body-fields {
  display: grid;
  min-width: 0;
  padding: 0;
  border: 0;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-5);
  margin-top: var(--space-5);
}

.body-field {
  min-width: 0;
}

.body-field__control {
  position: relative;
}

.body-field__input--with-unit {
  padding-right: var(--space-12);
}

.body-field__unit {
  position: absolute;
  top: 50%;
  right: var(--space-4);
  color: var(--color-text-muted);
  font-size: var(--font-size-caption);
  transform: translateY(-50%);
  pointer-events: none;
}

.body-fields__notice {
  margin-top: var(--space-5);
}

.try-on-registration__submit-error {
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-control);
  margin-top: var(--space-5);
  background: var(--color-error-soft);
  color: var(--color-error);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-control);
}

.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  overflow: hidden;
  border: 0;
  margin: -1px;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
}

@media (max-width: 980px) {
  .photo-registration {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 820px) {
  .body-fields {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 560px) {
  .try-on-registration__header,
  .registration-section__heading {
    flex-direction: column;
  }

  .photo-guide {
    padding: var(--space-5);
  }

  .body-fields {
    width: 100%;
    grid-template-columns: 1fr;
  }
}
</style>
