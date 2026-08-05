<script setup lang="ts">
import type { SearchStateContent, SearchStateKind } from '@/domains/search/types/search.types'

const props = defineProps<{
  state: SearchStateKind
  content: SearchStateContent
}>()

const emit = defineEmits<{
  action: []
}>()
</script>

<template>
  <section
    class="search-state"
    :class="{
      'search-state--loading': props.state === 'loading',
      'search-state--error': props.state === 'error' || props.state === 'price-error',
    }"
    :aria-busy="props.state === 'loading'"
    :role="props.state === 'error' || props.state === 'price-error' ? 'alert' : 'status'"
  >
    <div class="search-state__icon" aria-hidden="true">
      <svg v-if="props.state === 'loading'" viewBox="0 0 24 24">
        <path d="M12 3a9 9 0 1 0 9 9" />
      </svg>
      <svg v-else-if="props.state === 'error' || props.state === 'price-error'" viewBox="0 0 24 24">
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7v6" />
        <path d="M12 17h.01" />
      </svg>
      <svg v-else viewBox="0 0 24 24">
        <circle cx="11" cy="11" r="7" />
        <path d="m20 20-3.8-3.8" />
      </svg>
    </div>

    <div class="search-state__body">
      <h2>{{ props.content.title }}</h2>
      <p>{{ props.content.description }}</p>
    </div>

    <button
      v-if="props.content.actionLabel"
      class="search-state__action"
      type="button"
      @click="emit('action')"
    >
      {{ props.content.actionLabel }}
    </button>
  </section>
</template>

<style scoped lang="scss">
.search-state {
  display: grid;
  justify-items: center;
  min-height: var(--surface-min-height-lg);
  gap: var(--space-5);
  place-content: center;
  padding: var(--space-10);
  background: transparent;
  text-align: center;
}

.search-state__icon {
  display: grid;
  place-items: center;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: var(--color-primary-soft);
  color: var(--color-primary);
}

.search-state--error .search-state__icon {
  background: var(--color-error-soft);
  color: var(--color-error);
}

.search-state__icon svg {
  width: 28px;
  height: 28px;
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.8;
}

.search-state--loading .search-state__icon svg {
  animation: search-state-spin 900ms linear infinite;
}

.search-state__body {
  display: grid;
  gap: var(--space-2);
}

.search-state__body h2 {
  color: var(--color-text-primary);
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-extrabold);
  line-height: 30px;
}

.search-state__body p {
  max-width: 420px;
  color: var(--color-text-secondary);
  line-height: var(--line-height-body);
}

.search-state__action {
  min-width: 120px;
  height: var(--button-height-standard);
  padding: 0 var(--space-5);
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-control);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-weight: var(--font-weight-bold);
}

.search-state__action:hover {
  background: var(--color-primary-hover);
}

.search-state__action:focus-visible {
  outline: 1px solid var(--color-primary);
  outline-offset: 2px;
}

@keyframes search-state-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 720px) {
  .search-state {
    min-height: 280px;
    padding: var(--space-8) var(--space-5);
  }
}
</style>
