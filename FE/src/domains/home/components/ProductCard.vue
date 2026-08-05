<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import type { HomeProductCardItem } from '@/domains/home/types/homeView.types'
import type { RouteLocationRaw } from 'vue-router'

const props = withDefaults(
  defineProps<{
    product: HomeProductCardItem
    isWished?: boolean
    to?: RouteLocationRaw
    badgeLabel?: string
    badgeVariant?: 'direct' | 'auction'
    pricePrefix?: string
    actionTo?: RouteLocationRaw
    actionLabel?: string
  }>(),
  {
    isWished: false,
    to: undefined,
    badgeLabel: undefined,
    badgeVariant: undefined,
    pricePrefix: '',
    actionTo: undefined,
    actionLabel: undefined,
  },
)

const emit = defineEmits<{
  toggleWish: [productId: number]
}>()

const fallbackImageUrl =
  'https://images.unsplash.com/photo-1516762689617-e1cffcef479d?auto=format&fit=crop&w=900&q=80'
const productImageUrl = computed(() => props.product.primaryImageUrl || fallbackImageUrl)

const handleImageError = (event: Event) => {
  if (event.target instanceof HTMLImageElement) {
    event.target.onerror = null
    event.target.src = fallbackImageUrl
  }
}

const formatPrice = (value?: number) => {
  if (value === undefined) {
    return '시작가 미정'
  }

  return `${value.toLocaleString('ko-KR')}P`
}
</script>

<template>
  <article class="product-card">
    <RouterLink v-if="to" class="product-card__overlay-link" :to="to">
      <span class="product-card__overlay-text">{{ product.title }} 상세 보기</span>
    </RouterLink>
    <span class="product-card__media">
      <img
        class="product-card__image"
        :src="productImageUrl"
        :alt="product.title"
        @error="handleImageError"
      />
      <span
        v-if="badgeLabel"
        class="product-card__tag"
        :class="{
          'product-card__tag--auction': badgeVariant === 'auction',
          'product-card__tag--direct': badgeVariant === 'direct',
        }"
      >
        {{ badgeLabel }}
      </span>
      <button
        class="product-card__wish"
        :class="{ 'product-card__wish--active': isWished }"
        type="button"
        :aria-label="isWished ? `${product.title} 찜 해제` : `${product.title} 찜하기`"
        :aria-pressed="isWished"
        @click="emit('toggleWish', product.id)"
      >
        <svg aria-hidden="true" viewBox="0 0 24 24">
          <path
            d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78L12 21.23l8.84-8.84a5.5 5.5 0 0 0 0-7.78Z"
          />
        </svg>
      </button>
    </span>
    <span class="product-card__body">
      <span class="product-card__brand">{{ product.brandName }}</span>
      <span class="product-card__seller">판매자 {{ product.sellerName }}</span>
      <strong class="product-card__title">{{ product.title }}</strong>
      <span class="product-card__price">{{ pricePrefix }}{{ formatPrice(product.price) }}</span>
      <span class="product-card__meta">{{ product.categoryName }}</span>
      <span v-if="product.startingBid" class="product-card__bid">
        경매 시작가 {{ formatPrice(product.startingBid) }}
      </span>
      <RouterLink v-if="actionTo && actionLabel" class="product-card__action" :to="actionTo">
        {{ actionLabel }}
      </RouterLink>
    </span>
  </article>
</template>

<style scoped lang="scss">
// 카드 자체는 박스(테두리/배경)를 두르지 않는다 — 페이지 배경과 자연스럽게 연결하고,
// 얇은 border는 이미지 프레임에만 준다. hover도 뜨는 대신 이미지/보더 대비만 미세하게 바뀐다.
.product-card {
  position: relative;
  display: grid;
  gap: var(--space-2);
}

.product-card__overlay-link {
  position: absolute;
  z-index: 2;
  inset: 0;
}

.product-card__overlay-text {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  border: 0;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
}

.product-card__media {
  position: relative;
  display: block;
  overflow: hidden;
  aspect-ratio: 4 / 5;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-media);
  background: var(--color-image-frame);
  transition: border-color 220ms ease;
}

.product-card:hover .product-card__media {
  border-color: var(--color-border-strong);
}

.product-card__media::after {
  position: absolute;
  inset: 0;
  background: linear-gradient(0deg, rgba(10, 10, 10, 0.55), transparent 42%);
  content: '';
}

.product-card__image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  filter: saturate(0.88) contrast(1.04) brightness(0.95);
  transition: filter 220ms ease;
}

.product-card:hover .product-card__image {
  filter: saturate(0.88) contrast(1.04) brightness(1.03);
}

.product-card__tag {
  position: absolute;
  z-index: 1;
  top: 0;
  left: 0;
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 10px;
  border-radius: 0 0 var(--radius-badge) 0;
  background: rgba(10, 10, 10, 0.82);
  color: var(--color-text-primary);
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 500;
  letter-spacing: 0.08em;
  line-height: 18px;
}

.product-card__tag--auction {
  background: var(--color-accent);
}

.product-card__tag--direct {
  background: rgba(10, 10, 10, 0.82);
}

.product-card__wish {
  position: absolute;
  z-index: 3;
  top: var(--space-2);
  right: var(--space-2);
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-badge);
  background: rgba(10, 10, 10, 0.55);
  color: var(--color-text-secondary);
  backdrop-filter: blur(2px);
}

.product-card__wish svg {
  width: 20px;
  height: 20px;
  fill: transparent;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.8;
}

.product-card__wish:hover,
.product-card__wish--active {
  color: var(--color-auction);
}

.product-card__wish--active svg {
  fill: currentColor;
}

.product-card__wish:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

.product-card__body {
  display: grid;
  gap: var(--space-1);
  padding: var(--space-2) 0 0;
}

.product-card__brand {
  color: var(--color-text-muted);
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 500;
  letter-spacing: 0.16em;
  line-height: 18px;
  text-transform: uppercase;
}

.product-card__seller,
.product-card__meta {
  color: var(--color-text-muted);
  font-size: 12px;
  font-weight: 300;
  line-height: 18px;
}

.product-card__title {
  display: -webkit-box;
  overflow: hidden;
  margin-top: 2px;
  color: var(--color-text-primary);
  font-size: 17px;
  font-weight: 600;
  line-height: 24px;
  letter-spacing: -0.01em;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.product-card__price {
  margin-top: 2px;
  color: var(--color-text-primary);
  font-family: var(--font-mono);
  font-size: 18px;
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 24px;
  font-variant-numeric: tabular-nums;
}

.product-card__bid {
  color: var(--color-accent);
  font-family: var(--font-mono);
  font-weight: 500;
  letter-spacing: -0.02em;
  font-variant-numeric: tabular-nums;
  font-size: 13px;
}

.product-card__action {
  position: relative;
  z-index: 3;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: fit-content;
  height: 36px;
  padding: 0 var(--space-4);
  justify-self: end;
  margin-top: var(--space-2);
  border-radius: var(--radius-control);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-size: 13px;
  font-weight: 500;
  line-height: 20px;
  transition:
    background-color 220ms ease,
    color 220ms ease;
}

.product-card__action:hover {
  background: var(--color-primary-hover);
  color: var(--color-primary-strong);
}

@media (max-width: 520px) {
  .product-card__title {
    font-size: 15px;
    line-height: 22px;
  }
}
</style>
