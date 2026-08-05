<script setup lang="ts">
import { LIVE_CATEGORY_FILTER_OPTIONS } from '@/domains/live/constants/liveListFilterOptions'

import type { LiveCategoryFilter } from '@/domains/live/types/liveList.types'

interface Props {
  selectedCategory: LiveCategoryFilter
  canReset: boolean
  disabled?: boolean
}

withDefaults(defineProps<Props>(), {
  disabled: false,
})

const emit = defineEmits<{
  'update:selectedCategory': [category: LiveCategoryFilter]
  reset: []
  apply: []
}>()

const handleCategoryChange = (event: Event) => {
  emit('update:selectedCategory', (event.target as HTMLInputElement).value as LiveCategoryFilter)
}
</script>

<template>
  <aside class="live-list-filter" aria-label="라이브 필터">
    <div class="live-list-filter__heading">
      <h2>필터</h2>
      <button type="button" :disabled="disabled || !canReset" @click="emit('reset')">초기화</button>
    </div>

    <fieldset class="live-list-filter__group">
      <legend>카테고리</legend>

      <label v-for="option in LIVE_CATEGORY_FILTER_OPTIONS" :key="option.id">
        <input
          type="radio"
          name="live-category"
          :value="option.id"
          :checked="selectedCategory === option.id"
          :disabled="disabled"
          @change="handleCategoryChange"
        />
        <span>{{ option.label }}</span>
      </label>
    </fieldset>

    <div class="live-list-filter__actions">
      <button
        class="live-list-filter__apply"
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
.live-list-filter {
  position: sticky;
  top: var(--space-6);
  display: grid;
  align-self: start;
  width: var(--filter-panel-width);
  gap: var(--space-6);
  padding: var(--space-6);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
}

.live-list-filter__heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
}

.live-list-filter__heading h2 {
  color: var(--color-text-primary);
  font-family: var(--font-mono);
  font-size: var(--font-size-badge);
  font-weight: var(--font-weight-regular);
  letter-spacing: 0.2em;
  text-transform: uppercase;
}

.live-list-filter__heading button {
  border: 0;
  background: transparent;
  color: var(--color-text-secondary);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-semibold);
  text-decoration: underline;
  text-underline-offset: 3px;
}

.live-list-filter__heading button:hover:not(:disabled) {
  color: var(--color-primary);
}

.live-list-filter__heading button:focus-visible,
.live-list-filter__group input:focus-visible {
  outline: 1px solid var(--color-primary);
  outline-offset: 2px;
}

.live-list-filter__heading button:disabled {
  color: var(--color-text-muted);
  cursor: not-allowed;
  opacity: 0.65;
}

.live-list-filter__group {
  display: grid;
  gap: var(--space-3);
  border: 0;
}

.live-list-filter__group legend {
  margin-bottom: var(--space-4);
  color: var(--color-text-primary);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-medium);
  letter-spacing: -0.01em;
}

.live-list-filter__group label {
  display: flex;
  align-items: center;
  min-height: var(--filter-option-min-height);
  gap: var(--space-3);
  color: var(--color-text-secondary);
  cursor: pointer;
}

.live-list-filter__group label:has(input:disabled) {
  cursor: not-allowed;
  opacity: 0.55;
}

.live-list-filter__group input {
  width: var(--icon-size-xs-plus);
  height: var(--icon-size-xs-plus);
  accent-color: var(--color-primary);
}

.live-list-filter__actions {
  display: block;
}

.live-list-filter__apply {
  width: 100%;
  min-height: var(--button-height-small);
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-control);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-semibold);
  transition:
    border-color var(--transition-base),
    background-color var(--transition-base),
    color var(--transition-base);
}

.live-list-filter__apply:hover:not(:disabled) {
  border-color: var(--color-primary-hover);
  background: var(--color-primary-hover);
}

.live-list-filter__apply:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

.live-list-filter__apply:disabled {
  cursor: wait;
  opacity: 0.6;
}

@media (max-width: 1024px) {
  .live-list-filter {
    position: static;
    width: 100%;
    padding: var(--space-5);
  }

  .live-list-filter__group {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }

  .live-list-filter__group legend {
    grid-column: 1 / -1;
  }

  .live-list-filter__actions {
    max-width: 240px;
  }
}

@media (max-width: 640px) {
  .live-list-filter__group {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
