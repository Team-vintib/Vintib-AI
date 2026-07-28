<script setup lang="ts">
defineProps<{
  variant: 'error' | 'not-found'
  title: string
  description: string
  primaryLabel: string
  secondaryLabel?: string
}>()

const emit = defineEmits<{
  primary: []
  secondary: []
}>()
</script>

<template>
  <section
    class="product-detail-state"
    :class="`product-detail-state--${variant}`"
    :role="variant === 'error' ? 'alert' : 'status'"
  >
    <div class="product-detail-state__icon" aria-hidden="true">
      <svg v-if="variant === 'error'" viewBox="0 0 24 24">
        <path d="M12 8v5m0 3.5v.5M10.3 4.6 3.2 17a2 2 0 0 0 1.7 3h14.2a2 2 0 0 0 1.7-3L13.7 4.6a2 2 0 0 0-3.4 0Z" />
      </svg>
      <svg v-else viewBox="0 0 24 24">
        <circle cx="11" cy="11" r="7" />
        <path d="m20 20-4-4" />
      </svg>
    </div>

    <p class="product-detail-state__eyebrow">
      {{ variant === 'error' ? '일시적인 오류' : '상품 없음' }}
    </p>
    <h1>{{ title }}</h1>
    <p class="product-detail-state__description">{{ description }}</p>

    <div class="product-detail-state__actions">
      <button class="product-detail-state__primary" type="button" @click="emit('primary')">
        {{ primaryLabel }}
      </button>
      <button
        v-if="secondaryLabel"
        class="product-detail-state__secondary"
        type="button"
        @click="emit('secondary')"
      >
        {{ secondaryLabel }}
      </button>
    </div>
  </section>
</template>

<style scoped lang="scss">
.product-detail-state {
  display: grid;
  min-height: 520px;
  align-content: center;
  justify-items: center;
  padding: var(--space-12);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
  text-align: center;
}

.product-detail-state__icon {
  display: grid;
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: var(--color-surface-secondary);
  color: var(--color-text-secondary);
  place-items: center;
}

.product-detail-state--error .product-detail-state__icon {
  background: var(--color-error-soft);
  color: var(--color-error);
}

.product-detail-state__icon svg {
  width: 28px;
  height: 28px;
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.7;
}

.product-detail-state__eyebrow {
  margin-top: var(--space-5);
  color: var(--color-text-muted);
  font-size: 13px;
  font-weight: 600;
  line-height: 18px;
}

.product-detail-state h1 {
  margin-top: var(--space-2);
  font-size: 26px;
  font-weight: 700;
  line-height: 36px;
}

.product-detail-state__description {
  max-width: 520px;
  margin-top: var(--space-3);
  color: var(--color-text-secondary);
  font-size: 15px;
  line-height: 24px;
}

.product-detail-state__actions {
  display: flex;
  gap: var(--space-3);
  margin-top: var(--space-8);
}

.product-detail-state__actions button {
  min-width: 128px;
  height: var(--button-height-standard);
  padding: 0 var(--space-5);
  border-radius: var(--radius-control);
  font-weight: 600;
}

.product-detail-state__primary {
  border: 1px solid var(--color-primary);
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

.product-detail-state__secondary {
  border: 1px solid var(--color-border-strong);
  background: var(--color-surface);
  color: var(--color-text-primary);
}

.product-detail-state__actions button:focus-visible {
  outline: 3px solid var(--color-primary-soft);
  outline-offset: 2px;
}
</style>
