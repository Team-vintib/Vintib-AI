<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'

import {
  SELLER_AUCTION_DEFAULT_CONFIG,
  SELLER_AUCTION_DEFAULT_START_PRICE,
  SELLER_AUCTION_DURATION_PRESETS,
  SELLER_AUCTION_DURATION_RANGE,
  SELLER_AUCTION_EXTEND_SECONDS,
  SELLER_AUCTION_EXTEND_THRESHOLD_SECONDS,
  SELLER_AUCTION_INCREMENT_PRESETS,
  SELLER_AUCTION_MOCK_BID_INTERVAL_SECONDS,
  SELLER_AUCTION_MOCK_COMPETITORS,
} from '@/domains/auction/constants/sellerAuctionMockData'

import type { SellerAuctionPhase } from '@/domains/auction/types/sellerAuction.types'
import type {
  LiveWatchProduct,
  LiveWatchStatus,
} from '@/domains/live/types/liveWatch.types'

const props = defineProps<{
  product: LiveWatchProduct | null
  status: LiveWatchStatus
}>()

// 경매 종료(낙찰/미낙찰) 결과를 상위(LiveBroadcastPage)로 알린다 — 441 판매자 낙찰 이벤트.
// 실제 종료/낙찰 확정은 서버 몫(docs/requests/BE/009) → 지금은 mock 타이머 종료 시점에 emit.
const emit = defineEmits<{
  'auction-ended': [
    result: {
      outcome: 'WON' | 'FAILED'
      winnerNickname: string | null
      winningBid: number
      productTitle: string | null
    },
  ]
}>()

const phase = ref<SellerAuctionPhase>('IDLE')
const startPrice = ref(SELLER_AUCTION_DEFAULT_START_PRICE)
const increment = ref(SELLER_AUCTION_DEFAULT_CONFIG.increment)
const durationSeconds = ref(SELLER_AUCTION_DEFAULT_CONFIG.durationSeconds)

const currentBid = ref(0)
const highestBidder = ref<string | null>(null)
const remainingSeconds = ref(0)
const bidderCount = ref(0)
const isExtendFlashing = ref(false)

let countdownTimer: number | undefined
let extendFlashTimer: number | undefined
let secondsElapsed = 0

const clearTimers = () => {
  window.clearInterval(countdownTimer)
  window.clearTimeout(extendFlashTimer)
  countdownTimer = undefined
  extendFlashTimer = undefined
}

const isDurationValid = computed(
  () =>
    Number.isFinite(durationSeconds.value) &&
    durationSeconds.value >= SELLER_AUCTION_DURATION_RANGE.min &&
    durationSeconds.value <= SELLER_AUCTION_DURATION_RANGE.max,
)

const isConfigValid = computed(
  () =>
    Number.isFinite(startPrice.value) &&
    startPrice.value > 0 &&
    Number.isFinite(increment.value) &&
    increment.value > 0 &&
    isDurationValid.value,
)

const canStart = computed(
  () => props.product !== null && props.status === 'LIVE' && isConfigValid.value,
)

const formattedRemaining = computed(() => {
  const total = Math.max(0, remainingSeconds.value)
  const minutes = Math.floor(total / 60)
  const seconds = total % 60

  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
})

const durationLabel = computed(() => {
  const minutes = Math.floor(durationSeconds.value / 60)
  const seconds = durationSeconds.value % 60

  if (minutes > 0 && seconds === 0) return `${minutes}분`
  if (minutes > 0) return `${minutes}분 ${seconds}초`

  return `${seconds}초`
})

const applyDurationPreset = (seconds: number) => {
  durationSeconds.value = seconds
}

const applyIncrementPreset = (value: number) => {
  increment.value = value
}

const resetToIdle = () => {
  clearTimers()
  phase.value = 'IDLE'
  currentBid.value = 0
  highestBidder.value = null
  remainingSeconds.value = 0
  bidderCount.value = 0
  isExtendFlashing.value = false
  secondsElapsed = 0
  startPrice.value = props.product?.price ?? SELLER_AUCTION_DEFAULT_START_PRICE
}

const flashExtend = () => {
  isExtendFlashing.value = true
  window.clearTimeout(extendFlashTimer)
  extendFlashTimer = window.setTimeout(() => {
    isExtendFlashing.value = false
  }, 1500)
}

// mock 가짜 입찰. 실제 입찰·선착순 판정은 서버 몫(docs/requests/BE/009).
const simulateBid = () => {
  currentBid.value += increment.value
  highestBidder.value =
    SELLER_AUCTION_MOCK_COMPETITORS[bidderCount.value % SELLER_AUCTION_MOCK_COMPETITORS.length]
  bidderCount.value += 1

  // AUCT-010 종료 직전 자동 연장(mock 연출).
  if (remainingSeconds.value <= SELLER_AUCTION_EXTEND_THRESHOLD_SECONDS) {
    remainingSeconds.value += SELLER_AUCTION_EXTEND_SECONDS
    flashExtend()
  }
}

const endAuction = () => {
  clearTimers()
  const won = bidderCount.value > 0
  phase.value = won ? 'ENDED_WON' : 'ENDED_FAILED'
  emit('auction-ended', {
    outcome: won ? 'WON' : 'FAILED',
    winnerNickname: highestBidder.value,
    winningBid: currentBid.value,
    productTitle: props.product?.title ?? null,
  })
}

const tick = () => {
  if (remainingSeconds.value <= 0) return

  remainingSeconds.value -= 1
  secondsElapsed += 1

  if (
    remainingSeconds.value > 0 &&
    secondsElapsed % SELLER_AUCTION_MOCK_BID_INTERVAL_SECONDS === 0
  ) {
    simulateBid()
  }

  if (remainingSeconds.value <= 0) {
    endAuction()
  }
}

const startAuction = () => {
  if (!canStart.value) return

  currentBid.value = startPrice.value
  highestBidder.value = null
  bidderCount.value = 0
  remainingSeconds.value = durationSeconds.value
  secondsElapsed = 0
  isExtendFlashing.value = false
  phase.value = 'RUNNING'

  clearTimers()
  countdownTimer = window.setInterval(tick, 1000)
}

// PROD-005 미낙찰 후속 판매 방식 선택은 내일 별도 구현 → 지금은 자리/링크만.
const relistPlaceholderNotice = ref(false)
const openRelistFlow = () => {
  relistPlaceholderNotice.value = true
}

watch(
  () => props.product?.id,
  () => {
    resetToIdle()
  },
  { immediate: true },
)

// 방송이 종료/취소되면 진행 중 경매도 정리한다.
watch(
  () => props.status,
  (status) => {
    if (status !== 'LIVE' && phase.value === 'RUNNING') {
      endAuction()
    }
  },
)

onBeforeUnmount(() => {
  clearTimers()
})
</script>

<template>
  <section class="seller-auction" aria-labelledby="seller-auction-title">
    <div class="seller-auction__header">
      <h2 id="seller-auction-title">경매 설정</h2>
      <span
        class="seller-auction__phase"
        :class="`seller-auction__phase--${phase.toLowerCase()}`"
      >
        {{
          phase === 'RUNNING'
            ? '진행 중'
            : phase === 'ENDED_WON'
              ? '낙찰'
              : phase === 'ENDED_FAILED'
                ? '미낙찰'
                : '설정'
        }}
      </span>
    </div>

    <!-- 상품 미선택 -->
    <p v-if="!product" class="seller-auction__empty">
      큐에서 상품을 선택하면 경매를 설정할 수 있습니다.
    </p>

    <!-- 설정 전(IDLE) -->
    <template v-else-if="phase === 'IDLE'">
      <p class="seller-auction__target">
        <span>경매 상품</span>
        <strong>{{ product.title }}</strong>
      </p>

      <div class="seller-auction__field">
        <label for="seller-auction-start-price">시작가</label>
        <div class="seller-auction__input">
          <input
            id="seller-auction-start-price"
            v-model.number="startPrice"
            type="number"
            min="0"
            step="1000"
            inputmode="numeric"
          />
          <span>P</span>
        </div>
      </div>

      <div class="seller-auction__field">
        <span class="seller-auction__label">증액 단위</span>
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
          <input
            v-model.number="increment"
            type="number"
            min="0"
            step="1000"
            inputmode="numeric"
            aria-label="증액 단위 직접 입력"
          />
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
          <input
            v-model.number="durationSeconds"
            type="number"
            :min="SELLER_AUCTION_DURATION_RANGE.min"
            :max="SELLER_AUCTION_DURATION_RANGE.max"
            step="10"
            inputmode="numeric"
            aria-label="진행 시간 직접 입력(초)"
          />
          <span>초</span>
        </div>
        <p v-if="!isDurationValid" class="seller-auction__hint seller-auction__hint--error">
          {{ SELLER_AUCTION_DURATION_RANGE.min }}~{{ SELLER_AUCTION_DURATION_RANGE.max }}초 사이로
          입력해 주세요.
        </p>
        <p v-else class="seller-auction__hint">{{ durationLabel }} 동안 진행됩니다.</p>
      </div>

      <button
        class="seller-auction__start"
        type="button"
        :disabled="!canStart"
        @click="startAuction"
      >
        경매 시작
      </button>
      <p v-if="status !== 'LIVE'" class="seller-auction__hint">
        방송 중일 때 경매를 시작할 수 있습니다.
      </p>
    </template>

    <!-- 진행 중(RUNNING) -->
    <template v-else-if="phase === 'RUNNING'">
      <p class="seller-auction__target">
        <span>경매 상품</span>
        <strong>{{ product.title }}</strong>
      </p>

      <div class="seller-auction__metrics">
        <div class="seller-auction__metric seller-auction__metric--current">
          <span>현재 입찰가</span>
          <strong>{{ currentBid.toLocaleString('ko-KR') }}P</strong>
        </div>
        <div class="seller-auction__metric">
          <span>남은 시간</span>
          <strong :class="{ 'seller-auction__timer--urgent': remainingSeconds <= 30 }">
            {{ formattedRemaining }}
          </strong>
        </div>
        <div class="seller-auction__metric">
          <span>최고 입찰자</span>
          <strong>{{ highestBidder ?? '입찰 대기 중' }}</strong>
        </div>
        <div class="seller-auction__metric">
          <span>참여 입찰</span>
          <strong>{{ bidderCount.toLocaleString('ko-KR') }}회</strong>
        </div>
      </div>

      <p v-if="isExtendFlashing" class="seller-auction__extend" role="status">
        종료 임박 · {{ SELLER_AUCTION_EXTEND_SECONDS }}초 연장
      </p>
      <p class="seller-auction__hint">경매는 남은 시간이 끝나면 자동 종료됩니다.</p>
    </template>

    <!-- 낙찰(ENDED_WON) -->
    <template v-else-if="phase === 'ENDED_WON'">
      <div class="seller-auction__result seller-auction__result--won">
        <strong>낙찰되었습니다</strong>
        <dl>
          <div>
            <dt>낙찰자</dt>
            <dd>{{ highestBidder }}</dd>
          </div>
          <div>
            <dt>낙찰가</dt>
            <dd>{{ currentBid.toLocaleString('ko-KR') }}P</dd>
          </div>
        </dl>
      </div>
    </template>

    <!-- 미낙찰(ENDED_FAILED, AUCT-014) -->
    <template v-else>
      <div class="seller-auction__result seller-auction__result--failed">
        <strong>미낙찰</strong>
        <p>입찰자가 없어 상품이 판매자 관리 목록으로 되돌아갑니다.</p>
      </div>
      <!-- PROD-005 판매 방식 선택은 내일 별도 구현 → 지금은 링크/자리만 -->
      <button class="seller-auction__relist" type="button" @click="openRelistFlow">
        판매 방식 선택
        <span class="seller-auction__soon">준비 중</span>
      </button>
      <p v-if="relistPlaceholderNotice" class="seller-auction__hint">
        판매 방식 선택(PROD-005)은 곧 연결됩니다.
      </p>
    </template>
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

.seller-auction__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.seller-auction__header h2 {
  color: var(--color-live-text-primary);
  font-size: 13px;
  font-weight: 700;
}

.seller-auction__phase {
  display: inline-flex;
  align-items: center;
  min-height: 22px;
  padding: 0 8px;
  border-radius: var(--radius-badge);
  background: var(--color-live-surface-raised);
  color: var(--color-live-text-secondary);
  font-size: 10px;
  font-weight: 700;
}

.seller-auction__phase--running {
  background: #c43d46;
  color: #fff;
}

.seller-auction__phase--ended_won {
  background: var(--color-live);
  color: var(--color-text-inverse);
}

.seller-auction__empty {
  color: var(--color-live-text-secondary);
  font-size: 12px;
  line-height: 18px;
}

.seller-auction__target {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--color-live-border);
}

.seller-auction__target span {
  color: var(--color-live-text-secondary);
  font-size: 10px;
}

.seller-auction__target strong {
  overflow: hidden;
  color: var(--color-live-text-primary);
  font-size: 13px;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.seller-auction__field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.seller-auction__field > label,
.seller-auction__label {
  color: var(--color-live-text-secondary);
  font-size: 11px;
  font-weight: 600;
}

.seller-auction__presets {
  display: flex;
  gap: 6px;
}

.seller-auction__presets button {
  flex: 1;
  min-height: 30px;
  border: 1px solid var(--color-live-border);
  border-radius: var(--radius-control);
  background: var(--color-live-background);
  color: var(--color-live-text-secondary);
  font-size: 11px;
  font-weight: 600;
}

.seller-auction__presets button:hover {
  color: var(--color-live-text-primary);
}

.seller-auction__preset--active {
  border-color: #c43d46 !important;
  background: color-mix(in srgb, #c43d46 18%, transparent) !important;
  color: #fff !important;
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
  height: 34px;
  border: 0;
  background: transparent;
  color: var(--color-live-text-primary);
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 13px;
  font-variant-numeric: tabular-nums;
}

.seller-auction__input input:focus {
  outline: none;
}

.seller-auction__input span {
  color: var(--color-live-text-secondary);
  font-size: 12px;
}

.seller-auction__hint {
  color: var(--color-live-text-secondary);
  font-size: 10px;
  line-height: 15px;
}

.seller-auction__hint--error {
  color: var(--color-error);
}

.seller-auction__start {
  min-height: 44px;
  margin-top: var(--space-1);
  border: 0;
  border-radius: 9px;
  background: #c43d46;
  box-shadow: 0 6px 18px rgba(196, 61, 70, 0.2);
  color: #fff;
  font-size: 14px;
  font-weight: 700;
}

.seller-auction__start:hover:not(:disabled) {
  background: var(--color-auction);
}

.seller-auction__start:disabled {
  background: var(--color-live-surface-raised);
  box-shadow: none;
  color: var(--color-live-text-secondary);
}

.seller-auction__metrics {
  display: grid;
  gap: var(--space-2);
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.seller-auction__metric {
  min-width: 0;
}

.seller-auction__metric span {
  display: block;
  color: var(--color-live-text-secondary);
  font-size: 10px;
}

.seller-auction__metric strong {
  display: block;
  margin-top: 1px;
  overflow: hidden;
  color: var(--color-live-text-primary);
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 13px;
  font-variant-numeric: tabular-nums;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.seller-auction__metric--current strong {
  color: #c43d46;
  font-size: 20px;
  font-weight: 700;
}

.seller-auction__timer--urgent {
  color: var(--color-timer) !important;
}

.seller-auction__extend {
  padding: 6px 10px;
  border-radius: var(--radius-control);
  background: color-mix(in srgb, var(--color-timer) 18%, transparent);
  color: var(--color-timer);
  font-size: 11px;
  font-weight: 700;
  text-align: center;
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

.seller-auction__result strong {
  color: var(--color-live-text-primary);
  font-size: 15px;
  font-weight: 800;
}

.seller-auction__result p {
  color: var(--color-live-text-secondary);
  font-size: 12px;
  line-height: 18px;
}

.seller-auction__result dl {
  display: grid;
  gap: 4px;
}

.seller-auction__result dl div {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.seller-auction__result dt {
  color: var(--color-live-text-secondary);
  font-size: 11px;
}

.seller-auction__result dd {
  color: var(--color-live-text-primary);
  font-size: 13px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.seller-auction__relist {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 40px;
  gap: 6px;
  border: 1px solid var(--color-live-border);
  border-radius: var(--radius-control);
  background: var(--color-live-background);
  color: var(--color-live-text-primary);
  font-size: 13px;
  font-weight: 700;
}

.seller-auction__soon {
  padding: 1px 6px;
  border-radius: var(--radius-badge);
  background: var(--color-live-surface-raised);
  color: var(--color-live-text-secondary);
  font-size: 9px;
  font-weight: 700;
}

.seller-auction__start:focus-visible,
.seller-auction__relist:focus-visible,
.seller-auction__presets button:focus-visible {
  outline: 2px solid var(--color-ai);
  outline-offset: 2px;
}
</style>
