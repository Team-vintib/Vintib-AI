<script setup lang="ts">
import { RouterLink } from 'vue-router'

import type { RouteLocationRaw } from 'vue-router'

withDefaults(
  defineProps<{
    titleId: string
    eyebrow: string
    title: string
    linkLabel?: string
    linkTo?: RouteLocationRaw
    isEmpty?: boolean
    emptyMessage?: string
  }>(),
  {
    linkLabel: '전체보기',
    linkTo: undefined,
    isEmpty: false,
    emptyMessage: '표시할 콘텐츠가 없습니다.',
  },
)
</script>

<template>
  <section class="home-section" :aria-labelledby="titleId">
    <div class="home-section__header">
      <div>
        <p class="home-section__eyebrow">{{ eyebrow }}</p>
        <h2 :id="titleId" class="home-section__title">{{ title }}</h2>
      </div>
      <RouterLink v-if="linkTo" class="home-section__link" :to="linkTo">
        {{ linkLabel }}
      </RouterLink>
    </div>

    <div v-if="isEmpty" class="home-section__empty">
      <slot name="empty">
        {{ emptyMessage }}
      </slot>
    </div>
    <slot v-else />
  </section>
</template>

<style scoped lang="scss">
.home-section {
  display: grid;
  width: 100%;
  gap: var(--space-5);
}

.home-section__header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--space-4);
  padding-bottom: 14px;
  border-bottom: 1px solid var(--color-border);
}

.home-section__eyebrow {
  color: var(--color-text-muted);
  font-family: var(--font-mono);
  font-size: var(--font-size-badge);
  font-weight: var(--font-weight-regular);
  letter-spacing: 0.2em;
  line-height: var(--line-height-xs);
  text-transform: uppercase;
}

.home-section__title {
  margin-top: var(--space-2);
  color: var(--color-text-primary);
  font-family: var(--font-display);
  font-size: 26px;
  font-weight: var(--font-weight-semibold);
  letter-spacing: -0.03em;
  line-height: 1.05;
}

.home-section__link {
  color: var(--color-text-muted);
  font-family: var(--font-mono);
  font-size: var(--font-size-2xs);
  font-weight: var(--font-weight-regular);
  letter-spacing: 0.14em;
  text-transform: uppercase;
  white-space: nowrap;
  transition: color var(--transition-base);
}

.home-section__link::after {
  content: ' →';
}

.home-section__link:hover {
  color: var(--color-text-primary);
}

.home-section__empty {
  display: grid;
  min-height: 144px;
  place-items: center;
  padding: var(--space-8);
  border: 1px dashed var(--color-border-strong);
  border-radius: var(--radius-card);
  background: var(--color-surface);
  color: var(--color-text-muted);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-light);
  line-height: var(--line-height-relaxed);
  text-align: center;
}

@media (max-width: 768px) {
  .home-section__header {
    align-items: flex-start;
  }

  .home-section__title {
    font-size: 22px;
    line-height: 31px;
  }
}
</style>
