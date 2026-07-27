<script setup lang="ts">
defineProps<{
  titleId: string
  eyebrow: string
  title: string
  description: string
  imageUrl: string
  nowrapSuffix?: string
}>()
</script>

<template>
  <section class="home-hero" :aria-labelledby="titleId">
    <img class="home-hero__image" :src="imageUrl" alt="" />
    <div class="home-hero__content">
      <p class="home-hero__eyebrow">{{ eyebrow }}</p>
      <h1 :id="titleId" class="home-hero__title">
        {{ title }}
        <span v-if="nowrapSuffix" class="home-hero__nowrap">{{ nowrapSuffix }}</span>
      </h1>
      <p class="home-hero__description">{{ description }}</p>
      <div class="home-hero__actions">
        <slot name="actions" />
      </div>
    </div>
  </section>
</template>

<style scoped lang="scss">
.home-hero {
  position: relative;
  width: 100%;
  min-height: 300px;
  overflow: hidden;
  border-radius: var(--radius-media);
  background: var(--color-live-background);
}

.home-hero::after {
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, rgba(14, 17, 16, 0.86), rgba(14, 17, 16, 0.3));
  content: '';
}

.home-hero__image {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.home-hero__content {
  position: relative;
  z-index: 1;
  display: grid;
  max-width: 780px;
  gap: var(--space-4);
  padding: var(--space-10);
}

.home-hero__eyebrow {
  color: var(--color-text-inverse);
  font-size: 13px;
  font-weight: 800;
  line-height: 20px;
}

.home-hero__title {
  color: var(--color-text-inverse);
  font-size: 34px;
  font-weight: 800;
  line-height: 44px;
}

.home-hero__nowrap {
  white-space: nowrap;
}

.home-hero__description {
  color: var(--color-live-text-secondary);
  font-size: 16px;
  line-height: 26px;
}

.home-hero__actions {
  display: flex;
  gap: var(--space-3);
  flex-wrap: wrap;
}

@media (max-width: 768px) {
  .home-hero {
    min-height: 260px;
  }

  .home-hero__content {
    padding: var(--space-6);
  }

  .home-hero__title {
    font-size: 28px;
    line-height: 38px;
  }

  .home-hero__description {
    font-size: 15px;
    line-height: 24px;
  }
}

@media (max-width: 520px) {
  .home-hero__content {
    padding: var(--space-5);
  }
}
</style>
