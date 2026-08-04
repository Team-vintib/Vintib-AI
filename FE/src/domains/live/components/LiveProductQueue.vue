<script setup lang="ts">
import type { LiveWatchProduct } from '@/domains/live/types/liveWatch.types'

defineProps<{
  products: LiveWatchProduct[]
  currentProductId: number | null
  selectedProductId: number | null
}>()

defineEmits<{
  select: [productId: number]
}>()

const formatPrice = (price: number | null) =>
  price === null ? '가격 정보 준비 중' : `${price.toLocaleString('ko-KR')}P`
</script>

<template>
  <aside class="live-product-queue" aria-label="라이브 상품 큐">
    <div class="live-product-queue__header">
      <h2>상품 큐</h2>
    </div>

    <div v-if="products.length > 0" class="live-product-queue__list">
      <button
        v-for="product in products"
        :key="product.id"
        class="live-product-queue__item"
        :class="{
          'live-product-queue__item--selected': product.id === selectedProductId,
          'live-product-queue__item--current': product.id === currentProductId,
        }"
        type="button"
        :aria-current="product.id === currentProductId ? 'true' : undefined"
        :aria-pressed="product.id === selectedProductId"
        @click="$emit('select', product.id)"
      >
        <span class="live-product-queue__image">
          <img
            v-if="product.thumbnailUrl"
            :src="product.thumbnailUrl"
            :alt="`${product.title} 상품 이미지`"
          />
          <span v-else aria-hidden="true">상품</span>
          <span v-if="product.id === currentProductId" class="live-product-queue__now">NOW</span>
        </span>

        <span class="live-product-queue__content">
          <strong>{{ product.title }}</strong>
          <span>{{ product.brandName || '브랜드 정보 준비 중' }}</span>
          <span class="live-product-queue__price">{{ formatPrice(product.price) }}</span>
          <span class="live-product-queue__ai">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="m12 3 1.35 4.15L17.5 8.5l-4.15 1.35L12 14l-1.35-4.15L6.5 8.5l4.15-1.35L12 3Z" />
            </svg>
            AI
          </span>
        </span>
      </button>
    </div>

    <div v-else class="live-product-queue__empty" role="status">
      <span aria-hidden="true">
        <svg viewBox="0 0 24 24">
          <path d="M6 7h12l-1 13H7L6 7Z" />
          <path d="M9 7a3 3 0 0 1 6 0" />
        </svg>
      </span>
      <strong>소개할 상품이 없습니다</strong>
      <p>판매자가 상품을 연결하면 이곳에 표시됩니다.</p>
    </div>
  </aside>
</template>

<style scoped lang="scss">
.live-product-queue {
  display: flex;
  min-width: 0;
  min-height: 0;
  flex-direction: column;
  border-right: 1px solid var(--color-live-border);
  background: var(--color-live-background);
}

.live-product-queue__header {
  display: flex;
  align-items: center;
  min-height: 30px;
  padding: 0 var(--space-3);
}

.live-product-queue__header h2 {
  color: var(--color-live-text-secondary);
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 400;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.live-product-queue__list {
  overflow-y: auto;
  padding: 0 0 var(--space-3);
}

.live-product-queue__item {
  display: grid;
  width: 100%;
  min-height: 90px;
  min-width: 0;
  padding: 14px 16px;
  border: 0;
  border-bottom: 1px solid var(--color-live-surface);
  border-left: 3px solid transparent;
  background: transparent;
  grid-template-columns: 45px minmax(0, 1fr);
  gap: var(--space-3);
  color: var(--color-live-text-primary);
  text-align: left;
  transition:
    background-color 160ms ease,
    border-color 160ms ease;
}

.live-product-queue__item + .live-product-queue__item {
  margin-top: 0;
}

.live-product-queue__item:hover {
  background: var(--color-live-surface);
}

.live-product-queue__item--selected {
  border-left-color: var(--color-accent);
  background: var(--color-live-surface);
}

.live-product-queue__item--current {
  border-left-color: var(--color-accent);
}

.live-product-queue__image {
  display: grid;
  position: relative;
  width: 45px;
  height: 45px;
  overflow: hidden;
  border-radius: var(--radius-badge);
  background: var(--color-image-frame);
  color: var(--color-live-text-secondary);
  font-size: 10px;
  place-items: center;
}

.live-product-queue__image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  filter: saturate(0.88) contrast(1.04) brightness(0.95);
}

.live-product-queue__now {
  position: absolute;
  top: 0;
  left: 0;
  padding: 2px 5px;
  border-radius: 0 0 var(--radius-badge) 0;
  background: var(--color-accent);
  color: var(--color-primary-strong);
  font-family: var(--font-mono);
  font-size: 8px;
  font-weight: 500;
  letter-spacing: 0.12em;
}

.live-product-queue__content {
  display: flex;
  min-width: 0;
  flex-direction: column;
}

.live-product-queue__content strong {
  display: -webkit-box;
  overflow: hidden;
  color: var(--color-text-strong);
  font-size: 12px;
  font-weight: 500;
  line-height: 1.35;
  letter-spacing: -0.01em;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.live-product-queue__content > span {
  overflow: hidden;
  color: var(--color-live-text-secondary);
  font-size: 10px;
  line-height: 15px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.live-product-queue__content .live-product-queue__price {
  margin-top: 4px;
  color: var(--color-text-caption);
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.06em;
  font-variant-numeric: tabular-nums;
}

.live-product-queue__content .live-product-queue__ai {
  display: inline-flex;
  width: fit-content;
  align-items: center;
  margin-top: 4px;
  padding: 1px 5px;
  border: 1px solid var(--color-accent);
  border-radius: var(--radius-badge);
  gap: 3px;
  color: var(--color-accent);
  font-family: var(--font-mono);
  font-size: 8px;
  font-weight: 500;
  letter-spacing: 0.1em;
  line-height: 13px;
}

.live-product-queue__ai svg {
  width: 9px;
  height: 9px;
  fill: none;
  stroke: currentColor;
  stroke-linejoin: round;
  stroke-width: 1.8;
}

.live-product-queue__empty {
  display: flex;
  flex: 1;
  align-items: center;
  justify-content: center;
  padding: var(--space-6);
  flex-direction: column;
  color: var(--color-live-text-secondary);
  text-align: center;
}

.live-product-queue__empty > span {
  display: grid;
  width: 42px;
  height: 42px;
  margin-bottom: var(--space-3);
  border-radius: 50%;
  background: var(--color-live-surface-raised);
  place-items: center;
}

.live-product-queue__empty svg {
  width: 20px;
  height: 20px;
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.6;
}

.live-product-queue__empty strong {
  color: var(--color-live-text-primary);
  font-size: 12px;
}

.live-product-queue__empty p {
  max-width: 170px;
  margin-top: 5px;
  font-size: 10px;
  line-height: 16px;
}

.live-product-queue__item:focus-visible {
  outline: 1px solid var(--color-live-text-primary);
  outline-offset: -1px;
}

@media (max-width: 720px) {
  .live-product-queue {
    border-right: 0;
    border-bottom: 1px solid var(--color-live-border);
  }

  .live-product-queue__list {
    display: flex;
    overflow-x: auto;
    overflow-y: hidden;
  }

  .live-product-queue__item {
    flex: 0 0 215px;
  }

  .live-product-queue__item + .live-product-queue__item {
    margin-top: 0;
    margin-left: 6px;
  }
}
</style>
