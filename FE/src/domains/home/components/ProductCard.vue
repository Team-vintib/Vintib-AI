<script setup lang="ts">
import { RouterLink } from 'vue-router'

import type { HomeProductCardItem } from '@/domains/home/types/homeView.types'
import type { RouteLocationRaw } from 'vue-router'

withDefaults(
  defineProps<{
    product: HomeProductCardItem
    to?: RouteLocationRaw
    badgeLabel?: string
    badgeVariant?: 'direct' | 'auction'
    pricePrefix?: string
    actionTo?: RouteLocationRaw
    actionLabel?: string
  }>(),
  {
    to: undefined,
    badgeLabel: undefined,
    badgeVariant: undefined,
    pricePrefix: '',
    actionTo: undefined,
    actionLabel: undefined,
  },
)

const fallbackImageUrl =
  'https://images.unsplash.com/photo-1516762689617-e1cffcef479d?auto=format&fit=crop&w=900&q=80'

const handleImageError = (event: Event) => {
  if (event.target instanceof HTMLImageElement) {
    event.target.onerror = null
    event.target.src = fallbackImageUrl
  }
}

const formatPrice = (value?: number) => {
  if (value === undefined) {
    return '가격 확인'
  }

  return `${value.toLocaleString('ko-KR')}원`
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
        :src="product.primaryImageUrl"
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
.product-card {
  position: relative;
  display: grid;
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

.product-card:hover {
  border-color: #ded8ce;
  box-shadow: 0 10px 26px rgb(18 18 18 / 7%);
  transform: translateY(-2px);
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
  aspect-ratio: 16 / 9;
  background: var(--color-surface-secondary);
}

.product-card__media::after {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(14, 17, 16, 0.04), rgba(14, 17, 16, 0.5));
  content: '';
}

.product-card__image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.product-card__tag {
  position: absolute;
  z-index: 1;
  top: var(--space-2);
  left: var(--space-2);
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 10px;
  border-radius: var(--space-2);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-size: 12px;
  font-weight: 700;
  line-height: 18px;
}

.product-card__tag--auction {
  background: var(--color-auction);
}

.product-card__tag--direct {
  background: var(--color-direct-sale);
}

.product-card__body {
  display: grid;
  gap: var(--space-1);
  padding: var(--space-5);
}

.product-card__brand {
  color: var(--color-primary);
  font-size: 13px;
  font-weight: 600;
  line-height: 20px;
}

.product-card__seller,
.product-card__meta {
  color: var(--color-text-muted);
  font-size: 13px;
  font-weight: 400;
  line-height: 20px;
}

.product-card__title {
  display: -webkit-box;
  overflow: hidden;
  color: var(--color-text-primary);
  font-size: 18px;
  font-weight: 700;
  line-height: 26px;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.product-card__price,
.product-card__bid {
  color: var(--color-text-primary);
  font-size: 14px;
  font-weight: 800;
  line-height: 21px;
}

.product-card__bid {
  color: var(--color-auction);
}

.product-card__action {
  position: relative;
  z-index: 3;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: fit-content;
  height: 40px;
  padding: 0 var(--space-4);
  justify-self: end;
  margin-top: var(--space-2);
  border-radius: 12px;
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-size: 14px;
  font-weight: 600;
  line-height: 20px;
}

@media (max-width: 520px) {
  .product-card__title {
    font-size: 15px;
    line-height: 22px;
  }
}
</style>
