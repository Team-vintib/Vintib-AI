<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'

import {
  configureAuction,
  getAuctionErrorMessage,
  getCurrentAuction,
  startAuction,
} from '@/domains/auction/api/auctionApi'
import {
  SELLER_AUCTION_DEFAULT_CONFIG,
  SELLER_AUCTION_DEFAULT_START_PRICE,
  SELLER_AUCTION_DURATION_PRESETS,
  SELLER_AUCTION_INCREMENT_PRESETS,
  SELLER_AUCTION_MIN_DURATION_SECONDS,
} from '@/domains/auction/constants/sellerAuctionOptions'

import type { AuctionSnapshot } from '@/domains/auction/types/liveAuction.types'
import type {
  LiveWatchProduct,
  LiveWatchStatus,
} from '@/domains/live/types/liveWatch.types'

const props = defineProps<{
  liveId: number
  product: LiveWatchProduct | null
  status: LiveWatchStatus
  snapshot: AuctionSnapshot | null
  isLoading: boolean
  loadError: string
}>()

const emit = defineEmits<{
  'snapshot-change': [snapshot: AuctionSnapshot]
  'auction-closed': [snapshot: AuctionSnapshot]
}>()

const startPrice = ref(SELLER_AUCTION_DEFAULT_START_PRICE)
const increment = ref(SELLER_AUCTION_DEFAULT_CONFIG.increment)
const durationSeconds = ref(SELLER_AUCTION_DEFAULT_CONFIG.durationSeconds)
const isStarting = ref(false)
const actionError = ref('')
const dismissedTerminalAuctionId = ref<number | null>(null)
const lastEmittedClosedAuctionId = ref<number | null>(null)
const clockNow = ref(Date.now())
const snapshotReceivedAt = ref(Date.now())
const remainingAtReceiptMs = ref(0)

const activeSnapshot = computed(() => {
  const snapshot = props.snapshot

  if (!snapshot || dismissedTerminalAuctionId.value === snapshot.auctionId) {
    return null
  }

  if (snapshot.status === 'READY' || snapshot.status === 'RUNNING') {
    return snapshot
  }

  return snapshot.productId === props.product?.id ? snapshot : null
})

const isDurationValid = computed(
  () =>
    Number.isFinite(durationSeconds.value) &&
    durationSeconds.value >= SELLER_AUCTION_MIN_DURATION_SECONDS,
)

const isConfigValid = computed(
  () =>
    Number.isFinite(startPrice.value) &&
    startPrice.value >= 0 &&
    Number.isFinite(increment.value) &&
    increment.value > 0 &&
    isDurationValid.value,
)

// 이미 판매(낙찰·즉시구매)된 상품은 경매를 다시 시작할 수 없다(BE 035 §2 — saleStatus로 판별).
const isProductSold = computed(() => props.product?.saleStatus === 'SOLD')

const canStart = computed(
  () =>
    props.product !== null &&
    !isProductSold.value &&
    props.status === 'LIVE' &&
    isConfigValid.value &&
    !isStarting.value &&
    activeSnapshot.value?.status !== 'RUNNING',
)

const remainingSeconds = computed(() => {
  if (activeSnapshot.value?.status !== 'RUNNING' || !activeSnapshot.value.endsAt) {
    return 0
  }

  const elapsed = clockNow.value - snapshotReceivedAt.value
  return Math.max(0, Math.ceil((remainingAtReceiptMs.value - elapsed) / 1000))
})

const formattedRemaining = computed(() => {
  const minutes = Math.floor(remainingSeconds.value / 60)
  const seconds = remainingSeconds.value % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
})

const durationLabel = computed(() => {
  const minutes = Math.floor(durationSeconds.value / 60)
  const seconds = durationSeconds.value % 60

  if (minutes > 0 && seconds === 0) return `${minutes}분`
  if (minutes > 0) return `${minutes}분 ${seconds}초`
  return `${seconds}초`
})

const phaseLabel = computed(() => {
  if (activeSnapshot.value?.status === 'RUNNING') return '진행 중'
  if (activeSnapshot.value?.status === 'READY') return '시작 대기'
  if (activeSnapshot.value?.status === 'SUCCESS') return '낙찰'
  if (activeSnapshot.value?.status === 'FAILED') return '유찰'
  return '설정'
})

const applyDurationPreset = (seconds: number) => {
  actionError.value = ''
  durationSeconds.value = seconds
}

const applyIncrementPreset = (value: number) => {
  actionError.value = ''
  increment.value = value
}

const runAuctionStart = async () => {
  if (!canStart.value || !props.product) return

  isStarting.value = true
  actionError.value = ''

  try {
    const auctionId =
      activeSnapshot.value?.status === 'READY'
        ? activeSnapshot.value.auctionId
        : (
            await configureAuction(props.liveId, {
              productId: props.product.id,
              startPrice: startPrice.value,
              bidUnit: increment.value,
              durationSeconds: durationSeconds.value,
            })
          ).id
    const snapshot = await startAuction(auctionId)
    emit('snapshot-change', snapshot)
  } catch (error) {
    actionError.value = getAuctionErrorMessage(error)
    const latestSnapshot = await getCurrentAuction(props.liveId).catch(() => null)
    if (latestSnapshot) {
      emit('snapshot-change', latestSnapshot)
    }
  } finally {
    isStarting.value = false
  }
}

const prepareNextAuction = () => {
  dismissedTerminalAuctionId.value = activeSnapshot.value?.auctionId ?? null
  actionError.value = ''
}

watch(
  () => props.product?.id,
  () => {
    actionError.value = ''
    dismissedTerminalAuctionId.value = null
    startPrice.value = props.product?.price ?? SELLER_AUCTION_DEFAULT_START_PRICE
  },
  { immediate: true },
)

watch(
  () => props.snapshot,
  (snapshot) => {
    snapshotReceivedAt.value = Date.now()
    remainingAtReceiptMs.value =
      snapshot?.endsAt && snapshot.serverNow
        ? Math.max(0, new Date(snapshot.endsAt).getTime() - new Date(snapshot.serverNow).getTime())
        : 0

    if (
      snapshot &&
      (snapshot.status === 'SUCCESS' || snapshot.status === 'FAILED') &&
      lastEmittedClosedAuctionId.value !== snapshot.auctionId
    ) {
      lastEmittedClosedAuctionId.value = snapshot.auctionId
      emit('auction-closed', snapshot)
    }
  },
  { immediate: true },
)

const clockTimer = window.setInterval(() => {
  clockNow.value = Date.now()
}, 250)

onBeforeUnmount(() => {
  window.clearInterval(clockTimer)
})
</script>

<template>
  <section class="seller-auction" aria-labelledby="seller-auction-title">
    <div class="seller-auction__header">
      <h2 id="seller-auction-title">
        경매 설정<span v-if="product" class="seller-auction__product"> · {{ product.title }}</span>
      </h2>
      <span class="seller-auction__phase" :class="`seller-auction__phase--${activeSnapshot?.status.toLowerCase() || 'idle'}`">
        {{ phaseLabel }}
      </span>
    </div>

    <p v-if="isLoading" class="seller-auction__empty" role="status">
      경매 정보를 불러오는 중입니다.
    </p>
    <p v-else-if="loadError" class="seller-auction__hint seller-auction__hint--error" role="alert">
      {{ loadError }}
    </p>
    <p v-else-if="!product" class="seller-auction__empty">
      경매를 진행할 상품을 선택해 주세요.
    </p>

    <template v-else-if="activeSnapshot?.status === 'RUNNING'">
      <p class="seller-auction__target">
        <span>진행 상품</span>
        <strong>{{ activeSnapshot.productTitle || product.title }}</strong>
      </p>

      <div class="seller-auction__metrics">
        <div class="seller-auction__metric seller-auction__metric--current">
          <span>현재가</span>
          <strong>
            {{
              activeSnapshot.currentPrice > 0
                ? `${activeSnapshot.currentPrice.toLocaleString('ko-KR')}P`
                : '입찰 전'
            }}
          </strong>
        </div>
        <div class="seller-auction__metric">
          <span>남은 시간</span>
          <strong :class="{ 'seller-auction__timer--urgent': remainingSeconds <= 10 }">
            {{ formattedRemaining }}
          </strong>
        </div>
        <div class="seller-auction__metric">
          <span>최고 입찰자</span>
          <strong>{{ activeSnapshot.highestBidderNickname ?? '입찰 대기 중' }}</strong>
        </div>
        <div class="seller-auction__metric">
          <span>입찰 수</span>
          <strong>{{ activeSnapshot.bidCount.toLocaleString('ko-KR') }}회</strong>
        </div>
      </div>

      <p v-if="activeSnapshot.extensionCount > 0" class="seller-auction__extend">
        종료 직전 입찰로 {{ activeSnapshot.extensionCount }}회 자동 연장됐습니다.
      </p>
      <p v-else-if="remainingSeconds === 0" class="seller-auction__hint">
        서버의 경매 마감 결과를 기다리고 있습니다.
      </p>
    </template>

    <template v-else-if="activeSnapshot?.status === 'READY'">
      <p class="seller-auction__target">
        <span>설정 완료 상품</span>
        <strong>{{ activeSnapshot.productTitle || product.title }}</strong>
      </p>
      <dl class="seller-auction__ready">
        <div><dt>시작가</dt><dd>{{ activeSnapshot.startPrice.toLocaleString('ko-KR') }}P</dd></div>
        <div><dt>입찰 단위</dt><dd>{{ activeSnapshot.bidUnit.toLocaleString('ko-KR') }}P</dd></div>
        <div><dt>진행 시간</dt><dd>{{ activeSnapshot.durationSeconds }}초</dd></div>
      </dl>
      <button class="seller-auction__start" type="button" :disabled="!canStart" @click="runAuctionStart">
        {{ isStarting ? '경매 시작 중' : '설정된 경매 시작' }}
      </button>
    </template>

    <template v-else-if="activeSnapshot?.status === 'SUCCESS'">
      <div class="seller-auction__result seller-auction__result--won">
        <strong>낙찰되었습니다.</strong>
        <dl>
          <div><dt>낙찰자</dt><dd>{{ activeSnapshot.highestBidderNickname }}</dd></div>
          <div><dt>낙찰가</dt><dd>{{ activeSnapshot.currentPrice.toLocaleString('ko-KR') }}P</dd></div>
        </dl>
      </div>
      <button class="seller-auction__relist" type="button" @click="prepareNextAuction">
        다음 경매 설정
      </button>
    </template>

    <template v-else-if="activeSnapshot?.status === 'FAILED'">
      <div class="seller-auction__result seller-auction__result--failed">
        <strong>유찰되었습니다.</strong>
        <p>상품은 경매 예정 상태로 돌아갔습니다.</p>
      </div>
      <button class="seller-auction__relist" type="button" @click="prepareNextAuction">
        다시 경매 설정
      </button>
    </template>

    <template v-else-if="isProductSold">
      <p class="seller-auction__target">
        <span>대상 상품</span>
        <strong>{{ product.title }}</strong>
      </p>
      <div class="seller-auction__result seller-auction__result--failed">
        <strong>이미 판매된 상품입니다.</strong>
        <p>판매 완료된 상품은 경매를 시작할 수 없습니다.</p>
      </div>
    </template>

    <template v-else>
      <div class="seller-auction__fields">
        <div class="seller-auction__field">
        <label for="seller-auction-start-price">시작가</label>
        <div class="seller-auction__input">
          <input id="seller-auction-start-price" v-model.number="startPrice" type="number" min="0" step="1000" inputmode="numeric" />
          <span>P</span>
        </div>
      </div>

      <div class="seller-auction__field">
        <span class="seller-auction__label">입찰 단위</span>
        <div class="seller-auction__presets">
          <button
            v-for="preset in SELLER_AUCTION_INCREMENT_PRESETS"
            :key="preset"
            type="button"
            :class="{ 'seller-auction__preset--active': increment === preset }"
            @click="applyIncrementPreset(preset)"
          >
            {{ preset.toLocaleString('ko-KR') }}
          </button>
        </div>
        <div class="seller-auction__input">
          <input v-model.number="increment" type="number" min="1" step="1000" inputmode="numeric" aria-label="입찰 단위 직접 입력" />
          <span>P</span>
        </div>
      </div>

      <div class="seller-auction__field">
        <span class="seller-auction__label">진행 시간</span>
        <div class="seller-auction__presets">
          <button
            v-for="preset in SELLER_AUCTION_DURATION_PRESETS"
            :key="preset.seconds"
            type="button"
            :class="{ 'seller-auction__preset--active': durationSeconds === preset.seconds }"
            @click="applyDurationPreset(preset.seconds)"
          >
            {{ preset.label }}
          </button>
        </div>
        <div class="seller-auction__input">
          <input v-model.number="durationSeconds" type="number" :min="SELLER_AUCTION_MIN_DURATION_SECONDS" step="10" inputmode="numeric" aria-label="진행 시간 직접 입력(초)" />
          <span>초</span>
        </div>
        <p v-if="!isDurationValid" class="seller-auction__hint seller-auction__hint--error">
          1초 이상의 진행 시간을 입력해 주세요.
        </p>
        <p v-else class="seller-auction__hint">{{ durationLabel }} 동안 진행합니다.</p>
        </div>
      </div>

      <button class="seller-auction__start" type="button" :disabled="!canStart" @click="runAuctionStart">
        {{ isStarting ? '경매 시작 중' : '경매 시작' }}
      </button>
      <p v-if="status !== 'LIVE'" class="seller-auction__hint">방송 중일 때 경매를 시작할 수 있습니다.</p>
    </template>

    <p v-if="actionError" class="seller-auction__hint seller-auction__hint--error" role="alert">
      {{ actionError }}
    </p>
  </section>
</template>

<style scoped lang="scss">
.seller-auction {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-4);
  border: 1px solid var(--color-live-border);
  border-radius: var(--radius-control);
  background: var(--color-live-surface);
}

/* 경매 설정 필드(시작가·입찰단위·진행시간)를 가로로 펼쳐 짧은 하단 영역에서 스크롤 없이 보이게 */
.seller-auction__fields {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
}

.seller-auction__fields > .seller-auction__field {
  flex: 1 1 160px;
}

.seller-auction__header,
.seller-auction__ready div,
.seller-auction__result dl div {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.seller-auction__header h2 {
  min-width: 0;
  overflow: hidden;
  color: var(--color-live-text-primary);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-bold);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.seller-auction__product {
  color: var(--color-live-text-secondary);
  font-weight: var(--font-weight-regular);
}

.seller-auction__header .seller-auction__phase {
  flex-shrink: 0;
}

.seller-auction__phase {
  display: inline-flex;
  align-items: center;
  min-height: var(--badge-height-xs);
  padding: 0 8px;
  border-radius: var(--radius-badge);
  background: var(--color-live-surface-raised);
  color: var(--color-live-text-secondary);
  font-size: var(--font-size-badge);
  font-weight: var(--font-weight-bold);
}

.seller-auction__phase--running {
  background: var(--color-auction);
  color: var(--color-primary-strong);
}

.seller-auction__phase--success {
  background: var(--color-live);
  color: var(--color-text-inverse);
}

.seller-auction__empty,
.seller-auction__hint {
  color: var(--color-live-text-secondary);
  font-size: var(--font-size-xs);
  line-height: var(--line-height-snug);
}

.seller-auction__target {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--color-live-border);
}

.seller-auction__target span,
.seller-auction__field > label,
.seller-auction__label,
.seller-auction__metric span,
.seller-auction__ready dt,
.seller-auction__result dt {
  color: var(--color-live-text-secondary);
  font-size: var(--font-size-badge);
}

.seller-auction__target strong {
  overflow: hidden;
  color: var(--color-live-text-primary);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-bold);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.seller-auction__field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.seller-auction__presets {
  display: flex;
  gap: 6px;
}

.seller-auction__presets button {
  flex: 1;
  min-height: var(--badge-height-lg);
  border: 1px solid var(--color-live-border);
  border-radius: var(--radius-control);
  background: var(--color-live-background);
  color: var(--color-live-text-secondary);
  font-size: var(--font-size-2xs);
  font-weight: var(--font-weight-semibold);
}

.seller-auction__preset--active {
  border-color: var(--color-auction) !important;
  background: color-mix(in srgb, var(--color-auction) 18%, transparent) !important;
  color: var(--color-primary-strong) !important;
}

.seller-auction__input {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0 10px;
  border: 1px solid var(--color-live-border);
  border-radius: var(--radius-control);
  background: var(--color-live-background);
}

.seller-auction__input input {
  width: 100%;
  height: var(--button-height-2xs);
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--color-live-text-primary);
  font-family: var(--font-mono);
  font-size: var(--font-size-caption);
  font-variant-numeric: tabular-nums;
}

.seller-auction__input span {
  color: var(--color-live-text-secondary);
  font-size: var(--font-size-xs);
}

.seller-auction__hint--error {
  color: var(--color-error);
}

.seller-auction__start,
.seller-auction__relist {
  min-height: var(--button-height-compact);
  border: 0;
  border-radius: var(--radius-control);
  background: var(--color-auction);
  color: var(--color-primary-strong);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-bold);
}

.seller-auction__start:disabled {
  background: var(--color-live-surface-raised);
  color: var(--color-live-text-secondary);
}

.seller-auction__metrics {
  display: grid;
  gap: var(--space-2);
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.seller-auction__metric strong,
.seller-auction__ready dd,
.seller-auction__result dd {
  display: block;
  margin-top: 1px;
  overflow: hidden;
  color: var(--color-live-text-primary);
  font-family: var(--font-mono);
  font-size: var(--font-size-caption);
  font-variant-numeric: tabular-nums;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.seller-auction__metric--current strong {
  color: var(--color-auction);
  font-size: 20px;
  font-weight: var(--font-weight-bold);
}

.seller-auction__timer--urgent {
  color: var(--color-timer) !important;
}

.seller-auction__extend {
  padding: 6px 10px;
  border-radius: var(--radius-control);
  background: color-mix(in srgb, var(--color-timer) 18%, transparent);
  color: var(--color-timer);
  font-size: var(--font-size-2xs);
  font-weight: var(--font-weight-bold);
  text-align: center;
}

.seller-auction__ready,
.seller-auction__result dl {
  display: grid;
  gap: 6px;
}

.seller-auction__result {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-4);
  border-radius: var(--radius-control);
}

.seller-auction__result--won {
  background: color-mix(in srgb, var(--color-live) 16%, transparent);
}

.seller-auction__result--failed {
  background: var(--color-live-surface-raised);
}

.seller-auction__result > strong {
  color: var(--color-live-text-primary);
  font-size: var(--font-size-body);
}

.seller-auction__result p {
  color: var(--color-live-text-secondary);
  font-size: var(--font-size-xs);
}

.seller-auction__relist {
  border: 1px solid var(--color-live-border);
  background: var(--color-live-background);
  color: var(--color-live-text-primary);
}

.seller-auction button:focus-visible,
.seller-auction input:focus-visible {
  outline: 2px solid var(--color-ai);
  outline-offset: 2px;
}
</style>
