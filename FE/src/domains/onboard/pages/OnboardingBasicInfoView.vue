<script setup lang="ts">
import axios from 'axios'
import { nextTick, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/domains/auth/stores/authStore'
import { openPostcodeSearch } from '@/domains/onboard/api/postcode'
import { saveOnboardingBasicInfo } from '@/domains/onboard/api/onboarding'
import BaseButton from '@/domains/onboard/components/BaseButton.vue'
import BaseField from '@/domains/onboard/components/BaseField.vue'
import BaseInput from '@/domains/onboard/components/BaseInput.vue'
import OnboardingLayout from '@/domains/onboard/components/OnboardingLayout.vue'
import { ROUTE_NAMES } from '@/shared/constants/routes'

import type { OnboardingGender } from '@/domains/onboard/api/onboarding'
import type { ApiErrorBody as ApiError, ApiResponse } from '@/shared/types/api.types'

type Gender = '' | OnboardingGender
type FormField = 'nickname' | 'gender' | 'phoneNumber' | 'address' | 'detailAddress'
type TextFormField = Exclude<FormField, 'gender'>

interface BasicInfoForm {
  nickname: string
  gender: Gender
  phoneNumber: string
  zonecode: string
  address: string
  detailAddress: string
}

const form = reactive<BasicInfoForm>({
  nickname: '',
  gender: '',
  phoneNumber: '',
  zonecode: '',
  address: '',
  detailAddress: '',
})

const errors = reactive<Record<FormField, string>>({
  nickname: '',
  gender: '',
  phoneNumber: '',
  address: '',
  detailAddress: '',
})

const touched = reactive<Record<FormField, boolean>>({
  nickname: false,
  gender: false,
  phoneNumber: false,
  address: false,
  detailAddress: false,
})

const isAddressSearchLoading = ref(false)
const addressSearchError = ref('')
const isSubmitting = ref(false)
const submitError = ref('')
const detailAddressInput = ref<InstanceType<typeof BaseInput> | null>(null)
const router = useRouter()
const authStore = useAuthStore()

const genderOptions: { value: Exclude<Gender, ''>; label: string }[] = [
  { value: 'MALE', label: '남성' },
  { value: 'FEMALE', label: '여성' },
]

const fieldOrder: FormField[] = ['nickname', 'gender', 'phoneNumber', 'address', 'detailAddress']

const fieldIds: Record<FormField, string> = {
  nickname: 'nickname',
  gender: 'gender-group',
  phoneNumber: 'phone-number',
  address: 'address',
  detailAddress: 'detail-address',
}

const apiFieldMap: Record<string, FormField> = {
  nickname: 'nickname',
  gender: 'gender',
  phoneNumber: 'phoneNumber',
  postalCode: 'address',
  address: 'address',
  detailAddress: 'detailAddress',
}

const nicknamePattern = /^[가-힣A-Za-z0-9]{2,10}$/
const phonePattern = /^0\d{1,2}-?\d{3,4}-?\d{4}$/

const getValidationMessage = (field: FormField) => {
  if (field === 'nickname') {
    const nickname = form.nickname.trim()

    if (!nickname) {
      return '닉네임을 입력해 주세요.'
    }

    if (!nicknamePattern.test(nickname)) {
      return '특수문자 제외 2~10자 이내로 입력해 주세요.'
    }
  }

  if (field === 'gender' && !form.gender) {
    return '성별을 선택해 주세요.'
  }

  if (field === 'phoneNumber') {
    const phoneNumber = form.phoneNumber.trim()

    if (!phoneNumber) {
      return '전화번호를 입력해 주세요.'
    }

    if (!phonePattern.test(phoneNumber)) {
      return '전화번호 형식을 확인해 주세요. 예: 01012345678'
    }
  }

  if (field === 'address' && !form.address.trim()) {
    return '주소를 입력하거나 검색해 주세요.'
  }

  if (field === 'detailAddress' && !form.detailAddress.trim()) {
    return '상세 주소를 입력해 주세요.'
  }

  return ''
}

const validateField = (field: FormField) => {
  errors[field] = getValidationMessage(field)
  return !errors[field]
}

const handleFieldBlur = (field: FormField) => {
  touched[field] = true

  if (field !== 'gender') {
    form[field] = form[field].trim()
  }

  validateField(field)
}

const handleTextUpdate = (field: TextFormField, input: string) => {
  form[field] = field === 'phoneNumber' ? input.replace(/\D/g, '').slice(0, 11) : input
  submitError.value = ''

  if (touched[field]) {
    validateField(field)
  }
}

const handleGenderChange = () => {
  touched.gender = true
  submitError.value = ''
  validateField('gender')
}

const handleAddressSearch = async () => {
  if (isAddressSearchLoading.value) {
    return
  }

  isAddressSearchLoading.value = true
  addressSearchError.value = ''

  try {
    await openPostcodeSearch(async (result) => {
      form.zonecode = result.zonecode
      form.address = result.address
      touched.address = true
      validateField('address')
      submitError.value = ''

      await nextTick()
      detailAddressInput.value?.focus()
    })
  } catch {
    addressSearchError.value =
      '주소 검색 서비스를 불러오지 못했습니다. 직접 입력하거나 다시 시도해 주세요.'
  } finally {
    isAddressSearchLoading.value = false
  }
}

const focusField = async (field: FormField) => {
  await nextTick()
  document.getElementById(fieldIds[field])?.focus()
}

const applyApiError = async (apiError: ApiError | null) => {
  if (!apiError) {
    submitError.value = '기본 정보를 저장하지 못했습니다. 잠시 후 다시 시도해 주세요.'
    return
  }

  const mappedFields: FormField[] = []
  const unmappedReasons: string[] = []

  apiError.errors?.forEach((fieldError) => {
    const field = apiFieldMap[fieldError.field]

    if (!field) {
      unmappedReasons.push(fieldError.reason)
      return
    }

    touched[field] = true
    errors[field] = fieldError.reason
    mappedFields.push(field)
  })

  if (unmappedReasons.length > 0) {
    submitError.value = unmappedReasons.join(' ')
  } else if (mappedFields.length === 0) {
    submitError.value = apiError.message || '기본 정보를 저장하지 못했습니다.'
  }

  const firstInvalidField = fieldOrder.find((field) => mappedFields.includes(field))

  if (firstInvalidField) {
    await focusField(firstInvalidField)
  }
}

const handleSubmit = async () => {
  if (isSubmitting.value) {
    return
  }

  submitError.value = ''

  const isValid = fieldOrder
    .map((field) => {
      touched[field] = true
      return validateField(field)
    })
    .every(Boolean)

  if (!isValid) {
    const firstInvalidField = fieldOrder.find((field) => errors[field])

    await nextTick()

    if (firstInvalidField) {
      await focusField(firstInvalidField)
    }

    return
  }

  form.nickname = form.nickname.trim()
  form.phoneNumber = form.phoneNumber.trim()
  form.address = form.address.trim()
  form.detailAddress = form.detailAddress.trim()

  if (!form.gender) {
    return
  }

  isSubmitting.value = true

  try {
    const response = await saveOnboardingBasicInfo({
      nickname: form.nickname,
      gender: form.gender,
      phoneNumber: form.phoneNumber,
      postalCode: form.zonecode || null,
      address: form.address,
      detailAddress: form.detailAddress,
    }, {
      userId: authStore.user?.id,
    })

    if (!response.success) {
      await applyApiError(response.error ?? null)
      return
    }

    await router.push({ name: ROUTE_NAMES.ONBOARD_INTERESTS })
  } catch (error: unknown) {
    if (axios.isAxiosError<ApiResponse<unknown>>(error)) {
      if (!error.response) {
        submitError.value =
          '서버에 연결하지 못했습니다. 네트워크 상태를 확인한 뒤 다시 시도해 주세요.'
      } else {
        await applyApiError(error.response.data?.error ?? null)
      }
    } else {
      submitError.value = '기본 정보를 저장하지 못했습니다. 잠시 후 다시 시도해 주세요.'
    }
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <OnboardingLayout
    :current-step="1"
    title="기본 정보를 입력해 주세요"
    description="원활한 서비스 이용을 위해 기본 회원 정보를 등록해 주세요."
    :previous-disabled="true"
    :next-disabled="isSubmitting"
    :next-label="isSubmitting ? '저장 중' : '다음 단계'"
    @next="handleSubmit"
  >
    <form
      class="basic-info-form"
      novalidate
      aria-labelledby="basic-info-section-title"
      @submit.prevent="handleSubmit"
    >
      <header class="basic-info-form__header">
        <h2 id="basic-info-section-title" class="basic-info-form__title">기본 정보</h2>

        <p class="basic-info-form__description">
          입력하신 정보는 회원 식별 및 서비스 제공을 위한 용도로만 사용됩니다.
        </p>
      </header>

      <div class="basic-info-form__grid">
        <BaseField
          id="nickname"
          label="닉네임"
          required
          hint="한글, 영문, 숫자로 2~10자 이내로 입력해 주세요."
          :error="errors.nickname"
          v-slot="{ descriptionId, isInvalid }"
        >
          <BaseInput
            id="nickname"
            :model-value="form.nickname"
            placeholder="사용할 닉네임을 입력해 주세요"
            autocomplete="nickname"
            :maxlength="10"
            required
            :invalid="isInvalid"
            :described-by="descriptionId"
            @update:model-value="handleTextUpdate('nickname', $event)"
            @blur="handleFieldBlur('nickname')"
          />
        </BaseField>

        <BaseField
          id="phone-number"
          label="전화번호"
          required
          hint="숫자만 입력해 주세요."
          :error="errors.phoneNumber"
          v-slot="{ descriptionId, isInvalid }"
        >
          <BaseInput
            id="phone-number"
            :model-value="form.phoneNumber"
            type="tel"
            inputmode="tel"
            placeholder="01012345678"
            autocomplete="tel"
            :maxlength="11"
            required
            :invalid="isInvalid"
            :described-by="descriptionId"
            @update:model-value="handleTextUpdate('phoneNumber', $event)"
            @blur="handleFieldBlur('phoneNumber')"
          />
        </BaseField>

        <fieldset
          id="gender-group"
          class="gender-field basic-info-form__full"
          :class="{ 'gender-field--invalid': errors.gender }"
          :aria-invalid="errors.gender ? 'true' : 'false'"
          :aria-describedby="errors.gender ? 'gender-error' : undefined"
          tabindex="-1"
        >
          <legend class="gender-field__legend">
            성별
            <span class="gender-field__required" aria-hidden="true">*</span>
            <span class="gender-field__required-text">필수 선택</span>
          </legend>

          <div class="gender-field__options">
            <label
              v-for="option in genderOptions"
              :key="option.value"
              class="gender-field__option"
              :class="{
                'gender-field__option--selected': form.gender === option.value,
              }"
            >
              <input
                v-model="form.gender"
                class="gender-field__input"
                type="radio"
                name="gender"
                :value="option.value"
                required
                @change="handleGenderChange"
              />
              <span>{{ option.label }}</span>
            </label>
          </div>

          <p v-if="errors.gender" id="gender-error" class="gender-field__error" role="alert">
            {{ errors.gender }}
          </p>
        </fieldset>

        <BaseField
          id="address"
          class="basic-info-form__full"
          label="주소"
          required
          hint="주소 검색을 이용하거나 직접 입력할 수 있습니다."
          :error="errors.address"
          v-slot="{ descriptionId, isInvalid }"
        >
          <div class="address-field__control">
            <BaseInput
              id="address"
              :model-value="form.address"
              placeholder="도로명 또는 지번 주소"
              autocomplete="street-address"
              required
              :invalid="isInvalid"
              :described-by="descriptionId"
              @update:model-value="handleTextUpdate('address', $event)"
              @blur="handleFieldBlur('address')"
            />

            <BaseButton
              class="address-field__search"
              variant="secondary"
              :disabled="isAddressSearchLoading"
              @click="handleAddressSearch"
            >
              {{ isAddressSearchLoading ? '불러오는 중' : '주소 검색' }}
            </BaseButton>
          </div>

          <p v-if="addressSearchError" class="address-field__service-error" role="alert">
            {{ addressSearchError }}
          </p>
        </BaseField>

        <BaseField
          id="detail-address"
          class="basic-info-form__full"
          label="상세 주소"
          required
          hint="동, 호수 등 나머지 주소를 입력해 주세요."
          :error="errors.detailAddress"
          v-slot="{ descriptionId, isInvalid }"
        >
          <BaseInput
            id="detail-address"
            ref="detailAddressInput"
            :model-value="form.detailAddress"
            placeholder="상세 주소를 입력해 주세요"
            autocomplete="address-line2"
            required
            :invalid="isInvalid"
            :described-by="descriptionId"
            @update:model-value="handleTextUpdate('detailAddress', $event)"
            @blur="handleFieldBlur('detailAddress')"
          />
        </BaseField>
      </div>

      <div class="basic-info-form__notice" role="note">
        <strong class="basic-info-form__notice-title">입력 안내</strong>
        <p>원활한 서비스 이용을 위해 정확한 정보를 입력해 주세요.</p>
      </div>

      <p
        v-if="submitError"
        class="basic-info-form__submit-error"
        role="alert"
        aria-live="assertive"
      >
        {{ submitError }}
      </p>
    </form>
  </OnboardingLayout>
</template>

<style scoped lang="scss">
.basic-info-form {
  width: 100%;
}

.basic-info-form__header {
  margin-bottom: var(--space-8);
}

.basic-info-form__title {
  font-size: 24px;
  font-weight: 700;
  line-height: 34px;
}

.basic-info-form__description {
  margin-top: var(--space-2);
  color: var(--color-text-secondary);
}

.basic-info-form__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 320px), 1fr));
  gap: var(--space-6);
}

.basic-info-form__full {
  grid-column: 1 / -1;
}

.gender-field {
  min-width: 0;
  padding: 0;
  border: 0;
}

.gender-field:focus {
  outline: none;
}

.gender-field:focus-visible .gender-field__options {
  border-radius: var(--radius-control);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
}

.gender-field__legend {
  margin-bottom: var(--space-2);
  color: var(--color-text-primary);
  font-size: 14px;
  font-weight: 600;
  line-height: 20px;
}

.gender-field__required {
  margin-left: 2px;
  color: var(--color-error);
}

.gender-field__required-text {
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

.gender-field__options {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 160px), 1fr));
  gap: var(--space-3);
}

.gender-field__option {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: var(--button-height-standard);
  padding: 0 var(--space-4);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  cursor: pointer;
  font-weight: 600;
  transition:
    border-color 160ms ease,
    background-color 160ms ease,
    color 160ms ease,
    box-shadow 160ms ease;
}

.gender-field__option:hover {
  border-color: var(--color-primary);
}

.gender-field__option:has(.gender-field__input:focus-visible) {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
}

.gender-field__option--selected {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
  color: var(--color-primary);
}

.gender-field--invalid .gender-field__option {
  border-color: var(--color-error);
}

.gender-field__input {
  position: absolute;
  width: 1px;
  height: 1px;
  opacity: 0;
}

.gender-field__error,
.address-field__service-error {
  min-height: 20px;
  margin-top: var(--space-2);
  color: var(--color-error);
  font-size: 13px;
  line-height: 20px;
}

.address-field__control {
  display: flex;
  align-items: stretch;
  flex-wrap: wrap;
  gap: var(--space-3);
}

.address-field__control :deep(.base-input) {
  flex: 1 1 320px;
}

.address-field__search {
  flex: 0 0 auto;
}

.basic-info-form__notice {
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  margin-top: var(--space-8);
  background: var(--color-surface-secondary);
  color: var(--color-text-secondary);
  font-size: 14px;
}

.basic-info-form__notice-title {
  display: block;
  margin-bottom: var(--space-1);
  color: var(--color-primary);
}

.basic-info-form__submit-error {
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-control);
  margin-top: var(--space-6);
  background: var(--color-error-soft);
  color: var(--color-error);
  font-size: 14px;
  font-weight: 600;
}
</style>
