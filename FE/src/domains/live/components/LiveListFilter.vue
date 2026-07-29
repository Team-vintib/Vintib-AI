<script setup lang="ts">
import { LIVE_CATEGORY_FILTER_OPTIONS } from '@/domains/live/constants/liveListFilterOptions'

import type { LiveCategoryFilter } from '@/domains/live/types/liveList.types'

interface Props {
  selectedCategory: LiveCategoryFilter
  canReset: boolean
}

defineProps<Props>()

const emit = defineEmits<{
  'update:selectedCategory': [category: LiveCategoryFilter]
  reset: []
}>()

const handleCategoryChange = (event: Event) => {
  emit('update:selectedCategory', (event.target as HTMLInputElement).value as LiveCategoryFilter)
}
</script>

<template>
  <aside class="live-list-filter" aria-label="라이브 필터">
    <div class="live-list-filter__heading">
      <h2>필터</h2>
      <button type="button" :disabled="!canReset" @click="emit('reset')">초기화</button>
    </div>

    <fieldset class="live-list-filter__group">
      <legend>카테고리</legend>

      <label v-for="option in LIVE_CATEGORY_FILTER_OPTIONS" :key="option.id">
        <input
          type="radio"
          name="live-category"
          :value="option.id"
          :checked="selectedCategory === option.id"
          @change="handleCategoryChange"
        />
        <span>{{ option.label }}</span>
      </label>
    </fieldset>
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
  font-size: var(--font-size-body);
  font-weight: var(--font-weight-bold);
}

.live-list-filter__heading button {
  border: 0;
  background: transparent;
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: var(--font-weight-semibold);
  text-decoration: underline;
  text-underline-offset: 3px;
}

.live-list-filter__heading button:hover:not(:disabled) {
  color: var(--color-primary);
}

.live-list-filter__heading button:focus-visible,
.live-list-filter__group input:focus-visible {
  outline: 3px solid var(--color-primary-soft);
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
  font-size: 14px;
  font-weight: var(--font-weight-bold);
}

.live-list-filter__group label {
  display: flex;
  align-items: center;
  min-height: var(--filter-option-min-height);
  gap: var(--space-3);
  color: var(--color-text-secondary);
  font-size: 14px;
  cursor: pointer;
}

.live-list-filter__group input {
  width: 16px;
  height: 16px;
  accent-color: var(--color-primary);
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
}

@media (max-width: 640px) {
  .live-list-filter__group {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
