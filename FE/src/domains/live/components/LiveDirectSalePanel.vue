<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '@/domains/auth/stores/authStore'
import AppInlineNotice from '@/shared/components/AppInlineNotice.vue'
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
    <!-- 상품명·판매 상태는 바로 위 "선택한 상품 정보"에 이미 떠 있다 — 여기는 가격과
         구매 수단만 남긴다. -->
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

    <AppInlineNotice v-if="message" variant="success">
      {{ message }}
    </AppInlineNotice>
  </aside>
</template>

<style scoped lang="scss">
/* 상품 큐 아래 사이드바(280px)에서 "선택한 상품 정보" 설명 바로 밑에 이어 붙는다 —
   구분선이나 별도 배경 없이 같은 덩어리로 보이게 둔다. */
.live-direct-sale-panel {
  display: flex;
  min-width: 0;
  min-height: 0;
  flex-direction: column;
  gap: var(--space-2);
  padding: 0 15px 15px;
}

.live-direct-sale-panel__price {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}

.live-direct-sale-panel__price span {
  color: var(--color-live-text-secondary);
  font-size: var(--font-size-2xs);
}

.live-direct-sale-panel__price strong {
  color: var(--color-accent);
  font-family: var(--font-mono);
  font-size: var(--font-size-lg);
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
</style>
