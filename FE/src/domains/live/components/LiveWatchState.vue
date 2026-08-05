<script setup lang="ts">
defineProps<{
  variant: 'error' | 'not-found'
  title: string
  description: string
  primaryLabel: string
  secondaryLabel?: string
}>()

defineEmits<{
  primary: []
  secondary: []
}>()
</script>

<template>
  <section class="live-watch-state" :role="variant === 'error' ? 'alert' : 'status'">
    <div class="live-watch-state__icon" aria-hidden="true">
      <svg v-if="variant === 'error'" viewBox="0 0 24 24">
        <path d="M12 9v4M12 17h.01" />
        <path d="M10.3 3.6 2.7 17a2 2 0 0 0 1.7 3h15.2a2 2 0 0 0 1.7-3L13.7 3.6a2 2 0 0 0-3.4 0Z" />
      </svg>
      <svg v-else viewBox="0 0 24 24">
        <circle cx="12" cy="12" r="9" />
        <path d="m9 9 6 6M15 9l-6 6" />
      </svg>
    </div>
    <h1>{{ title }}</h1>
    <p>{{ description }}</p>
    <div class="live-watch-state__actions">
      <button type="button" @click="$emit('primary')">{{ primaryLabel }}</button>
      <button v-if="secondaryLabel" type="button" @click="$emit('secondary')">
        {{ secondaryLabel }}
      </button>
    </div>
  </section>
</template>

<style scoped lang="scss">
.live-watch-state {
  display: flex;
  min-height: 100vh;
  align-items: center;
  justify-content: center;
  padding: var(--space-8);
  background: var(--color-live-background);
  flex-direction: column;
  text-align: center;
}

.live-watch-state__icon {
  display: grid;
  width: 64px;
  height: 64px;
  margin-bottom: var(--space-5);
  border-radius: 50%;
  background: var(--color-live-surface-raised);
  color: var(--color-live-text-secondary);
  place-items: center;
}

.live-watch-state__icon svg {
  width: 28px;
  height: var(--badge-height-md);
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.6;
}

.live-watch-state h1 {
  font-size: var(--font-size-2xl);
  line-height: 34px;
}

.live-watch-state p {
  max-width: 460px;
  margin-top: var(--space-3);
  color: var(--color-live-text-secondary);
  font-size: var(--font-size-caption);
  line-height: var(--line-height-comfortable);
}

.live-watch-state__actions {
  display: flex;
  margin-top: var(--space-6);
  gap: var(--space-2);
}

.live-watch-state__actions button {
  min-height: var(--button-height-tight);
  padding: 0 var(--space-5);
  border: 1px solid var(--color-live-border);
  border-radius: var(--radius-control);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-bold);
}

.live-watch-state__actions button + button {
  background: transparent;
  color: var(--color-live-text-primary);
}

.live-watch-state__actions button:focus-visible {
  outline: var(--focus-ring-width) solid var(--color-ai);
  outline-offset: 2px;
}
</style>
