<script setup lang="ts">
import { computed, ref } from 'vue'

import type { ProductDetailImage } from '@/domains/product/types/productDetail.types'

const props = defineProps<{
  images: ProductDetailImage[]
  selectedImageId: string
}>()

const emit = defineEmits<{
  selectImage: [imageId: string]
}>()

const zoomDialog = ref<HTMLDialogElement | null>(null)

const selectedImageIndex = computed(() => {
  const selectedIndex = props.images.findIndex((image) => image.id === props.selectedImageId)
  return selectedIndex >= 0 ? selectedIndex : 0
})

const representativeImage = computed(() => props.images[selectedImageIndex.value])

const hasMultipleImages = computed(() => props.images.length > 1)

// 이미지 개수 무관 캐러셀. images[].role(앞/뒤)은 BE 미제공(010)이라 역할 구분 없이
// 정렬된 순서 그대로 좌우로 넘겨 본다. 양 끝에서는 순환(wrap-around)한다.
const goToOffset = (offset: number) => {
  if (!props.images.length) {
    return
  }

  const nextIndex =
    (selectedImageIndex.value + offset + props.images.length) % props.images.length
  emit('selectImage', props.images[nextIndex].id)
}

const openZoom = () => {
  zoomDialog.value?.showModal()
}

const closeZoom = () => {
  zoomDialog.value?.close()
}
</script>

<template>
  <section class="product-gallery" aria-label="상품 이미지">
    <div class="product-gallery__main">
      <img
        v-if="representativeImage"
        class="product-gallery__main-image"
        :src="representativeImage.url"
        :alt="representativeImage.alt"
      />
      <div v-else class="product-gallery__empty">등록된 상품 이미지가 없습니다.</div>

      <button
        v-if="hasMultipleImages"
        class="product-gallery__nav product-gallery__nav--prev"
        type="button"
        aria-label="이전 이미지"
        @click="goToOffset(-1)"
      >
        <svg aria-hidden="true" viewBox="0 0 24 24">
          <path d="m15 18-6-6 6-6" />
        </svg>
      </button>
      <button
        v-if="hasMultipleImages"
        class="product-gallery__nav product-gallery__nav--next"
        type="button"
        aria-label="다음 이미지"
        @click="goToOffset(1)"
      >
        <svg aria-hidden="true" viewBox="0 0 24 24">
          <path d="m9 6 6 6-6 6" />
        </svg>
      </button>

      <span v-if="hasMultipleImages" class="product-gallery__counter" aria-hidden="true">
        {{ selectedImageIndex + 1 }} / {{ images.length }}
      </span>

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

    <div
      v-if="hasMultipleImages"
      class="product-gallery__thumbnails"
      aria-label="상품 이미지 목록"
    >
      <button
        v-for="image in images"
        :key="image.id"
        class="product-gallery__thumbnail"
        :class="{ 'product-gallery__thumbnail--selected': image.id === representativeImage?.id }"
        type="button"
        :aria-label="`${image.label} 이미지 보기`"
        :aria-pressed="image.id === representativeImage?.id"
        @click="emit('selectImage', image.id)"
      >
        <img :src="image.url" alt="" />
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
        />
      </div>
    </dialog>
  </section>
</template>

<style scoped lang="scss">
.product-gallery {
  display: flex;
  flex-direction: column;
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

.product-gallery__nav {
  position: absolute;
  top: 50%;
  display: grid;
  width: 44px;
  height: 44px;
  border: 1px solid rgba(225, 224, 218, 0.8);
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.92);
  color: var(--color-text-secondary);
  place-items: center;
  transform: translateY(-50%);
  transition:
    background-color 160ms ease,
    color 160ms ease;
}

.product-gallery__nav--prev {
  left: var(--space-4);
}

.product-gallery__nav--next {
  right: var(--space-4);
}

.product-gallery__nav svg {
  width: 20px;
  height: 20px;
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.8;
}

.product-gallery__nav:hover {
  background: var(--color-surface);
  color: var(--color-primary);
}

.product-gallery__counter {
  position: absolute;
  bottom: var(--space-4);
  left: 50%;
  padding: 4px 10px;
  border-radius: var(--radius-badge);
  background: rgba(24, 24, 22, 0.72);
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  line-height: 16px;
  transform: translateX(-50%);
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

.product-gallery__zoom:hover {
  background: var(--color-surface);
  color: var(--color-primary);
}

.product-gallery__thumbnails {
  display: flex;
  gap: var(--space-3);
  overflow-x: auto;
  padding-bottom: var(--space-1);
  scroll-snap-type: x mandatory;
}

.product-gallery__thumbnail {
  flex: 0 0 auto;
  overflow: hidden;
  width: 72px;
  aspect-ratio: 4 / 5;
  padding: 0;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  scroll-snap-align: start;
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

.product-gallery__thumbnail:hover {
  border-color: var(--color-border-strong);
}

.product-gallery__thumbnail:focus-visible,
.product-gallery__zoom:focus-visible,
.product-gallery__nav:focus-visible {
  outline: 3px solid var(--color-primary-soft);
  outline-offset: 2px;
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
  z-index: 1;
  top: var(--space-3);
  right: var(--space-3);
  display: grid;
  width: 40px;
  height: 40px;
  border: 1px solid var(--color-border);
  border-radius: 50%;
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-size: 26px;
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
  .product-gallery__thumbnail {
    width: 56px;
  }

  .product-gallery__nav {
    width: 38px;
    height: 38px;
  }
}
</style>
