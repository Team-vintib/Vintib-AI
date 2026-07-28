<script setup lang="ts">
import { computed } from 'vue'

import type { ProductDetailImage } from '@/domains/product/types/productDetail.types'

const props = defineProps<{
  images: ProductDetailImage[]
}>()

const representativeImage = computed(() => props.images[0])
</script>

<template>
  <section class="product-gallery" aria-label="상품 이미지">
    <div v-if="images.length" class="product-gallery__thumbnails" aria-label="상품 이미지 목록">
      <button
        v-for="(image, index) in images"
        :key="image.id"
        class="product-gallery__thumbnail"
        :class="{ 'product-gallery__thumbnail--selected': index === 0 }"
        type="button"
        :aria-label="`${image.label} 이미지 보기`"
        :aria-pressed="index === 0"
      >
        <img :src="image.url" alt="" />
      </button>
    </div>

    <div class="product-gallery__main">
      <img
        v-if="representativeImage"
        class="product-gallery__main-image"
        :src="representativeImage.url"
        :alt="representativeImage.alt"
      />
      <div v-else class="product-gallery__empty">등록된 상품 이미지가 없습니다.</div>

      <button
        v-if="representativeImage"
        class="product-gallery__zoom"
        type="button"
        aria-label="상품 이미지 확대"
      >
        <svg aria-hidden="true" viewBox="0 0 24 24">
          <path d="m15 15 5 5m-2-9a7 7 0 1 1-14 0 7 7 0 0 1 14 0Z" />
        </svg>
      </button>
    </div>
  </section>
</template>

<style scoped lang="scss">
.product-gallery {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr);
  align-items: start;
  gap: var(--space-4);
  min-width: 0;
}

.product-gallery__main {
  position: relative;
  display: grid;
  overflow: hidden;
  aspect-ratio: 4 / 5;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-media);
  background: var(--color-surface-secondary);
  place-items: center;
}

.product-gallery__main-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.product-gallery__empty {
  padding: var(--space-6);
  color: var(--color-text-muted);
  font-size: 13px;
  font-weight: 400;
  line-height: 18px;
  text-align: center;
}

.product-gallery__thumbnails {
  display: grid;
  gap: var(--space-3);
}

.product-gallery__thumbnail {
  overflow: hidden;
  width: 72px;
  aspect-ratio: 4 / 5;
  padding: 0;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  transition: border-color 160ms ease;
}

.product-gallery__thumbnail--selected {
  border: 2px solid var(--color-primary);
}

.product-gallery__thumbnail img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.product-gallery__thumbnail:nth-child(2) img {
  transform: scale(1.35);
  transform-origin: 50% 26%;
}

.product-gallery__thumbnail:nth-child(3) img {
  transform: scale(1.45);
  transform-origin: 45% 78%;
}

.product-gallery__thumbnail:nth-child(4) img {
  transform: scale(1.45);
  transform-origin: 90% 78%;
}

.product-gallery__zoom {
  position: absolute;
  top: var(--space-4);
  right: var(--space-4);
  display: grid;
  width: 40px;
  height: 40px;
  border: 1px solid rgba(225, 224, 218, 0.8);
  border-radius: var(--radius-control);
  background: rgba(255, 255, 255, 0.92);
  color: var(--color-text-secondary);
  place-items: center;
  transition:
    background-color 160ms ease,
    color 160ms ease;
}

.product-gallery__zoom svg {
  width: 18px;
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-width: 1.6;
}

.product-gallery__thumbnail:hover {
  border-color: var(--color-border-strong);
}

.product-gallery__zoom:hover {
  background: var(--color-surface);
  color: var(--color-primary);
}

.product-gallery__thumbnail:focus-visible,
.product-gallery__zoom:focus-visible {
  outline: 3px solid var(--color-primary-soft);
  outline-offset: 2px;
}

@media (max-width: 520px) {
  .product-gallery {
    grid-template-columns: 56px minmax(0, 1fr);
    gap: var(--space-3);
  }

  .product-gallery__thumbnail {
    width: 56px;
  }
}
</style>
