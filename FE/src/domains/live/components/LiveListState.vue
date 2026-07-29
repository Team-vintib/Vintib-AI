<script setup lang="ts">
type StateVariant = 'loading' | 'empty' | 'filter-empty' | 'error'

interface Props {
  variant: StateVariant
  title?: string
  description?: string
}

defineProps<Props>()

const emit = defineEmits<{
  action: []
}>()
</script>

<template>
  <div
    v-if="variant === 'loading'"
    class="live-list-state live-list-state--loading"
    role="status"
    aria-live="polite"
  >
    <span class="sr-only">라이브 목록을 불러오는 중입니다.</span>
    <div v-for="index in 6" :key="index" class="live-list-state__skeleton" aria-hidden="true">
      <span class="live-list-state__skeleton-media" />
      <span class="live-list-state__skeleton-line live-list-state__skeleton-line--title" />
      <span class="live-list-state__skeleton-line" />
      <span class="live-list-state__skeleton-line live-list-state__skeleton-line--short" />
    </div>
  </div>

  <section
    v-else
    class="live-list-state live-list-state--message"
    :class="`live-list-state--${variant}`"
    :aria-live="variant === 'error' ? 'assertive' : 'polite'"
  >
    <span class="live-list-state__icon" aria-hidden="true">
      <svg v-if="variant === 'error'" viewBox="0 0 24 24">
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7v6m0 4h.01" />
      </svg>
      <svg v-else viewBox="0 0 24 24">
        <path d="M4 6.5h16v12H4z" />
        <path d="m8 13 2.5 2.5L16 10" />
      </svg>
    </span>
    <h2>{{ title }}</h2>
    <p>{{ description }}</p>
    <button v-if="variant !== 'empty'" type="button" @click="emit('action')">
      {{ variant === 'error' ? '다시 시도' : '필터 초기화' }}
    </button>
  </section>
</template>

<style scoped lang="scss">
.live-list-state--loading {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-6);
}

.live-list-state__skeleton {
  display: grid;
  overflow: hidden;
  gap: var(--space-3);
  padding-bottom: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: 20px;
  background: var(--color-surface);
}

.live-list-state__skeleton-media,
.live-list-state__skeleton-line {
  background: linear-gradient(
    100deg,
    var(--color-surface-secondary) 20%,
    var(--color-border) 38%,
    var(--color-surface-secondary) 56%
  );
  background-size: 220% 100%;
  animation: live-list-skeleton 1.4s ease-in-out infinite;
}

.live-list-state__skeleton-media {
  display: block;
  aspect-ratio: 16 / 9;
}

.live-list-state__skeleton-line {
  width: calc(100% - var(--space-10));
  height: 14px;
  margin: 0 var(--space-5);
  border-radius: var(--radius-badge);
}

.live-list-state__skeleton-line--title {
  height: 22px;
}

.live-list-state__skeleton-line--short {
  width: 42%;
}

.live-list-state--message {
  display: grid;
  min-height: 360px;
  padding: var(--space-10) var(--space-6);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
  text-align: center;
  place-items: center;
  align-content: center;
}

.live-list-state__icon {
  display: grid;
  width: 56px;
  height: 56px;
  margin-bottom: var(--space-4);
  border-radius: 50%;
  background: var(--color-surface-secondary);
  color: var(--color-text-secondary);
  place-items: center;
}

.live-list-state--error .live-list-state__icon {
  background: var(--color-error-soft);
  color: var(--color-live);
}

.live-list-state__icon svg {
  width: 26px;
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.8;
}

.live-list-state h2 {
  color: var(--color-text-primary);
  font-size: 20px;
  font-weight: var(--font-weight-bold);
  line-height: 30px;
}

.live-list-state p {
  max-width: 460px;
  margin-top: var(--space-2);
  color: var(--color-text-secondary);
  font-size: 14px;
  line-height: 22px;
}

.live-list-state button {
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

.live-list-state button:focus-visible {
  outline: 3px solid var(--color-primary-soft);
  outline-offset: 3px;
}

@keyframes live-list-skeleton {
  to {
    background-position-x: -220%;
  }
}

@media (prefers-reduced-motion: reduce) {
  .live-list-state__skeleton-media,
  .live-list-state__skeleton-line {
    animation: none;
  }
}

@media (max-width: 840px) {
  .live-list-state--loading {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .live-list-state--loading {
    grid-template-columns: minmax(0, 1fr);
    gap: var(--space-5);
  }

  .live-list-state--message {
    min-height: 320px;
    padding: var(--space-8) var(--space-5);
  }
}
</style>
