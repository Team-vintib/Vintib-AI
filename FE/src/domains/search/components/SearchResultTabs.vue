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
  min-height: 52px;
  border-bottom: 1px solid var(--color-border);
}

.search-result-tabs__item {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 112px;
  gap: var(--space-2);
  padding: 0 var(--space-4);
  border: 0;
  border-bottom: 2px solid transparent;
  background: transparent;
  color: var(--color-text-secondary);
  font-weight: 700;
}

.search-result-tabs__item:hover,
.search-result-tabs__item--active {
  border-bottom-color: var(--color-primary);
  color: var(--color-primary);
}

.search-result-tabs__item:focus-visible {
  outline: 3px solid var(--color-primary-soft);
  outline-offset: -3px;
}

.search-result-tabs__count {
  color: var(--color-text-muted);
  font-size: 13px;
  font-variant-numeric: tabular-nums;
  font-weight: 700;
}

.search-result-tabs__item--active .search-result-tabs__count {
  color: var(--color-primary);
}

@media (max-width: 720px) {
  .search-result-tabs {
    overflow-x: auto;
  }

  .search-result-tabs__item {
    flex: 1 0 auto;
    min-width: 88px;
    padding: 0 var(--space-3);
  }
}
</style>
