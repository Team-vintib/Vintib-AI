<script setup lang="ts">
import { computed } from 'vue'

import type {
  ProductDetailViewData,
  ProductSellerSummary,
} from '@/domains/product/types/productDetail.types'

const props = defineProps<{
  product: ProductDetailViewData
  seller: ProductSellerSummary
  isLiked: boolean
}>()

const emit = defineEmits<{
  toggleLike: []
  openTryOn: []
  purchase: []
  goLive: []
  viewSeller: []
}>()

const isAuction = computed(() => props.product.saleType === 'AUCTION')

const formattedPrice = computed(() => {
  if (isAuction.value) {
    return '경매 예정'
  }

  const price = `${props.product.price.toLocaleString('ko-KR')}P`
  return price
})

const saleTypeLabel = computed(() =>
  isAuction.value ? '경매 예정' : '정찰제',
)

const breadcrumb = computed(() =>
  [saleTypeLabel.value, props.product.category.trim()].filter(Boolean).join(' · '),
)

const quickInfoItems = computed(() =>
  [
    { label: '상품 상태', value: props.product.conditionLabel },
    { label: '사이즈', value: props.product.sizeLabel },
    { label: '색상', value: props.product.color },
  ]
    .map((item) => ({ ...item, value: item.value.trim() }))
    .filter((item) => item.value),
)

const isAuctionInProgress = computed(
  () => props.product.saleStatus === 'AUCTION_IN_PROGRESS',
)

// 경매 진행 중 상품은 라이브에서만 입찰할 수 있으므로, 연결 라이브가 실제 LIVE일 때만 이동 가능.
const canJoinLiveAuction = computed(
  () => isAuctionInProgress.value && props.product.linkedLive?.status === 'LIVE',
)

const purchaseLabel = computed(() => {
  if (props.product.saleStatus === 'SOLD') return '판매 완료'
  if (props.product.saleStatus === 'AUCTION_SCHEDULED') return '경매 예정'
  if (props.product.saleStatus === 'AUCTION_IN_PROGRESS') {
    return canJoinLiveAuction.value ? '라이브에서 입찰하기' : '경매 진행 중'
  }
  if (props.product.saleStatus === 'AUCTION_FAILED') return '경매 종료'
  return '구매하기'
})

// 정찰제 판매중(ON_SALE)만 실제 구매로 연결한다. 경매(예정/진행/종료)·판매완료·비공개는
// 구매 흐름으로 보내지 않으며, 진행 중 경매만 라이브 입장으로 대체한다.
const isPurchaseDisabled = computed(() => {
  if (isAuctionInProgress.value) return !canJoinLiveAuction.value

  return ['DRAFT', 'SOLD', 'AUCTION_FAILED', 'AUCTION_SCHEDULED'].includes(
    props.product.saleStatus,
  )
})

const handlePrimaryAction = () => {
  if (canJoinLiveAuction.value) {
    emit('goLive')
    return
  }

  emit('purchase')
}

const sellerNickname = computed(() => props.seller.nickname?.trim() || '판매자')
const sellerInitial = computed(() => sellerNickname.value.slice(0, 1).toUpperCase())
</script>

<template>
  <section class="purchase-summary" aria-labelledby="product-title">
    <p class="purchase-summary__breadcrumb">{{ breadcrumb }}</p>
    <h1 id="product-title" class="purchase-summary__title">{{ product.title }}</h1>
    <p
      class="purchase-summary__price"
      :class="{ 'purchase-summary__price--status': isAuction }"
    >
      {{ formattedPrice }}
    </p>

    <article class="purchase-summary__seller">
      <div class="purchase-summary__avatar" aria-hidden="true">
        {{ sellerInitial }}
      </div>
      <div>
        <strong>{{ sellerNickname }}</strong>
        <p>
          팔로워 {{ seller.followerCount.toLocaleString('ko-KR') }}명 · 판매 상품
          {{ seller.productCount }}개
        </p>
      </div>
      <button type="button" @click="emit('viewSeller')">판매자 프로필 보기</button>
    </article>

    <dl v-if="quickInfoItems.length" class="purchase-summary__quick-info">
      <div v-for="item in quickInfoItems" :key="item.label">
        <dt>{{ item.label }}</dt>
        <dd>{{ item.value }}</dd>
      </div>
    </dl>

    <div class="purchase-summary__actions">
      <button
        class="purchase-summary__secondary"
        :class="{ 'purchase-summary__secondary--liked': isLiked }"
        type="button"
        :aria-label="isLiked ? '상품 찜 해제' : '상품 찜하기'"
        :aria-pressed="isLiked"
        @click="emit('toggleLike')"
      >
        <svg aria-hidden="true" viewBox="0 0 24 24">
          <path
            d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78L12 21.23l8.84-8.84a5.5 5.5 0 0 0 0-7.78Z"
          />
        </svg>
        찜
      </button>
      <button
        class="purchase-summary__secondary purchase-summary__secondary--ai"
        type="button"
        @click="emit('openTryOn')"
      >
        <svg aria-hidden="true" viewBox="0 0 24 24">
          <path
            d="m12 3 1.3 4.2L17.5 9l-4.2 1.8L12 15l-1.3-4.2L6.5 9l4.2-1.8L12 3Zm6 12 .7 2.3L21 18l-2.3.7L18 21l-.7-2.3L15 18l2.3-.7L18 15Z"
          />
        </svg>
        AI 시착
      </button>
    </div>

    <button
      class="purchase-summary__purchase"
      type="button"
      :disabled="isPurchaseDisabled"
      @click="handlePrimaryAction"
    >
      {{ purchaseLabel }}
    </button>
  </section>
</template>

<style scoped lang="scss">
.purchase-summary {
  align-self: start;
  padding-top: var(--space-2);
}

.purchase-summary__breadcrumb {
  color: var(--color-text-secondary);
  font-size: var(--font-size-body);
  font-weight: var(--font-weight-medium);
  line-height: var(--line-height-body);
}

.purchase-summary__title {
  margin-top: var(--space-3);
  color: var(--color-text-primary);
  font-family: var(--font-display);
  font-size: var(--font-size-3xl-plus);
  font-weight: var(--font-weight-semibold);
  letter-spacing: -0.03em;
  line-height: 1.08;
}

.purchase-summary__price {
  margin-top: var(--space-3);
  color: var(--color-text-primary);
  font-family: var(--font-mono);
  font-size: var(--font-size-hero-display);
  font-variant-numeric: tabular-nums;
  font-weight: var(--font-weight-medium);
  letter-spacing: -0.03em;
  line-height: 1.1;
}

.purchase-summary__price--status {
  font-family: inherit;
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
  letter-spacing: -0.02em;
  line-height: var(--line-height-xl);
}

.purchase-summary__seller {
  display: grid;
  grid-template-columns: 44px minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--space-3);
  margin-top: var(--space-8);
  padding: var(--space-4) 0;
  border-top: 1px solid var(--color-border);
  border-bottom: 1px solid var(--color-border);
}

.purchase-summary__avatar {
  display: grid;
  width: var(--button-height-compact);
  height: var(--button-height-compact);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-badge);
  background: var(--color-surface-secondary);
  color: var(--color-text-primary);
  font-family: var(--font-mono);
  font-size: var(--font-size-body);
  font-weight: var(--font-weight-medium);
  place-items: center;
}

.purchase-summary__seller strong {
  font-size: var(--font-size-md-plus);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-body);
}

.purchase-summary__seller p {
  margin-top: 2px;
  color: var(--color-text-secondary);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-regular);
  line-height: var(--line-height-relaxed);
}

.purchase-summary__seller button {
  height: var(--button-height-2xs);
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-snug);
  transition:
    border-color var(--transition-base),
    color var(--transition-base);
}

.purchase-summary__quick-info {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 1px;
  margin-top: var(--space-6);
  border: 1px solid var(--color-border-grid);
  border-radius: var(--radius-control);
  background: var(--color-border-grid);
  overflow: hidden;
}

.purchase-summary__quick-info div {
  min-width: 0;
  padding: var(--space-4);
  background: var(--color-surface);
}

.purchase-summary__quick-info dt {
  color: var(--color-text-secondary);
  font-family: var(--font-mono);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-regular);
  letter-spacing: 0.06em;
  line-height: var(--line-height-snug);
  text-transform: uppercase;
}

.purchase-summary__quick-info dd {
  overflow: hidden;
  margin-top: var(--space-1);
  color: var(--color-text-primary);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-lg);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.purchase-summary__actions {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-2);
  margin-top: var(--space-4);
}

.purchase-summary__secondary {
  display: flex;
  height: var(--button-height-compact);
  align-items: center;
  justify-content: center;
  gap: 6px;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  font-size: var(--font-size-body);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-control);
  transition:
    border-color var(--transition-base),
    background-color var(--transition-base),
    color var(--transition-base);
}

.purchase-summary__secondary svg {
  width: var(--icon-size-xs-plus);
  height: var(--icon-size-xs-plus);
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.7;
}

.purchase-summary__purchase {
  width: 100%;
  height: var(--button-height-major);
  margin-top: var(--space-3);
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-control);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-size: var(--font-size-body);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-control);
  transition: background-color var(--transition-base);
}

.purchase-summary__seller button:hover,
.purchase-summary__secondary:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.purchase-summary__secondary:hover {
  background: var(--color-primary-soft);
}

.purchase-summary__secondary--liked {
  border-color: var(--color-auction);
  background: var(--color-auction-soft);
  color: var(--color-auction);
}

.purchase-summary__secondary--liked svg {
  fill: currentColor;
}

.purchase-summary__secondary--ai,
.purchase-summary__secondary--ai:hover {
  border-color: var(--color-ai);
  background: var(--color-ai-soft);
  color: var(--color-ai);
}

.purchase-summary__secondary--ai:focus-visible {
  outline-color: var(--color-ai-soft);
}

.purchase-summary__purchase:hover {
  border-color: var(--color-primary-hover);
  background: var(--color-primary-hover);
  color: var(--color-primary-strong);
}

.purchase-summary__purchase:disabled {
  cursor: not-allowed;
  border-color: var(--color-border);
  background: var(--color-surface-secondary);
  color: var(--color-text-muted);
}

.purchase-summary__secondary:disabled {
  cursor: not-allowed;
  border-color: var(--color-border);
  background: var(--color-surface-secondary);
  color: var(--color-text-muted);
}

.purchase-summary button:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

@media (max-width: 480px) {
  .purchase-summary__seller {
    grid-template-columns: 44px 1fr;
  }

  .purchase-summary__seller button {
    grid-column: 1 / -1;
  }
}
</style>
