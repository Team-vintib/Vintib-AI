<script setup lang="ts">
import {
  PRODUCT_CATEGORY_OPTIONS,
  PRODUCT_CONDITION_OPTIONS,
} from '@/domains/product/constants/productListMockData'

interface Props {
  selectedCategoryIds: string[]
  selectedConditionIds: string[]
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:selectedCategoryIds': [categoryIds: string[]]
  'update:selectedConditionIds': [conditionIds: string[]]
  reset: []
  apply: []
}>()

const toggleSelection = (selectedIds: string[], targetId: string, isSelected: boolean) => {
  if (isSelected) {
    return [...selectedIds, targetId]
  }

  return selectedIds.filter((id) => id !== targetId)
}

const handleCategoryChange = (event: Event, categoryId: string) => {
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
</script>

<template>
  <aside class="product-filter" aria-label="상품 필터">
    <fieldset class="product-filter__group">
      <legend class="product-filter__legend">카테고리</legend>

      <label
        v-for="option in PRODUCT_CATEGORY_OPTIONS"
        :key="option.id"
        class="product-filter__option"
      >
        <input
          class="product-filter__checkbox"
          type="checkbox"
          :checked="selectedCategoryIds.includes(option.id)"
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
          @change="handleConditionChange($event, option.id)"
        />
        <span>{{ option.label }}</span>
      </label>
    </fieldset>

    <div class="product-filter__actions">
      <button
        class="product-filter__button product-filter__button--reset"
        type="button"
        @click="emit('reset')"
      >
        초기화
      </button>
      <button
        class="product-filter__button product-filter__button--apply"
        type="button"
        @click="emit('apply')"
      >
        적용
      </button>
    </div>
  </aside>
</template>

<style scoped lang="scss">
.product-filter {
  position: sticky;
  top: var(--space-6);
  align-self: start;
  width: 224px;
  padding: var(--space-6);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
}

.product-filter__group {
  display: grid;
  gap: var(--space-3);
  border: 0;
}

.product-filter__group + .product-filter__group {
  margin-top: var(--space-8);
}

.product-filter__legend {
  margin-bottom: var(--space-4);
  color: var(--color-text-primary);
  font-size: 15px;
  font-weight: 700;
}

.product-filter__option {
  display: flex;
  align-items: center;
  min-height: 24px;
  gap: var(--space-3);
  color: var(--color-text-secondary);
  cursor: pointer;
}

.product-filter__checkbox {
  width: 16px;
  height: 16px;
  accent-color: var(--color-primary);
}

.product-filter__checkbox:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 3px;
}

.product-filter__actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-2);
  margin-top: var(--space-8);
}

.product-filter__button {
  min-height: var(--button-height-small);
  border-radius: var(--radius-control);
  font-size: 14px;
  font-weight: 600;
  transition:
    border-color 160ms ease,
    background-color 160ms ease,
    color 160ms ease;
}

.product-filter__button:focus-visible {
  outline: 3px solid var(--color-primary-soft);
  outline-offset: 2px;
}

.product-filter__button--reset {
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text-primary);
}

.product-filter__button--reset:hover {
  border-color: var(--color-border-strong);
  background: var(--color-surface-secondary);
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

  .product-filter__group + .product-filter__group {
    margin-top: var(--space-6);
  }

  .product-filter__legend {
    grid-column: 1 / -1;
  }

  .product-filter__actions {
    max-width: 240px;
  }
}
</style>
