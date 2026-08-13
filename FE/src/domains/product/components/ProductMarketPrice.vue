<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { getProductMarketPrice } from '@/domains/product/api/productApi'
import type {
  ProductMarketPrice,
  ProductMarketPriceItem,
} from '@/domains/product/types/productDetail.types'
import { ROUTE_NAMES } from '@/shared/constants/routes'

// SY046: "동일 상품 시세"(docs/requests/FE/042 반영) — matchKey 기준 동일 상품의 호가/완료거래가.
// 카테고리 기준 "유사 상품 가격대"(ProductPriceDistribution.vue)와는 별개 기능이다.
const props = defineProps<{
  productId: number
}>()

const router = useRouter()

const marketPrice = ref<ProductMarketPrice | null>(null)
const loadState = ref<'loading' | 'loaded' | 'error'>('loading')

const listings = computed(() => marketPrice.value?.listings ?? [])
const hasListings = computed(() => Boolean(marketPrice.value?.matchKey) && listings.value.length > 0)

const priceKindLabel = (kind: ProductMarketPriceItem['priceKind']) => {
  if (kind === 'SOLD_DIRECT') return '직접판매 완료'
  if (kind === 'SOLD_AUCTION') return '경매 낙찰'
  return '판매중 호가'
}

const formatPrice = (value: number) => `${value.toLocaleString('ko-KR')}P`

const load = async (productId: number) => {
  loadState.value = 'loading'

  try {
    marketPrice.value = await getProductMarketPrice(productId)
    loadState.value = 'loaded'
  } catch {
    marketPrice.value = null
    loadState.value = 'error'
  }
}

const viewProduct = (targetProductId: number) => {
  void router.push({ name: ROUTE_NAMES.PRODUCT_DETAIL, params: { productId: targetProductId } })
}

watch(
  () => props.productId,
  () => {
    void load(props.productId)
  },
  { immediate: true },
)
</script>

<template>
  <section class="market-price" aria-labelledby="market-price-title">
    <div class="market-price__head">
      <h2 id="market-price-title">동일 상품 시세</h2>
    </div>

    <p v-if="loadState === 'loading'" class="market-price__state">시세를 불러오는 중…</p>
    <p v-else-if="loadState === 'error'" class="market-price__state">
      동일 상품 시세를 불러오지 못했습니다.
    </p>
    <p v-else-if="!hasListings" class="market-price__state">아직 동일 상품 시세 정보가 없어요.</p>

    <ul v-else class="market-price__list">
      <li v-for="item in listings" :key="item.productId" class="market-price__item">
        <button
          type="button"
          class="market-price__item-button"
          @click="viewProduct(item.productId)"
        >
          <span class="market-price__item-title">{{ item.title }}</span>
          <span
            class="market-price__item-kind"
            :class="`market-price__item-kind--${item.priceKind.toLowerCase()}`"
          >
            {{ priceKindLabel(item.priceKind) }}
          </span>
          <strong class="market-price__item-price">{{ formatPrice(item.price) }}</strong>
        </button>
      </li>
    </ul>
  </section>
</template>

<style scoped lang="scss">
.market-price {
  margin-top: var(--space-8);
}

.market-price__head {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: var(--space-4);
  margin-bottom: var(--space-4);
}

.market-price__head h2 {
  color: var(--color-text-primary);
  font-size: var(--font-size-2xl-plus);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-2xl-plus);
}

.market-price__state {
  padding: var(--space-6) 0;
  color: var(--color-text-muted);
  font-size: var(--font-size-button-small);
}

.market-price__list {
  display: grid;
  gap: var(--space-2);
  list-style: none;
}

.market-price__item-button {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  align-items: center;
  width: 100%;
  gap: var(--space-4);
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  text-align: left;
  transition:
    border-color var(--transition-base),
    background-color var(--transition-base);
}

.market-price__item-button:hover {
  border-color: var(--color-primary);
}

.market-price__item-button:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

.market-price__item-title {
  overflow: hidden;
  color: var(--color-text-primary);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-semibold);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.market-price__item-kind {
  padding: 3px var(--space-2);
  border-radius: var(--radius-badge);
  background: var(--color-surface-secondary);
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-xs);
  white-space: nowrap;
}

.market-price__item-kind--sold_direct,
.market-price__item-kind--sold_auction {
  background: var(--color-primary-soft);
  color: var(--color-primary);
}

.market-price__item-price {
  color: var(--color-text-primary);
  font-size: var(--font-size-button-small);
  font-variant-numeric: tabular-nums;
  font-weight: var(--font-weight-extrabold);
  white-space: nowrap;
}

@media (max-width: 520px) {
  .market-price__item-button {
    grid-template-columns: minmax(0, 1fr) auto;
    grid-template-areas:
      'title price'
      'kind kind';
    row-gap: var(--space-1);
  }

  .market-price__item-title {
    grid-area: title;
  }

  .market-price__item-price {
    grid-area: price;
  }

  .market-price__item-kind {
    justify-self: start;
    grid-area: kind;
  }
}
</style>
