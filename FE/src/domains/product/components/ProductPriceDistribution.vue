<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import type { SimilarProductPricePoint } from '@/domains/product/types/productDetail.types'

const props = defineProps<{
  currentProductId: number
  currentPrice: number
  products: SimilarProductPricePoint[]
}>()

const emit = defineEmits<{
  viewProduct: [productId: number]
}>()

interface ProductPriceBand {
  start: number
  end: number
  label: string
  products: SimilarProductPricePoint[]
}

const MAX_VISIBLE_PRODUCTS = 3
const selectedBandStart = ref<number | null>(null)

const availableProducts = computed(() =>
  props.products.filter((product) => product.id !== props.currentProductId),
)

const bandStep = computed(() => {
  const prices = [...availableProducts.value.map((product) => product.price), props.currentPrice]
  const minimum = Math.min(...prices)
  const maximum = Math.max(...prices)
  const tenThousandBandCount =
    Math.floor(maximum / 10000) - Math.floor(minimum / 10000) + 1

  return tenThousandBandCount > 6 ? Math.ceil(tenThousandBandCount / 6) * 10000 : 10000
})

const formatBandLabel = (start: number, step: number) => {
  const startInTenThousands = start / 10000

  if (step === 10000) return `${startInTenThousands}만원대`

  const endInTenThousands = (start + step) / 10000
  return `${startInTenThousands}–${endInTenThousands}만원`
}

const priceBands = computed<ProductPriceBand[]>(() => {
  const prices = [...availableProducts.value.map((product) => product.price), props.currentPrice]
  const step = bandStep.value
  const minimum = Math.floor(Math.min(...prices) / step) * step
  const maximum = Math.floor(Math.max(...prices) / step) * step
  const bands: ProductPriceBand[] = []

  for (let start = minimum; start <= maximum; start += step) {
    bands.push({
      start,
      end: start + step,
      label: formatBandLabel(start, step),
      products: availableProducts.value
        .filter((product) => product.price >= start && product.price < start + step)
        .sort((first, second) => first.price - second.price),
    })
  }

  return bands
})

const maximumProductCount = computed(() =>
  Math.max(...priceBands.value.map((band) => band.products.length), 1),
)

const selectedBand = computed(() =>
  priceBands.value.find((band) => band.start === selectedBandStart.value),
)

const visibleSelectedProducts = computed(
  () => selectedBand.value?.products.slice(0, MAX_VISIBLE_PRODUCTS) ?? [],
)

const getBarHeight = (productCount: number) => {
  if (productCount === 0) return '8%'
  return `${Math.max(24, (productCount / maximumProductCount.value) * 100)}%`
}

const formatPrice = (price: number) => `${price.toLocaleString('ko-KR')}P`

const selectBand = (band: ProductPriceBand) => {
  if (band.products.length === 0) return
  selectedBandStart.value = band.start
}

watch(
  priceBands,
  (bands) => {
    const nextBand = bands.reduce<ProductPriceBand | undefined>((mostPopulated, band) => {
      if (!mostPopulated || band.products.length > mostPopulated.products.length) return band
      return mostPopulated
    }, undefined)

    selectedBandStart.value = nextBand?.start ?? null
  },
  { immediate: true },
)
</script>

<template>
  <section
    v-if="availableProducts.length > 0"
    class="price-distribution"
    aria-labelledby="price-distribution-title"
  >
    <div class="price-distribution__layout">
      <div class="price-distribution__chart">
        <div class="price-distribution__heading">
          <div>
            <h2 id="price-distribution-title">유사 상품 가격대</h2>
            <p>비슷한 상품이 많이 등록된 가격대를 확인해 보세요.</p>
          </div>
          <span class="price-distribution__current-price">
            현재 상품 {{ formatPrice(currentPrice) }}
          </span>
        </div>

        <div
          class="price-distribution__histogram"
          role="group"
          aria-label="가격대별 유사 상품 수"
        >
          <button
            v-for="band in priceBands"
            :key="band.start"
            class="price-distribution__column"
            :class="{ 'price-distribution__column--selected': selectedBandStart === band.start }"
            type="button"
            :disabled="band.products.length === 0"
            :aria-label="`${band.label}, 유사 상품 ${band.products.length}개`"
            :aria-pressed="selectedBandStart === band.start"
            @click="selectBand(band)"
          >
            <span class="price-distribution__count">{{ band.products.length }}개</span>
            <span class="price-distribution__bar-track" aria-hidden="true">
              <span
                class="price-distribution__bar"
                :style="{ height: getBarHeight(band.products.length) }"
              ></span>
            </span>
            <span class="price-distribution__band-label">{{ band.label }}</span>
          </button>
        </div>
      </div>

      <div v-if="selectedBand" class="price-distribution__products" aria-live="polite">
        <div class="price-distribution__products-heading">
          <div>
            <span>선택한 가격대</span>
            <strong>{{ selectedBand.label }} 유사 상품</strong>
          </div>
          <span>{{ visibleSelectedProducts.length }}개</span>
        </div>

        <div class="price-distribution__product-list">
          <button
            v-for="product in visibleSelectedProducts"
            :key="product.id"
            class="price-distribution__product"
            type="button"
            @click="emit('viewProduct', product.id)"
          >
            <span>{{ product.title }}</span>
            <strong>{{ formatPrice(product.price) }}</strong>
            <svg aria-hidden="true" viewBox="0 0 24 24">
              <path d="m9 18 6-6-6-6" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped lang="scss">
.price-distribution {
  margin-top: var(--space-10);
  padding: var(--space-8) 0;
  border-top: 1px solid var(--color-border);
  border-bottom: 1px solid var(--color-border);
}

.price-distribution__layout {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(320px, 0.8fr);
  align-items: stretch;
  gap: var(--space-10);
}

.price-distribution__chart {
  min-width: 0;
}

.price-distribution__heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
}

.price-distribution__heading h2 {
  color: var(--color-text-primary);
  font-size: var(--font-size-md-plus);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-body);
}

.price-distribution__heading p {
  margin-top: var(--space-1);
  color: var(--color-text-muted);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-regular);
  line-height: var(--line-height-snug);
}

.price-distribution__current-price {
  flex: 0 0 auto;
  padding: 5px var(--space-3);
  border: 1px solid var(--color-border-input);
  border-radius: var(--radius-badge);
  background: transparent;
  color: var(--color-text-secondary);
  font-family: var(--font-mono);
  font-size: var(--font-size-2xs);
  font-variant-numeric: tabular-nums;
  font-weight: var(--font-weight-regular);
  letter-spacing: -0.01em;
  line-height: var(--line-height-snug);
  white-space: nowrap;
}

.price-distribution__histogram {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(54px, 1fr));
  align-items: end;
  gap: var(--space-2);
  margin-top: var(--space-6);
}

.price-distribution__column {
  min-width: 0;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--color-text-muted);
  text-align: center;
}

.price-distribution__count {
  display: block;
  margin-bottom: var(--space-2);
  font-family: var(--font-mono);
  font-size: var(--font-size-2xs);
  font-variant-numeric: tabular-nums;
  font-weight: var(--font-weight-medium);
  line-height: var(--line-height-xs);
}

.price-distribution__bar-track {
  display: flex;
  height: 112px;
  align-items: flex-end;
  justify-content: center;
}

.price-distribution__bar {
  display: block;
  width: min(100%, 44px);
  min-height: 3px;
  border-radius: 0;
  background: var(--color-border-strong);
  transition:
    height var(--transition-moderate),
    background-color var(--transition-base);
}

.price-distribution__band-label {
  display: block;
  margin-top: var(--space-2);
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-snug);
  white-space: nowrap;
}

.price-distribution__column:not(:disabled):hover .price-distribution__bar {
  background: var(--color-text-muted);
}

.price-distribution__column--selected {
  color: var(--color-primary);
}

.price-distribution__column--selected .price-distribution__bar {
  background: var(--color-primary);
}

.price-distribution__column--selected .price-distribution__band-label {
  color: var(--color-primary);
}

.price-distribution__column:disabled {
  cursor: default;
  opacity: 0.5;
}

.price-distribution__column:focus-visible {
  border-radius: var(--radius-control);
  outline: 2px solid var(--color-primary);
  outline-offset: var(--focus-ring-offset);
}

.price-distribution__products {
  display: flex;
  min-width: 0;
  flex-direction: column;
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface-secondary);
}

.price-distribution__products-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
}

.price-distribution__products-heading > div > span {
  display: block;
  margin-bottom: 2px;
  color: var(--color-primary);
  font-size: var(--font-size-2xs);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-xs);
}

.price-distribution__products-heading strong {
  display: block;
  color: var(--color-text-primary);
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-body);
}

.price-distribution__products-heading > span {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-snug);
}

.price-distribution__product-list {
  margin-top: var(--space-4);
}

.price-distribution__product {
  display: grid;
  width: 100%;
  min-height: var(--button-height-compact);
  grid-template-columns: minmax(0, 1fr) auto 18px;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-primary);
  text-align: left;
  transition:
    border-color var(--transition-base),
    color var(--transition-base);
}

.price-distribution__product + .price-distribution__product {
  margin-top: var(--space-2);
}

.price-distribution__product > span {
  overflow: hidden;
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-snug);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.price-distribution__product > strong {
  font-family: var(--font-mono);
  font-size: var(--font-size-caption);
  font-variant-numeric: tabular-nums;
  font-weight: var(--font-weight-medium);
  letter-spacing: -0.02em;
  line-height: var(--line-height-snug);
  white-space: nowrap;
}

.price-distribution__product svg {
  width: var(--icon-size-sm);
  height: var(--icon-size-sm);
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.8;
}

.price-distribution__product:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.price-distribution__product:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

@media (max-width: 480px) {
  .price-distribution__heading {
    display: block;
  }

  .price-distribution__current-price {
    display: inline-flex;
    margin-top: var(--space-3);
  }

  .price-distribution__histogram {
    grid-template-columns: repeat(auto-fit, minmax(48px, 1fr));
    gap: var(--space-1);
  }

  .price-distribution__bar-track {
    height: 96px;
  }
}

@media (max-width: 940px) {
  .price-distribution__layout {
    grid-template-columns: 1fr;
    gap: var(--space-6);
  }

}

@media (prefers-reduced-motion: reduce) {
  .price-distribution__bar {
    transition: none;
  }
}
</style>
