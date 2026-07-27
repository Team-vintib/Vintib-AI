<script setup lang="ts">
import axios from 'axios'
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

import { saveOnboardingInterests } from '@/domains/onboard/api/onboarding'
import BaseField from '@/domains/onboard/components/BaseField.vue'
import BaseInput from '@/domains/onboard/components/BaseInput.vue'
import OnboardingLayout from '@/domains/onboard/components/OnboardingLayout.vue'
import { ROUTE_NAMES } from '@/shared/constants/routes'

import type { ApiErrorBody as ApiError, ApiResponse } from '@/shared/types/api.types'

interface InterestOption {
  id: string
  label: string
}

const brands: InterestOption[] = [
  { id: 'brand-a', label: '브랜드 A' },
  { id: 'brand-b', label: '브랜드 B' },
  { id: 'brand-c', label: '브랜드 C' },
  { id: 'brand-d', label: '브랜드 D' },
  { id: 'brand-e', label: '브랜드 E' },
  { id: 'brand-f', label: '브랜드 F' },
]

const categories: InterestOption[] = [
  { id: 'outer', label: '아우터' },
  { id: 'top', label: '상의' },
  { id: 'bottom', label: '하의' },
  { id: 'dress', label: '원피스' },
  { id: 'shoes', label: '신발' },
  { id: 'accessories', label: '액세서리' },
]

const brandSearchQuery = ref('')
const selectedBrandIds = ref<string[]>([])
const selectedCategoryIds = ref<string[]>([])
const isSubmitting = ref(false)
const submitError = ref('')
const router = useRouter()

const filteredBrands = computed(() => {
  const normalizedSearchQuery = brandSearchQuery.value.trim().toLocaleLowerCase()

  if (!normalizedSearchQuery) {
    return brands
  }

  return brands.filter((brand) => brand.label.toLocaleLowerCase().includes(normalizedSearchQuery))
})

const isBrandSelected = (brandId: string) => selectedBrandIds.value.includes(brandId)

const toggleBrand = (brandId: string) => {
  submitError.value = ''

  if (isBrandSelected(brandId)) {
    selectedBrandIds.value = selectedBrandIds.value.filter(
      (selectedBrandId) => selectedBrandId !== brandId,
    )
    return
  }

  selectedBrandIds.value = [...selectedBrandIds.value, brandId]
}

const handlePrevious = async () => {
  await router.push({ name: ROUTE_NAMES.ONBOARD_PROFILE })
}

const applyApiError = (apiError: ApiError | null) => {
  submitError.value =
    apiError?.message || '관심 정보를 저장하지 못했습니다. 잠시 후 다시 시도해 주세요.'
}

const handleSave = async (skip = false) => {
  if (isSubmitting.value) {
    return
  }

  isSubmitting.value = true
  submitError.value = ''

  try {
    const response = await saveOnboardingInterests({
      brandIds: skip ? [] : [...selectedBrandIds.value],
      categoryIds: skip ? [] : [...selectedCategoryIds.value],
    })

    if (!response.success) {
      applyApiError(response.error ?? null)
      return
    }

    await router.push({ name: ROUTE_NAMES.ONBOARD_TRYON })
  } catch (error: unknown) {
    if (axios.isAxiosError<ApiResponse<unknown>>(error)) {
      if (!error.response) {
        submitError.value =
          '서버에 연결하지 못했습니다. 네트워크 상태를 확인한 뒤 다시 시도해 주세요.'
      } else {
        applyApiError(error.response.data?.error ?? null)
      }
    } else {
      applyApiError(null)
    }
  } finally {
    isSubmitting.value = false
  }
}

const handleCategoryChange = () => {
  submitError.value = ''
}
</script>

<template>
  <OnboardingLayout
    :current-step="2"
    title="관심 정보를 설정해 주세요"
    description="관심 있는 브랜드와 카테고리를 선택해 주세요."
    show-skip
    :previous-disabled="isSubmitting"
    :skip-disabled="isSubmitting"
    :next-disabled="isSubmitting"
    :next-label="isSubmitting ? '저장 중' : '다음 단계'"
    @previous="handlePrevious"
    @skip="handleSave(true)"
    @next="handleSave(false)"
  >
    <div class="interest-selection">
      <header class="interest-selection__header">
        <div>
          <h2 class="interest-selection__title">관심 정보</h2>
          <p class="interest-selection__description">
            선택한 관심 정보는 맞춤 상품과 라이브를 추천하는 데 사용됩니다.
          </p>
        </div>

        <span class="interest-selection__optional">선택 사항</span>
      </header>

      <fieldset class="interest-group" aria-describedby="brand-selection-hint">
        <legend class="interest-group__legend">
          <span>관심 브랜드</span>
          <span class="interest-group__count" aria-live="polite">
            {{ selectedBrandIds.length }}개 선택
          </span>
        </legend>

        <p id="brand-selection-hint" class="interest-group__hint">
          여러 브랜드를 선택할 수 있습니다.
        </p>

        <BaseField
          id="brand-search"
          class="brand-search"
          label="브랜드 검색"
          hint="브랜드명을 입력하면 아래 목록에서 검색할 수 있습니다."
        >
          <template #default="{ descriptionId, isInvalid }">
            <BaseInput
              id="brand-search"
              v-model="brandSearchQuery"
              placeholder="브랜드명을 입력해 주세요."
              :described-by="descriptionId"
              :invalid="isInvalid"
            />
          </template>
        </BaseField>

        <div v-if="filteredBrands.length > 0" class="brand-options">
          <button
            v-for="brand in filteredBrands"
            :key="brand.id"
            class="brand-option"
            :class="{ 'brand-option--selected': isBrandSelected(brand.id) }"
            type="button"
            :aria-pressed="isBrandSelected(brand.id)"
            @click="toggleBrand(brand.id)"
          >
            <span
              class="brand-option__check"
              :class="{ 'brand-option__check--visible': isBrandSelected(brand.id) }"
              aria-hidden="true"
            >
              ✓
            </span>
            <span>{{ brand.label }}</span>
          </button>
        </div>

        <p v-else class="brand-options-empty" role="status">검색 결과가 없습니다.</p>
      </fieldset>

      <fieldset class="interest-group" aria-describedby="category-selection-hint">
        <legend class="interest-group__legend">
          <span>관심 카테고리</span>
          <span class="interest-group__count" aria-live="polite">
            {{ selectedCategoryIds.length }}개 선택
          </span>
        </legend>

        <p id="category-selection-hint" class="interest-group__hint">
          자주 찾는 의류 카테고리를 모두 선택해 주세요.
        </p>

        <div class="category-options">
          <label
            v-for="category in categories"
            :key="category.id"
            class="category-option"
            :class="{
              'category-option--selected': selectedCategoryIds.includes(category.id),
            }"
          >
            <input
              v-model="selectedCategoryIds"
              class="category-option__input"
              type="checkbox"
              name="interest-category"
              :value="category.id"
              @change="handleCategoryChange"
            />

            <span class="category-option__label">{{ category.label }}</span>

            <span class="category-option__check" aria-hidden="true">
              {{ selectedCategoryIds.includes(category.id) ? '✓' : '' }}
            </span>
          </label>
        </div>
      </fieldset>

      <div class="interest-selection__notice" role="note">
        <strong>나중에 변경할 수 있어요</strong>
        <p>관심 정보는 선택 사항이며, 가입 후 마이페이지에서 언제든 수정할 수 있습니다.</p>
      </div>

      <p
        v-if="submitError"
        class="interest-selection__submit-error"
        role="alert"
        aria-live="assertive"
      >
        {{ submitError }}
      </p>
    </div>
  </OnboardingLayout>
</template>

<style scoped lang="scss">
.interest-selection {
  width: 100%;
}

.interest-selection__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
  margin-bottom: var(--space-10);
}

.interest-selection__title {
  font-size: 24px;
  font-weight: 700;
  line-height: 34px;
}

.interest-selection__description {
  margin-top: var(--space-2);
  color: var(--color-text-secondary);
}

.interest-selection__optional {
  flex: 0 0 auto;
  padding: var(--space-1) var(--space-3);
  border-radius: 999px;
  background: var(--color-surface-secondary);
  color: var(--color-text-secondary);
  font-size: 12px;
  font-weight: 600;
  line-height: 20px;
}

.interest-group {
  min-width: 0;
  padding: 0;
  border: 0;
}

.interest-group + .interest-group {
  padding-top: var(--space-10);
  border-top: 1px solid var(--color-border);
  margin-top: var(--space-10);
}

.interest-group__legend {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  gap: var(--space-4);
  color: var(--color-text-primary);
  font-size: 17px;
  font-weight: 600;
  line-height: 24px;
}

.interest-group__count {
  color: var(--color-primary);
  font-size: 13px;
  font-weight: 600;
  line-height: 18px;
}

.interest-group__hint {
  margin-top: var(--space-1);
  color: var(--color-text-secondary);
  font-size: 13px;
  line-height: 20px;
}

.brand-search {
  margin-top: var(--space-5);
}

.brand-options {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  margin-top: var(--space-5);
}

.brand-options-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 72px;
  padding: var(--space-4);
  border: 1px dashed var(--color-border-strong);
  border-radius: var(--radius-control);
  margin-top: var(--space-5);
  background: var(--color-surface-secondary);
  color: var(--color-text-secondary);
  font-size: 14px;
  line-height: 20px;
  text-align: center;
}

.brand-option {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  min-width: 136px;
  min-height: var(--button-height-standard);
  padding: 0 var(--space-5);
  border: 1px solid var(--color-border-strong);
  border-radius: 999px;
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

.brand-option:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.brand-option:focus-visible {
  border-color: var(--color-primary);
  outline: none;
  box-shadow: 0 0 0 3px var(--color-primary-soft);
}

.brand-option--selected {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
  color: var(--color-primary);
}

.brand-option__check {
  width: 0;
  overflow: hidden;
  opacity: 0;
  transition:
    width 160ms ease,
    opacity 160ms ease;
}

.brand-option__check--visible {
  width: 14px;
  opacity: 1;
}

.category-options {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-3);
  margin-top: var(--space-5);
}

.category-option {
  display: flex;
  align-items: center;
  min-height: 64px;
  padding: 0 var(--space-5);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition:
    border-color 160ms ease,
    background-color 160ms ease,
    color 160ms ease,
    box-shadow 160ms ease;
}

.category-option:hover {
  border-color: var(--color-primary);
}

.category-option:has(.category-option__input:focus-visible) {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
}

.category-option--selected {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
  color: var(--color-primary);
}

.category-option__input {
  position: absolute;
  width: 1px;
  height: 1px;
  opacity: 0;
}

.category-option__label {
  font-weight: 600;
}

.category-option__check {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: 1px solid var(--color-border-strong);
  border-radius: 6px;
  margin-left: auto;
  background: var(--color-surface);
  color: var(--color-text-inverse);
  font-size: 14px;
  font-weight: 700;
}

.category-option--selected .category-option__check {
  border-color: var(--color-primary);
  background: var(--color-primary);
}

.interest-selection__notice {
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  margin-top: var(--space-10);
  background: var(--color-surface-secondary);
  color: var(--color-text-secondary);
  font-size: 14px;
}

.interest-selection__notice strong {
  display: block;
  margin-bottom: var(--space-1);
  color: var(--color-primary);
}

.interest-selection__submit-error {
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-control);
  margin-top: var(--space-6);
  background: var(--color-error-soft);
  color: var(--color-error);
  font-size: 14px;
  font-weight: 600;
}

@media (max-width: 820px) {
  .category-options {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 560px) {
  .interest-selection__header,
  .interest-group__legend {
    align-items: flex-start;
    flex-direction: column;
  }

  .brand-option {
    flex: 1 1 calc(50% - var(--space-3));
    min-width: 0;
  }

  .category-options {
    grid-template-columns: 1fr;
  }
}
</style>
