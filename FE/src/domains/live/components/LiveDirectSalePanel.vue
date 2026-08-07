<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '@/domains/auth/stores/authStore'
import { ROUTE_NAMES } from '@/shared/constants/routes'

import type { LiveWatchProduct, LiveWatchStatus } from '@/domains/live/types/liveWatch.types'

const props = defineProps<{
  product: LiveWatchProduct
  liveStatus: LiveWatchStatus
  isHost: boolean
  message: string
}>()

const emit = defineEmits<{
  purchase: []
}>()

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const slideValue = ref(0)

const isOnSale = computed(
  () =>
    props.product.saleType === 'DIRECT_SALE' &&
    props.product.saleStatus === 'ON_SALE' &&
    props.product.price !== null,
)

const canPurchase = computed(
  () => props.liveStatus === 'LIVE' && isOnSale.value && authStore.isAuthenticated && !props.isHost,
)

const statusLabel = computed(() => {
  if (props.product.saleStatus === 'SOLD') return '판매 완료'
  if (isOnSale.value) return '상시 판매'
  return '판매 준비 중'
})

const sliderLabel = computed(() => {
  if (props.isHost) return '내 상품은 구매할 수 없습니다'
  if (!authStore.isAuthenticated) return '로그인 후 구매 가능'
  if (props.liveStatus !== 'LIVE') return '방송 중에 구매할 수 있습니다'
  if (props.product.saleStatus === 'SOLD') return '판매 완료된 상품입니다'
  if (!isOnSale.value) return '구매 준비 중입니다'
  return '오른쪽으로 밀어서 정찰제 구매'
})

const completeSlide = () => {
  if (slideValue.value >= 95 && canPurchase.value) {
    emit('purchase')
  }

  slideValue.value = 0
}

const goToLogin = () => {
  void router.push({
    name: ROUTE_NAMES.AUTH_LOGIN,
    query: { redirect: route.fullPath },
  })
}

watch(
  () => props.product.id,
  () => {
    slideValue.value = 0
  },
)
</script>

<template>
  <aside class="live-direct-sale-panel" aria-labelledby="live-direct-sale-title">
    <div class="live-direct-sale-panel__header">
      <h2 id="live-direct-sale-title">정찰제 구매</h2>
      <span
        class="live-direct-sale-panel__status"
        :class="{ 'live-direct-sale-panel__status--sold': product.saleStatus === 'SOLD' }"
      >
        {{ statusLabel }}
      </span>
    </div>

    <div class="live-direct-sale-panel__product">
      <span>선택 상품</span>
      <strong>{{ product.title }}</strong>
    </div>

    <div class="live-direct-sale-panel__price">
      <span>판매 가격</span>
      <strong>
        {{
          product.price === null ? '가격 정보 준비 중' : `${product.price.toLocaleString('ko-KR')}P`
        }}
      </strong>
    </div>

    <div
      class="live-direct-sale-panel__slider"
      :class="{ 'live-direct-sale-panel__slider--disabled': !canPurchase }"
      :style="{ '--slide-progress': `${slideValue}%` }"
    >
      <input
        v-model.number="slideValue"
        type="range"
        min="0"
        max="100"
        step="1"
        :disabled="!canPurchase"
        :aria-label="
          product.price === null
            ? '정찰제 구매 준비 중'
            : `${product.price.toLocaleString('ko-KR')}포인트 정찰제 구매`
        "
        @change="completeSlide"
      />
      <span aria-hidden="true">{{ sliderLabel }}</span>
    </div>

    <button
      v-if="!authStore.isAuthenticated"
      class="live-direct-sale-panel__login"
      type="button"
      @click="goToLogin"
    >
      로그인
    </button>

    <p v-if="message" class="live-direct-sale-panel__message" role="status">
      {{ message }}
    </p>
    <p class="live-direct-sale-panel__guide">
      밀기 완료 후 배송지와 보유 포인트를 확인하고 결제합니다.
    </p>
  </aside>
</template>

<style scoped lang="scss">
.live-direct-sale-panel {
  display: flex;
  min-width: 0;
  min-height: 0;
  flex-direction: column;
  gap: var(--space-3);
  padding: 16px 18px;
  border-top: 1px solid var(--color-live-border);
  border-left: 1px solid var(--color-live-border);
  background: var(--color-surface-raised);
}

.live-direct-sale-panel__header,
.live-direct-sale-panel__price {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}

.live-direct-sale-panel h2 {
  color: var(--color-accent);
  font-family: var(--font-mono);
  font-size: var(--font-size-2xs);
  font-weight: var(--font-weight-regular);
  letter-spacing: 0.2em;
  line-height: var(--line-height-tight);
  text-transform: uppercase;
}

.live-direct-sale-panel__status {
  padding: 3px 8px;
  border-radius: var(--radius-badge);
  background: color-mix(in srgb, var(--color-accent) 18%, transparent);
  color: var(--color-accent);
  font-size: var(--font-size-badge);
  font-weight: var(--font-weight-bold);
}

.live-direct-sale-panel__status--sold {
  background: var(--color-live-background);
  color: var(--color-live-text-secondary);
}

.live-direct-sale-panel__product {
  display: grid;
  min-width: 0;
  gap: 3px;
}

.live-direct-sale-panel__product span,
.live-direct-sale-panel__price span,
.live-direct-sale-panel__guide {
  color: var(--color-live-text-secondary);
  font-size: var(--font-size-2xs);
}

.live-direct-sale-panel__product strong {
  overflow: hidden;
  color: var(--color-live-text-primary);
  font-size: var(--font-size-caption);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.live-direct-sale-panel__price strong {
  color: var(--color-accent);
  font-family: var(--font-mono);
  font-size: var(--font-size-xl);
  font-variant-numeric: tabular-nums;
}

.live-direct-sale-panel__slider {
  position: relative;
  flex-shrink: 0;
  height: var(--button-height-compact);
  overflow: hidden;
  border: 1px solid var(--color-accent);
  border-radius: 999px;
  background: linear-gradient(
    90deg,
    color-mix(in srgb, var(--color-accent) 35%, transparent) 0 var(--slide-progress),
    var(--color-live-background) var(--slide-progress) 100%
  );
}

.live-direct-sale-panel__slider input {
  position: absolute;
  z-index: 2;
  inset: 0;
  width: 100%;
  height: 100%;
  margin: 0;
  appearance: none;
  background: transparent;
  cursor: grab;
}

.live-direct-sale-panel__slider input:active {
  cursor: grabbing;
}

.live-direct-sale-panel__slider input::-webkit-slider-thumb {
  width: 36px;
  height: 36px;
  border: 0;
  border-radius: 50%;
  appearance: none;
  background: var(--color-accent);
  box-shadow: 0 0 0 2px var(--color-live-background);
}

.live-direct-sale-panel__slider input::-moz-range-thumb {
  width: 36px;
  height: 36px;
  border: 0;
  border-radius: 50%;
  background: var(--color-accent);
}

.live-direct-sale-panel__slider > span {
  display: grid;
  position: absolute;
  z-index: 1;
  inset: 0;
  padding-left: 42px;
  color: var(--color-live-text-primary);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-bold);
  pointer-events: none;
  place-items: center;
}

.live-direct-sale-panel__slider--disabled {
  border-color: var(--color-live-border);
  opacity: 0.65;
}

.live-direct-sale-panel__login {
  min-height: var(--button-height-2xs);
  border: 1px solid var(--color-live-border);
  border-radius: var(--radius-control);
  background: var(--color-live-background);
  color: var(--color-live-text-primary);
  font-size: var(--font-size-xs);
}

.live-direct-sale-panel__message {
  color: var(--color-accent);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-bold);
}

.live-direct-sale-panel__guide {
  margin-top: auto;
  line-height: var(--line-height-snug);
}
</style>
