<script setup lang="ts">
import axios from 'axios'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/domains/auth/stores/authStore'
import { saveOnboardingInterests } from '@/domains/onboard/api/onboarding'
import BaseField from '@/domains/onboard/components/BaseField.vue'
import BaseInput from '@/domains/onboard/components/BaseInput.vue'
import OnboardingLayout from '@/domains/onboard/components/OnboardingLayout.vue'
import { getBrands, getCategories } from '@/domains/product/api/productApi'
import { ROUTE_NAMES } from '@/shared/constants/routes'

import type { ApiErrorBody as ApiError, ApiResponse } from '@/shared/types/api.types'

interface InterestOption {
  id: number
  label: string
}

// 관심 카테고리는 성별(depth 1)을 빼고 대분류(depth 2)만 보여준다.
// 성별마다 중복되는 대분류(예: 남/여/공용 상의)를 이름으로 묶고, 선택 시 그 이름의 모든 성별 id를 함께 담는다.
interface CategoryGroup {
  label: string
  ids: number[]
}

const brandSearchQuery = ref('')
const brands = ref<InterestOption[]>([])
const categories = ref<CategoryGroup[]>([])
const selectedBrandIds = ref<number[]>([])
const selectedCategoryIds = ref<number[]>([])
const isSubmitting = ref(false)
const submitError = ref('')
const router = useRouter()
const authStore = useAuthStore()

const filteredBrands = computed(() => {
  const normalizedSearchQuery = brandSearchQuery.value.trim().toLocaleLowerCase()

  if (!normalizedSearchQuery) {
    return brands.value
  }

  return brands.value.filter((brand) => brand.label.toLocaleLowerCase().includes(normalizedSearchQuery))
})

const isBrandSelected = (brandId: number) => selectedBrandIds.value.includes(brandId)

const toggleBrand = (brandId: number) => {
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
  if (apiError?.code === 'P008') {
    submitError.value =
      '선택한 브랜드 중 더 이상 존재하지 않는 항목이 있습니다. 목록을 새로고침한 뒤 다시 선택해 주세요.'
    return
  }

  if (apiError?.code === 'P009') {
    submitError.value =
      '선택한 카테고리 중 더 이상 존재하지 않는 항목이 있습니다. 목록을 새로고침한 뒤 다시 선택해 주세요.'
    return
  }

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
    }, {
      userId: authStore.user?.id,
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

const isCategorySelected = (ids: number[]) =>
  ids.length > 0 && ids.every((id) => selectedCategoryIds.value.includes(id))

// 대분류 그룹을 토글한다 — 성별 구분 없이 그 이름의 모든 성별 id를 함께 넣거나 뺀다.
const toggleCategory = (ids: number[]) => {
  submitError.value = ''

  if (isCategorySelected(ids)) {
    selectedCategoryIds.value = selectedCategoryIds.value.filter((id) => !ids.includes(id))
    return
  }

  selectedCategoryIds.value = [...new Set([...selectedCategoryIds.value, ...ids])]
}

const selectedCategoryCount = computed(
  () => categories.value.filter((category) => isCategorySelected(category.ids)).length,
)

const loadInterestOptions = async () => {
  try {
    const [brandResponse, categoryResponse] = await Promise.all([getBrands(), getCategories()])

    brands.value = brandResponse.map((brand) => ({
      id: brand.id,
      label: brand.nameEn ? `${brand.name} (${brand.nameEn})` : brand.name,
    }))
    const categoryGroups = new Map<string, number[]>()
    categoryResponse
      .filter((category) => category.depth === 2)
      .forEach((category) => {
        const ids = categoryGroups.get(category.name) ?? []
        ids.push(category.id)
        categoryGroups.set(category.name, ids)
      })
    categories.value = [...categoryGroups.entries()].map(([label, ids]) => ({ label, ids }))
  } catch {
    brands.value = []
    categories.value = []
  }
}

onMounted(() => {
  void loadInterestOptions()
})
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
            {{ selectedCategoryCount }}개 선택
          </span>
        </legend>

        <p id="category-selection-hint" class="interest-group__hint">
          자주 찾는 의류 카테고리를 모두 선택해 주세요.
        </p>

        <div class="category-options">
          <button
            v-for="category in categories"
            :key="category.label"
            type="button"
            class="category-option"
            :class="{ 'category-option--selected': isCategorySelected(category.ids) }"
            :aria-pressed="isCategorySelected(category.ids)"
            @click="toggleCategory(category.ids)"
          >
            <span class="category-option__label">{{ category.label }}</span>

            <span class="category-option__check" aria-hidden="true">
              {{ isCategorySelected(category.ids) ? '✓' : '' }}
            </span>
          </button>
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
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-2xl-loose);
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
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-control);
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
  font-size: var(--font-size-md-plus);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-body);
}

.interest-group__count {
  color: var(--color-primary);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-snug);
}

.interest-group__hint {
  margin-top: var(--space-1);
  color: var(--color-text-secondary);
  font-size: var(--font-size-caption);
  line-height: var(--line-height-control);
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
  font-size: var(--font-size-button-small);
  line-height: var(--line-height-control);
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
  font-weight: var(--font-weight-semibold);
  transition:
    border-color var(--transition-base),
    background-color var(--transition-base),
    color var(--transition-base),
    box-shadow var(--transition-base);
}

.brand-option:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.brand-option:focus-visible {
  border-color: var(--color-primary);
  outline: none;
  box-shadow: none;
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
    width var(--transition-base),
    opacity var(--transition-base);
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
    border-color var(--transition-base),
    background-color var(--transition-base),
    color var(--transition-base),
    box-shadow var(--transition-base);
}

.category-option:hover {
  border-color: var(--color-primary);
}

.category-option:has(.category-option__input:focus-visible) {
  border-color: var(--color-primary);
  box-shadow: none;
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
  font-weight: var(--font-weight-semibold);
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
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-bold);
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
  font-size: var(--font-size-button-small);
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
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-semibold);
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
