<script setup lang="ts">
import { RouterLink } from 'vue-router'

import type { HomeContentCardItem } from '@/domains/home/types/homeView.types'

defineProps<{
  content: HomeContentCardItem
}>()
</script>

<template>
  <RouterLink class="content-card" :to="content.targetPath">
    <img class="content-card__image" :src="content.imageUrl" :alt="content.title" />
    <span class="content-card__shade" />
    <span class="content-card__body">
      <strong class="content-card__title">{{ content.title }}</strong>
      <span class="content-card__description">{{ content.description }}</span>
      <span class="content-card__cta">{{ content.ctaLabel }}</span>
    </span>
  </RouterLink>
</template>

<style scoped lang="scss">
.content-card {
  position: relative;
  display: block;
  width: 100%;
  height: 150px;
  min-height: 0;
  overflow: hidden;
  border: 1px solid #e6e1d8;
  border-radius: 20px;
  background: var(--color-surface);
  box-shadow: 0 8px 24px rgb(18 18 18 / 5%);
  transition:
    border-color 160ms ease,
    box-shadow 160ms ease,
    transform 160ms ease;
}

.content-card:hover {
  border-color: #ded8ce;
  box-shadow: 0 10px 26px rgb(18 18 18 / 7%);
  transform: translateY(-2px);
}

.content-card__image {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.content-card__shade {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(14, 17, 16, 0.18), rgba(14, 17, 16, 0.82));
}

.content-card__body {
  position: absolute;
  z-index: 1;
  right: var(--space-8);
  bottom: var(--space-5);
  left: var(--space-8);
  display: grid;
  max-width: 520px;
  gap: var(--space-2);
}

.content-card__title {
  color: var(--color-text-inverse);
  font-size: 24px;
  font-weight: 800;
  line-height: 34px;
}

.content-card__description {
  color: var(--color-live-text-secondary);
}

.content-card__cta {
  color: var(--color-text-inverse);
  font-weight: 800;
}

@media (max-width: 520px) {
  .content-card {
    height: 132px;
  }

  .content-card__body {
    right: var(--space-4);
    bottom: var(--space-4);
    left: var(--space-4);
  }
}
</style>
