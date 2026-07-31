<script setup lang="ts">
type StateVariant = 'loading' | 'empty' | 'filter-empty' | 'error'

defineProps<{
  variant: StateVariant
  title?: string
  description?: string
}>()

const emit = defineEmits<{
  action: []
}>()
</script>

<template>
  <div
    v-if="variant === 'loading'"
    class="notification-state notification-state--loading"
    role="status"
    aria-live="polite"
  >
    <span class="sr-only">알림 목록을 불러오는 중입니다.</span>
    <div v-for="index in 5" :key="index" class="notification-state__skeleton" aria-hidden="true">
      <span class="notification-state__skeleton-icon" />
      <span class="notification-state__skeleton-content">
        <span class="notification-state__skeleton-line notification-state__skeleton-line--meta" />
        <span class="notification-state__skeleton-line notification-state__skeleton-line--title" />
        <span class="notification-state__skeleton-line" />
      </span>
    </div>
  </div>

  <section
    v-else
    class="notification-state notification-state--message"
    :class="`notification-state--${variant}`"
    :aria-live="variant === 'error' ? 'assertive' : 'polite'"
  >
    <span class="notification-state__icon" aria-hidden="true">
      <svg v-if="variant === 'error'" viewBox="0 0 24 24">
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7v6m0 4h.01" />
      </svg>
      <svg v-else viewBox="0 0 24 24">
        <path d="M18 9.8a6 6 0 1 0-12 0c0 5.7-2.2 6.7-2.2 6.7h16.4S18 15.5 18 9.8Z" />
        <path d="M14.1 19a2.3 2.3 0 0 1-4.2 0" />
      </svg>
    </span>
    <h2>{{ title }}</h2>
    <p>{{ description }}</p>
    <button v-if="variant !== 'empty'" type="button" @click="emit('action')">
      {{ variant === 'error' ? '다시 시도' : '전체 보기' }}
    </button>
  </section>
</template>

<style scoped lang="scss">
.notification-state--loading {
  display: grid;
  gap: var(--space-3);
}

.notification-state__skeleton {
  display: grid;
  grid-template-columns: 44px minmax(0, 1fr);
  gap: var(--space-4);
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
}

.notification-state__skeleton-icon,
.notification-state__skeleton-line {
  border-radius: var(--radius-badge);
  background: linear-gradient(
    100deg,
    var(--color-surface-secondary) 20%,
    var(--color-border) 38%,
    var(--color-surface-secondary) 56%
  );
  background-size: 220% 100%;
  animation: notification-skeleton 1.4s ease-in-out infinite;
}

.notification-state__skeleton-icon {
  width: 44px;
  height: 44px;
}

.notification-state__skeleton-content {
  display: grid;
  gap: var(--space-2);
}

.notification-state__skeleton-line {
  width: 100%;
  height: 14px;
}

.notification-state__skeleton-line--meta {
  width: 34%;
}

.notification-state__skeleton-line--title {
  width: 68%;
  height: 18px;
}

.notification-state--message {
  display: grid;
  min-height: 320px;
  padding: var(--space-10) var(--space-6);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  text-align: center;
  place-items: center;
  align-content: center;
}

.notification-state__icon {
  display: grid;
  width: 56px;
  height: 56px;
  margin-bottom: var(--space-4);
  border-radius: 50%;
  background: var(--color-primary-soft);
  color: var(--color-primary);
  place-items: center;
}

.notification-state--error .notification-state__icon {
  background: var(--color-error-soft);
  color: var(--color-live);
}

.notification-state__icon svg {
  width: 26px;
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.8;
}

.notification-state h2 {
  color: var(--color-text-primary);
  font-size: 20px;
  font-weight: var(--font-weight-bold);
  line-height: 30px;
}

.notification-state p {
  max-width: 460px;
  margin-top: var(--space-2);
  color: var(--color-text-secondary);
  font-size: 14px;
  line-height: 22px;
}

.notification-state button {
  min-height: var(--button-height-standard);
  padding: 0 var(--space-5);
  margin-top: var(--space-5);
  border: 0;
  border-radius: var(--radius-control);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-size: 14px;
  font-weight: var(--font-weight-bold);
}

@keyframes notification-skeleton {
  to {
    background-position-x: -220%;
  }
}

@media (prefers-reduced-motion: reduce) {
  .notification-state__skeleton-icon,
  .notification-state__skeleton-line {
    animation: none;
  }
}
</style>
