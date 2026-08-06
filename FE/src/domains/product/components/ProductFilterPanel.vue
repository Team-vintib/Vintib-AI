<script setup lang="ts">
import { PRODUCT_CONDITION_OPTIONS } from '@/domains/product/constants/productListMockData'
import type { ProductCategoryOption } from '@/domains/product/types/productList.types'

interface Props {
  categoryOptions: ProductCategoryOption[]
  categoryStatusMessage: string
  selectedCategoryIds: number[]
  selectedConditionIds: string[]
  minimumPrice: string
  maximumPrice: string
  priceError: string
  canReset: boolean
  disabled?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  disabled: false,
})

const emit = defineEmits<{
  'update:selectedCategoryIds': [categoryIds: number[]]
  'update:selectedConditionIds': [conditionIds: string[]]
  'update:minimumPrice': [price: string]
  'update:maximumPrice': [price: string]
  reset: []
  apply: []
}>()

const toggleSelection = <T,>(selectedIds: T[], targetId: T, isSelected: boolean): T[] => {
  if (isSelected) {
    return [...selectedIds, targetId]
  }

  return selectedIds.filter((id) => id !== targetId)
}

const handleCategoryChange = (event: Event, categoryId: number) => {
  const isSelected = (event.target as HTMLInputElement).checked

  emit(
    'update:selectedCategoryIds',
    toggleSelection(props.selectedCategoryIds, categoryId, isSelected),
  )
}

const handleConditionChange = (event: Event, conditionId: string) => {
  const isSelected = (event.target as HTMLInputElement).checked

  emit(
    'update:selectedConditionIds',
    toggleSelection(props.selectedConditionIds, conditionId, isSelected),
  )
}

const handlePriceInput = (event: Event, target: 'minimum' | 'maximum') => {
  const value = (event.target as HTMLInputElement).value

  if (target === 'minimum') {
    emit('update:minimumPrice', value)
    return
  }

  emit('update:maximumPrice', value)
}
</script>

<template>
  <aside class="product-filter" aria-label="상품 필터">
    <div class="product-filter__heading">
      <h2>필터</h2>
      <button
        type="button"
        :disabled="disabled || !canReset"
        @click="emit('reset')"
      >
        초기화
      </button>
    </div>

    <fieldset class="product-filter__group">
      <legend class="product-filter__legend">카테고리</legend>

      <p v-if="!categoryOptions.length" class="product-filter__empty">
        {{ categoryStatusMessage }}
      </p>

      <label
        v-for="option in categoryOptions"
        :key="option.id"
        class="product-filter__option"
      >
        <input
          class="product-filter__checkbox"
          type="checkbox"
          :checked="selectedCategoryIds.includes(option.id)"
          :disabled="disabled"
          @change="handleCategoryChange($event, option.id)"
        />
        <span>{{ option.label }}</span>
      </label>
    </fieldset>

    <fieldset class="product-filter__group">
      <legend class="product-filter__legend">상태</legend>

      <label
        v-for="option in PRODUCT_CONDITION_OPTIONS"
        :key="option.id"
        class="product-filter__option"
      >
        <input
          class="product-filter__checkbox"
          type="checkbox"
          :checked="selectedConditionIds.includes(option.id)"
          :disabled="disabled"
          @change="handleConditionChange($event, option.id)"
        />
        <span>{{ option.label }}</span>
      </label>
    </fieldset>

    <fieldset class="product-filter__group">
      <legend class="product-filter__legend">가격</legend>

      <div class="product-filter__price-fields">
        <label class="product-filter__price-field">
          <span>최소 가격</span>
          <span class="product-filter__price-control">
            <input
              :value="minimumPrice"
              type="number"
              min="0"
              step="1000"
              inputmode="numeric"
              placeholder="0"
              :disabled="disabled"
              :aria-invalid="Boolean(priceError)"
              :aria-describedby="priceError ? 'product-price-error' : undefined"
              @input="handlePriceInput($event, 'minimum')"
            />
            <span aria-hidden="true">P</span>
          </span>
        </label>

        <span class="product-filter__price-separator" aria-hidden="true">–</span>

        <label class="product-filter__price-field">
          <span>최대 가격</span>
          <span class="product-filter__price-control">
            <input
              :value="maximumPrice"
              type="number"
              min="0"
              step="1000"
              inputmode="numeric"
              placeholder="제한 없음"
              :disabled="disabled"
              :aria-invalid="Boolean(priceError)"
              :aria-describedby="priceError ? 'product-price-error' : undefined"
              @input="handlePriceInput($event, 'maximum')"
            />
            <span aria-hidden="true">P</span>
          </span>
        </label>
      </div>

      <p v-if="priceError" id="product-price-error" class="product-filter__error" role="alert">
        {{ priceError }}
      </p>
    </fieldset>

    <div class="product-filter__actions">
      <button
        class="product-filter__button product-filter__button--apply"
        type="button"
        :disabled="disabled"
        @click="emit('apply')"
      >
        적용
      </button>
    </div>
  </aside>
</template>

<style scoped lang="scss">
.product-filter {
  display: grid;
  align-self: start;
  width: var(--filter-panel-width);
  gap: var(--space-6);
  padding: var(--space-6);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
}

.product-filter__heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
}

.product-filter__heading h2 {
  color: var(--color-text-primary);
  font-family: var(--font-mono);
  font-size: var(--font-size-badge);
  font-weight: var(--font-weight-regular);
  letter-spacing: 0.2em;
  text-transform: uppercase;
}

.product-filter__heading button {
  border: 0;
  background: transparent;
  color: var(--color-text-secondary);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-semibold);
  text-decoration: underline;
  text-underline-offset: 3px;
}

.product-filter__heading button:hover:not(:disabled) {
  color: var(--color-primary);
}

.product-filter__heading button:focus-visible {
  outline: 1px solid var(--color-primary);
  outline-offset: 2px;
}

.product-filter__heading button:disabled {
  color: var(--color-text-muted);
  cursor: not-allowed;
  opacity: 0.65;
}

.product-filter__group {
  display: grid;
  gap: var(--space-3);
  border: 0;
}

.product-filter__group + .product-filter__group {
  padding-top: var(--space-6);
  border-top: 1px solid var(--color-border);
}

.product-filter__legend {
  margin-bottom: var(--space-4);
  color: var(--color-text-primary);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-medium);
  letter-spacing: -0.01em;
}

.product-filter__option {
  display: flex;
  align-items: center;
  min-height: var(--filter-option-min-height);
  gap: var(--space-3);
  color: var(--color-text-secondary);
  cursor: pointer;
}

.product-filter__option:has(input:disabled) {
  cursor: not-allowed;
  opacity: 0.55;
}

.product-filter__empty {
  color: var(--color-text-muted);
  font-size: var(--font-size-caption);
  line-height: var(--line-height-control);
}

.product-filter__checkbox {
  width: var(--icon-size-xs-plus);
  height: var(--icon-size-xs-plus);
  accent-color: var(--color-primary);
}

.product-filter__checkbox:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: var(--focus-ring-offset);
}

.product-filter__price-fields {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--space-3);
}

.product-filter__price-field {
  display: grid;
  min-width: 0;
  gap: var(--space-2);
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-semibold);
}

.product-filter__price-control {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  min-width: 0;
  height: var(--button-height-small);
  padding-right: var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-muted);
}

.product-filter__price-control:focus-within {
  border-color: var(--color-border-underline);
}

.product-filter__price-control input {
  min-width: 0;
  width: 100%;
  height: 100%;
  padding: 0 0 0 var(--space-3);
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--color-text-primary);
  font-family: var(--font-mono);
  font-size: var(--font-size-caption);
  font-variant-numeric: tabular-nums;
}

.product-filter__price-control input::placeholder {
  color: var(--color-text-muted);
}

.product-filter__price-control input::-webkit-inner-spin-button,
.product-filter__price-control input::-webkit-outer-spin-button {
  margin: 0;
  appearance: none;
}

.product-filter__price-control input[type='number'] {
  appearance: textfield;
}

.product-filter__price-separator {
  display: none;
}

.product-filter__error {
  margin-top: var(--space-3);
  color: var(--color-error);
  font-size: var(--font-size-xs);
  line-height: var(--line-height-snug);
}

.product-filter__actions {
  display: block;
}

.product-filter__button {
  width: 100%;
  min-height: var(--button-height-small);
  border-radius: var(--radius-control);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-semibold);
  transition:
    border-color var(--transition-base),
    background-color var(--transition-base),
    color var(--transition-base);
}

.product-filter__button:disabled {
  cursor: wait;
  opacity: 0.6;
}

.product-filter__button:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

.product-filter__button--apply {
  border: 1px solid var(--color-primary);
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

.product-filter__button--apply:hover {
  border-color: var(--color-primary-hover);
  background: var(--color-primary-hover);
}

@media (max-width: 1024px) {
  .product-filter {
    position: static;
    width: 100%;
  }

  .product-filter__group {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .product-filter__legend {
    grid-column: 1 / -1;
  }

  .product-filter__price-fields,
  .product-filter__error {
    grid-column: 1 / -1;
    max-width: 440px;
  }

  .product-filter__price-fields {
    grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
    align-items: end;
    gap: var(--space-2);
  }

  .product-filter__price-separator {
    display: block;
    padding-bottom: 11px;
    color: var(--color-text-muted);
  }

  .product-filter__actions {
    max-width: 240px;
  }
}
</style>
