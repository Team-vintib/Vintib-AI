<script setup lang="ts">
import { computed, ref } from 'vue'

import fallbackProductImage from '@/assets/images/products/product-denim-jacket.webp'
import type { ProductDetailImage } from '@/domains/product/types/productDetail.types'

const props = defineProps<{
  images: ProductDetailImage[]
  selectedImageId: string
}>()

const handleImageError = (event: Event) => {
  const target = event.target

  if (target instanceof HTMLImageElement) {
    target.onerror = null
    target.src = fallbackProductImage
  }
}

const emit = defineEmits<{
  selectImage: [imageId: string]
}>()

const zoomDialog = ref<HTMLDialogElement | null>(null)

const selectedImageIndex = computed(() => {
  const selectedIndex = props.images.findIndex((image) => image.id === props.selectedImageId)
  return selectedIndex >= 0 ? selectedIndex : 0
})

const representativeImage = computed(() => props.images[selectedImageIndex.value])

// 2~4번째 자리의 확대 스타일은 "상품 실사진 클로즈업"이라는 전제로 만들어졌다.
// AI 착용컷(전신 합성 이미지)은 그 전제가 안 맞아 몇 번째 자리에 오든 확대하지 않는다.
const representativeImageStyle = computed(() => {
  const defaultStyle = { transform: 'scale(1)', transformOrigin: '50% 50%' }

  if (representativeImage.value?.id === 'ai-model-cut') {
    return defaultStyle
  }

  const detailStyles = [
    defaultStyle,
    { transform: 'scale(1.35)', transformOrigin: '50% 26%' },
    { transform: 'scale(1.45)', transformOrigin: '45% 78%' },
    { transform: 'scale(1.45)', transformOrigin: '90% 78%' },
  ]

  return detailStyles[selectedImageIndex.value] ?? detailStyles[0]
})

const openZoom = () => {
  zoomDialog.value?.showModal()
}

const closeZoom = () => {
  zoomDialog.value?.close()
}
</script>

<template>
  <section class="product-gallery" aria-label="상품 이미지">
    <div v-if="images.length" class="product-gallery__thumbnails" aria-label="상품 이미지 목록">
      <button
        v-for="image in images"
        :key="image.id"
        class="product-gallery__thumbnail"
        :class="{
          'product-gallery__thumbnail--selected': image.id === representativeImage?.id,
          'product-gallery__thumbnail--ai-model-cut': image.id === 'ai-model-cut',
        }"
        type="button"
        :aria-label="`${image.label} 이미지 보기`"
        :aria-pressed="image.id === representativeImage?.id"
        @click="emit('selectImage', image.id)"
      >
        <img :src="image.url" alt="" @error="handleImageError" />
      </button>
    </div>

    <div class="product-gallery__main">
      <img
        v-if="representativeImage"
        class="product-gallery__main-image"
        :src="representativeImage.url"
        :alt="representativeImage.alt"
        :style="representativeImageStyle"
        @error="handleImageError"
      />
      <div v-else class="product-gallery__empty">등록된 상품 이미지가 없습니다.</div>

      <button
        v-if="representativeImage"
        class="product-gallery__zoom"
        type="button"
        aria-label="상품 이미지 확대"
        @click="openZoom"
      >
        <svg aria-hidden="true" viewBox="0 0 24 24">
          <path d="m15 15 5 5m-2-9a7 7 0 1 1-14 0 7 7 0 0 1 14 0Z" />
        </svg>
      </button>
    </div>

    <dialog
      ref="zoomDialog"
      class="product-gallery__dialog"
      aria-label="상품 이미지 확대 보기"
      @click.self="closeZoom"
    >
      <button type="button" aria-label="확대 이미지 닫기" @click="closeZoom">×</button>
      <div class="product-gallery__dialog-image">
        <img
          v-if="representativeImage"
          :src="representativeImage.url"
          :alt="`${representativeImage.alt} 확대 이미지`"
          :style="representativeImageStyle"
          @error="handleImageError"
        />
      </div>
    </dialog>
  </section>
</template>

<style scoped lang="scss">
.product-gallery {
  display: grid;
  grid-template-columns: var(--thumbnail-size-sm) minmax(0, 1fr);
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
  background: var(--color-image-frame);
  place-items: center;
}

.product-gallery__main-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  filter: saturate(0.88) contrast(1.04) brightness(0.95);
  transition: transform var(--transition-moderate);
}

.product-gallery__empty {
  padding: var(--space-6);
  color: var(--color-text-muted);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-regular);
  line-height: var(--line-height-snug);
  text-align: center;
}

.product-gallery__thumbnails {
  display: grid;
  gap: var(--space-3);
}

.product-gallery__thumbnail {
  overflow: hidden;
  width: var(--thumbnail-size-sm);
  aspect-ratio: 4 / 5;
  padding: 0;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  transition: border-color var(--transition-base);
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

/* AI 착용컷은 몇 번째 자리에 오든(상품 사진 장수에 따라 위치가 달라짐) 위 nth-child
   확대를 적용하지 않는다 — 전신 합성 이미지라 클로즈업 전제가 안 맞는다. nth-child 규칙과
   동일한 특이도(클래스 2개+엘리먼트)로 써야 소스 순서로 이 규칙이 이긴다. */
.product-gallery__thumbnail.product-gallery__thumbnail--ai-model-cut img {
  transform: none;
  transform-origin: 50% 50%;
}

.product-gallery__zoom {
  position: absolute;
  top: var(--space-4);
  right: var(--space-4);
  display: grid;
  width: var(--button-height-small);
  height: var(--button-height-small);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--overlay-scrim-medium);
  color: var(--color-text-secondary);
  backdrop-filter: blur(2px);
  place-items: center;
  transition:
    background-color var(--transition-base),
    color var(--transition-base);
}

.product-gallery__zoom svg {
  width: var(--icon-size-sm);
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
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

.product-gallery__thumbnail img,
.product-gallery__dialog-image img {
  filter: saturate(0.88) contrast(1.04) brightness(0.95);
}

.product-gallery__dialog {
  width: min(760px, calc(100vw - 48px));
  max-width: none;
  padding: var(--space-6);
  border: 0;
  border-radius: var(--radius-card);
  background: var(--color-surface);
}

.product-gallery__dialog::backdrop {
  background: rgba(24, 24, 22, 0.72);
}

.product-gallery__dialog > button {
  position: absolute;
  z-index: var(--z-layer-1);
  top: var(--space-3);
  right: var(--space-3);
  display: grid;
  width: var(--button-height-sm);
  height: var(--button-height-sm);
  border: 1px solid var(--color-border);
  border-radius: 50%;
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-size: var(--font-size-2xl-plus);
  line-height: 1;
  place-items: center;
}

.product-gallery__dialog-image {
  overflow: hidden;
  aspect-ratio: 4 / 5;
  border-radius: var(--radius-media);
  background: var(--color-surface-secondary);
}

.product-gallery__dialog-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
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
