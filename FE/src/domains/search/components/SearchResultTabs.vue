<script setup lang="ts">
import type { SearchResultTab, SearchResultTabId } from '@/domains/search/types/search.types'

defineProps<{
  tabs: SearchResultTab[]
  activeTabId: SearchResultTabId
}>()

const emit = defineEmits<{
  select: [tabId: SearchResultTabId]
}>()
</script>

<template>
  <div class="search-result-tabs" role="tablist" aria-label="검색 결과 유형">
    <button
      v-for="tab in tabs"
      :id="`search-tab-${tab.id}`"
      :key="tab.id"
      class="search-result-tabs__item"
      :class="{ 'search-result-tabs__item--active': activeTabId === tab.id }"
      type="button"
      role="tab"
      :aria-selected="activeTabId === tab.id"
      :aria-controls="`search-panel-${tab.id}`"
      @click="emit('select', tab.id)"
    >
      <span>{{ tab.label }}</span>
      <span class="search-result-tabs__count">{{ tab.count.toLocaleString('ko-KR') }}</span>
    </button>
  </div>
</template>

<style scoped lang="scss">
.search-result-tabs {
  display: flex;
  min-height: 48px;
  gap: var(--space-4);
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--color-border);
}

.search-result-tabs__item {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 92px;
  height: 40px;
  gap: var(--space-2);
  padding: 0 var(--space-4);
  border: 1px solid transparent;
  border-radius: 999px;
  background: transparent;
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-bold);
  transition:
    background 160ms ease,
    border-color 160ms ease,
    color 160ms ease;
}

.search-result-tabs__item:hover {
  color: var(--color-primary);
}

.search-result-tabs__item--active {
  border-color: var(--color-primary-soft);
  background: var(--color-primary-soft);
  color: var(--color-primary);
}

.search-result-tabs__item:focus-visible {
  outline: 3px solid var(--color-primary-soft);
  outline-offset: 2px;
}

.search-result-tabs__count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 22px;
  height: 22px;
  padding: 0 var(--space-2);
  border-radius: 999px;
  background: var(--color-surface-secondary);
  color: var(--color-text-muted);
  font-size: var(--font-size-caption);
  font-variant-numeric: tabular-nums;
  font-weight: var(--font-weight-bold);
}

.search-result-tabs__item--active .search-result-tabs__count {
  background: var(--color-surface);
  color: var(--color-primary);
}

@media (max-width: 720px) {
  .search-result-tabs {
    overflow-x: auto;
  }

  .search-result-tabs__item {
    flex: 1 0 auto;
    min-width: 84px;
    padding: 0 var(--space-3);
  }
}
</style>
