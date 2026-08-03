<script setup lang="ts">
import { computed } from 'vue'

import type { ProductListItem } from '@/domains/product/types/productList.types'
import { ROUTE_NAMES } from '@/shared/constants/routes'

interface Props {
  product: ProductListItem
  isLiked: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  toggleLike: [productId: number]
}>()

const formattedPrice = computed(() => `${props.product.price.toLocaleString('ko-KR')}P`)
const pricePrefix = computed(() => (props.product.saleType === 'AUCTION' ? '시작 ' : ''))
const saleTypeLabel = computed(() =>
  props.product.saleType === 'AUCTION' ? '경매 예정' : '상시 판매',
)
</script>

<template>
  <article class="product-card">
    <div class="product-card__media">
      <RouterLink
        class="product-card__detail-link product-card__media-link"
        :to="{ name: ROUTE_NAMES.PRODUCT_DETAIL, params: { productId: product.id } }"
        :aria-label="`${product.name} 상세 보기`"
      >
        <img
          v-if="product.imageUrl"
          class="product-card__image"
          :src="product.imageUrl"
          :alt="product.imageAlt"
        />
        <span class="product-card__grade">{{ product.conditionGrade }}급</span>
      </RouterLink>

      <button
        class="product-card__like-button"
        :class="{ 'product-card__like-button--active': isLiked }"
        type="button"
        :aria-label="isLiked ? `${product.name} 찜 해제` : `${product.name} 찜하기`"
        :aria-pressed="isLiked"
        @click="emit('toggleLike', product.id)"
      >
        <svg aria-hidden="true" viewBox="0 0 24 24">
          <path
            d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78L12 21.23l8.84-8.84a5.5 5.5 0 0 0 0-7.78Z"
          />
        </svg>
      </button>
    </div>

    <RouterLink
      class="product-card__detail-link product-card__body"
      :to="{ name: ROUTE_NAMES.PRODUCT_DETAIL, params: { productId: product.id } }"
    >
      <p class="product-card__brand">{{ product.brand }}</p>
      <h2 class="product-card__name">{{ product.name }}</h2>

      <div class="product-card__meta">
        <p class="product-card__price">
          <span v-if="pricePrefix" class="product-card__price-prefix">{{ pricePrefix }}</span>
          {{ formattedPrice }}
        </p>
        <span
          class="product-card__sale-badge"
          :class="{ 'product-card__sale-badge--auction': product.saleType === 'AUCTION' }"
        >
          {{ saleTypeLabel }}
        </span>
      </div>
    </RouterLink>
  </article>
</template>

<style scoped lang="scss">
.product-card {
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
  transition:
    border-color 160ms ease,
    transform 160ms ease;
}

.product-card:hover {
  border-color: var(--color-border-strong);
  transform: translateY(-2px);
}

.product-card__media {
  position: relative;
  overflow: hidden;
  aspect-ratio: 4 / 5;
  background: var(--color-surface-secondary);
}

.product-card__detail-link {
  color: inherit;
  text-decoration: none;
}

.product-card__media-link {
  display: block;
  width: 100%;
  height: 100%;
}

.product-card__image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.product-card__grade {
  position: absolute;
  top: var(--space-3);
  left: var(--space-3);
  padding: 2px var(--space-2);
  border-radius: var(--radius-badge);
  background: rgba(255, 255, 255, 0.9);
  color: var(--color-text-primary);
  font-size: 12px;
  font-weight: 700;
  line-height: 18px;
}

.product-card__like-button {
  position: absolute;
  top: var(--space-3);
  right: var(--space-3);
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  border: 1px solid rgba(225, 224, 218, 0.8);
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.92);
  color: var(--color-text-secondary);
}

.product-card__like-button svg {
  width: 20px;
  height: 20px;
  fill: transparent;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.8;
}

.product-card__like-button:hover,
.product-card__like-button--active {
  color: var(--color-auction);
}

.product-card__like-button--active svg {
  fill: currentColor;
}

.product-card__like-button:focus-visible {
  outline: 3px solid var(--color-primary-soft);
  outline-offset: 2px;
}

.product-card__body {
  display: block;
  padding: var(--space-4);
}

.product-card__detail-link:focus-visible {
  outline: 3px solid var(--color-primary-soft);
  outline-offset: -3px;
}

.product-card__brand {
  overflow: hidden;
  color: var(--color-text-muted);
  font-size: 13px;
  line-height: 18px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.product-card__name {
  overflow: hidden;
  min-height: 24px;
  margin-top: var(--space-1);
  color: var(--color-text-primary);
  font-size: 17px;
  font-weight: 600;
  line-height: 24px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.product-card__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  margin-top: var(--space-3);
}

.product-card__price {
  color: var(--color-text-primary);
  font-size: 16px;
  font-variant-numeric: tabular-nums;
  font-weight: 700;
  line-height: 24px;
}

.product-card__price-prefix {
  color: var(--color-text-secondary);
  font-size: 12px;
  font-weight: 500;
}

.product-card__sale-badge {
  flex: 0 0 auto;
  padding: 3px var(--space-2);
  border-radius: var(--radius-badge);
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-size: 12px;
  font-weight: 600;
  line-height: 16px;
}

.product-card__sale-badge--auction {
  background: var(--color-auction-soft);
  color: var(--color-auction);
}
</style>
