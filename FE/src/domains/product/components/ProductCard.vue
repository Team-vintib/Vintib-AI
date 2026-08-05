<script setup lang="ts">
import { computed } from 'vue'

import fallbackProductImage from '@/assets/images/products/product-denim-jacket.webp'
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

const formattedPrice = computed(() =>
  props.product.saleType === 'AUCTION'
    ? '경매 예정'
    : `${props.product.price.toLocaleString('ko-KR')}P`,
)
const saleTypeLabel = computed(() =>
  props.product.saleType === 'AUCTION' ? '경매 예정' : '정찰제',
)
const displayImageUrl = computed(() => props.product.imageUrl || fallbackProductImage)
const handleImageError = (event: Event) => {
  const target = event.target

  if (target instanceof HTMLImageElement) {
    target.onerror = null
    target.src = fallbackProductImage
  }
}
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
          class="product-card__image"
          :src="displayImageUrl"
          :alt="product.imageAlt"
          @error="handleImageError"
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
    border-color var(--transition-base),
    transform var(--transition-base);
}

.product-card {
  transition:
    border-color var(--transition-slow),
    background-color var(--transition-slow),
    transform var(--transition-emphasized);
}

.product-card:hover {
  border-color: var(--color-border-strong);
  transform: translateY(-3px);
}

.product-card:hover .product-card__image {
  transform: scale(1.045);
}

.product-card__media {
  position: relative;
  overflow: hidden;
  aspect-ratio: 4 / 5;
  background: var(--color-image-frame);
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
  filter: saturate(0.88) contrast(1.04) brightness(0.95);
  transition: transform var(--transition-emphasized);
}

.product-card__grade {
  position: absolute;
  top: 0;
  left: 0;
  padding: 3px var(--space-2);
  border-radius: 0 0 var(--radius-badge) 0;
  background: var(--overlay-scrim-strong);
  color: var(--color-text-primary);
  font-family: var(--font-mono);
  font-size: var(--font-size-badge);
  font-weight: var(--font-weight-medium);
  letter-spacing: 0.06em;
  line-height: var(--line-height-xs);
}

.product-card__like-button {
  position: absolute;
  top: var(--space-2);
  right: var(--space-2);
  display: grid;
  place-items: center;
  width: var(--button-height-2xs);
  height: var(--button-height-2xs);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-badge);
  background: var(--overlay-scrim-medium);
  color: var(--color-text-secondary);
  backdrop-filter: blur(2px);
}

.product-card__like-button svg {
  width: var(--icon-size-md);
  height: var(--icon-size-md);
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
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

.product-card__body {
  display: block;
  padding: var(--space-4);
}

.product-card__detail-link:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: calc(var(--focus-ring-offset) * -1);
}

.product-card__brand {
  overflow: hidden;
  color: var(--color-text-muted);
  font-family: var(--font-mono);
  font-size: var(--font-size-badge);
  font-weight: var(--font-weight-medium);
  letter-spacing: 0.16em;
  line-height: var(--line-height-snug);
  text-overflow: ellipsis;
  text-transform: uppercase;
  white-space: nowrap;
}

.product-card__name {
  overflow: hidden;
  min-height: var(--badge-height-xs);
  margin-top: var(--space-1);
  color: var(--color-text-primary);
  font-size: var(--font-size-body);
  font-weight: var(--font-weight-medium);
  line-height: var(--line-height-relaxed);
  letter-spacing: -0.01em;
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
  font-family: var(--font-mono);
  font-size: var(--font-size-body);
  font-variant-numeric: tabular-nums;
  font-weight: var(--font-weight-medium);
  letter-spacing: -0.02em;
  line-height: var(--line-height-relaxed);
}

.product-card__price-prefix {
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
}

.product-card__sale-badge {
  flex: 0 0 auto;
  padding: 3px var(--space-2);
  border: 1px solid var(--color-border-input);
  border-radius: var(--radius-badge);
  background: transparent;
  color: var(--color-text-muted);
  font-size: var(--font-size-2xs);
  font-weight: var(--font-weight-regular);
  line-height: var(--line-height-xs);
}

.product-card__sale-badge--auction {
  border-color: var(--color-accent);
  background: transparent;
  color: var(--color-accent);
}
</style>
