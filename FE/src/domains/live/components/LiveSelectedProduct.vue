<script setup lang="ts">
import type { LiveWatchProduct } from '@/domains/live/types/liveWatch.types'

defineProps<{
  product: LiveWatchProduct | null
  isWished: boolean
  isWishPending: boolean
  wishMessage: string
}>()

defineEmits<{
  viewProduct: [productId: number]
  toggleWish: []
}>()
</script>

<template>
  <section class="live-selected-product" aria-labelledby="selected-product-title">
    <div class="live-selected-product__heading">
      <h2 id="selected-product-title">선택한 상품 정보</h2>
      <slot name="actions"></slot>
    </div>

    <div v-if="product" class="live-selected-product__body">
      <div class="live-selected-product__image">
        <img
          v-if="product.thumbnailUrl"
          :src="product.thumbnailUrl"
          :alt="`${product.title} 상품 이미지`"
        />
        <span v-else aria-hidden="true">상품</span>
      </div>

      <div class="live-selected-product__content">
        <div class="live-selected-product__identity">
          <strong>{{ product.title }}</strong>
        </div>

        <dl class="live-selected-product__details">
          <div>
            <dt>소재</dt>
            <dd>{{ product.material || '정보 준비 중' }}</dd>
          </div>
          <div>
            <dt>상태</dt>
            <dd>{{ product.condition || '정보 준비 중' }}</dd>
          </div>
          <div>
            <dt>실측</dt>
            <dd>{{ product.measurements || '정보 준비 중' }}</dd>
          </div>
          <div>
            <dt>하자</dt>
            <dd>{{ product.defectSummary || '정보 준비 중' }}</dd>
          </div>
        </dl>

        <div class="live-selected-product__actions">
          <button
            class="live-selected-product__wish"
            :class="{ 'live-selected-product__wish--active': isWished }"
            type="button"
            :aria-pressed="isWished"
            :disabled="isWishPending"
            @click="$emit('toggleWish')"
          >
            <svg v-if="!isWishPending" viewBox="0 0 24 24" aria-hidden="true">
              <path d="M20.3 5.7a5.1 5.1 0 0 0-7.2 0L12 6.8l-1.1-1.1a5.1 5.1 0 0 0-7.2 7.2L12 21l8.3-8.1a5.1 5.1 0 0 0 0-7.2Z" />
            </svg>
            {{ isWishPending ? '처리 중' : isWished ? '찜함' : '찜' }}
          </button>
        </div>
        <p v-if="wishMessage" class="live-selected-product__wish-message" role="status">
          {{ wishMessage }}
        </p>
      </div>
    </div>

    <div v-else class="live-selected-product__empty" role="status">
      상품이 연결되면 상세 정보가 이곳에 표시됩니다.
    </div>
  </section>
</template>

<style scoped lang="scss">
.live-selected-product {
  padding: 15px;
  border-top: 1px solid var(--color-live-border);
  background: var(--color-live-background);
}

.live-selected-product__heading {
  display: flex;
  min-height: 15px;
  align-items: center;
  margin-bottom: 10px;
}

.live-selected-product__heading h2 {
  color: var(--color-live-text-secondary);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-demibold);
  line-height: var(--line-height-tight);
}

.live-selected-product__body {
  display: grid;
  align-items: center;
  grid-template-columns: 180px minmax(0, 1fr);
  gap: 16px;
}

.live-selected-product__identity {
  min-width: 0;
}

.live-selected-product__content {
  min-width: 0;
}

.live-selected-product__image {
  display: grid;
  width: 180px;
  height: 180px;
  overflow: hidden;
  border-radius: var(--radius-control);
  background: var(--color-live-surface-raised);
  color: var(--color-live-text-secondary);
  font-size: var(--font-size-badge);
  place-items: center;
}

.live-selected-product__image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.live-selected-product__identity strong {
  display: -webkit-box;
  overflow: hidden;
  font-size: var(--font-size-2xl);
  line-height: 30px;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.live-selected-product__details {
  display: grid;
  margin-top: 3px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 2px 12px;
}

.live-selected-product__details > div {
  display: grid;
  grid-template-columns: 46px minmax(0, 1fr);
  gap: 4px;
}

.live-selected-product__details dt,
.live-selected-product__details dd {
  overflow: hidden;
  font-size: var(--font-size-md);
  line-height: 22px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.live-selected-product__details dt {
  color: var(--color-live-text-secondary);
}

.live-selected-product__details dt::after {
  content: ':';
}

.live-selected-product__details dd {
  color: var(--color-live-text-primary);
}

.live-selected-product__actions {
  display: flex;
  align-items: center;
  margin-top: 7px;
  gap: var(--space-2);
}

.live-selected-product__actions button {
  display: inline-flex;
  height: 40px;
  min-height: 0;
  align-items: center;
  justify-content: center;
  padding: 0;
  border: 1px solid var(--color-live-border);
  border-radius: var(--radius-control);
  background: var(--color-live-surface-raised);
  color: var(--color-live-text-primary);
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-demibold);
  line-height: 1;
  white-space: nowrap;
}

.live-selected-product__actions button:hover {
  border-color: var(--color-live-text-secondary);
}

.live-selected-product__actions .live-selected-product__wish {
  width: auto;
  min-width: 37px;
  padding: 0 18px;
  gap: 8px;
  background: transparent;
}

.live-selected-product__actions .live-selected-product__wish:disabled {
  cursor: wait;
  opacity: 0.65;
}

.live-selected-product__wish-message {
  margin-top: 5px;
  color: var(--color-accent);
  font-size: var(--font-size-badge);
  line-height: var(--line-height-tight);
}

.live-selected-product__wish svg {
  width: 20px;
  height: 20px;
  fill: none;
  stroke: currentColor;
  stroke-linejoin: round;
  stroke-width: 1.7;
}

.live-selected-product__actions .live-selected-product__wish--active {
  border-color: var(--color-live);
  color: #f06a73;
}

.live-selected-product__wish--active svg {
  fill: currentColor;
}

.live-selected-product__actions button:focus-visible {
  outline: var(--focus-ring-width) solid var(--color-ai);
  outline-offset: 2px;
}

.live-selected-product__empty {
  display: grid;
  min-height: 68px;
  border: 1px dashed var(--color-live-border);
  border-radius: var(--radius-control);
  color: var(--color-live-text-secondary);
  font-size: var(--font-size-2xs);
  place-items: center;
}

@media (max-width: 1180px) {
  .live-selected-product__details {
    column-gap: var(--space-2);
  }
}

@media (max-width: 720px) {
  .live-selected-product__body {
    grid-template-columns: 1fr;
  }

}
</style>
