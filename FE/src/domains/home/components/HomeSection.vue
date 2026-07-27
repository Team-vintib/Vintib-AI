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
  }>(),
  {
    linkLabel: '전체보기',
    linkTo: undefined,
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

    <slot />
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
}

.home-section__eyebrow {
  color: var(--color-primary);
  font-size: 13px;
  font-weight: 800;
  line-height: 20px;
}

.home-section__title {
  margin-top: var(--space-1);
  color: var(--color-text-primary);
  font-size: 24px;
  font-weight: 800;
  line-height: 34px;
}

.home-section__link {
  color: var(--color-primary);
  font-size: 14px;
  font-weight: 800;
  white-space: nowrap;
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
