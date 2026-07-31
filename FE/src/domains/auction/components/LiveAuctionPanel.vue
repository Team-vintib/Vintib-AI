<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'

import { LIVE_AUCTION_MOCK_SNAPSHOT } from '@/domains/auction/constants/liveAuctionMockData'

import type { LiveAuctionMockState } from '@/domains/auction/types/liveAuction.types'
import type {
  LiveWatchProduct,
  LiveWatchStatus,
} from '@/domains/live/types/liveWatch.types'

const props = withDefaults(
  defineProps<{
    product: LiveWatchProduct | null
    status: LiveWatchStatus
    mockState?: LiveAuctionMockState
  }>(),
  {
    mockState: 'BIDDABLE',
  },
)

// mock 경쟁자(다른 시청자) 닉네임. 실제 최고 입찰자는 BE 선착순 판정 결과로 대체.
const MOCK_COMPETITORS = ['bidder_99', 'vintage_lover', 'archive_king']
const BID_HOLD_MS = 3000
const EXTEND_THRESHOLD_SECONDS = 3 // 기능 정의서 AUCT-010
const EXTEND_SECONDS = 5

const currentBid = ref(LIVE_AUCTION_MOCK_SNAPSHOT.currentBid)
const highestBidder = ref(LIVE_AUCTION_MOCK_SNAPSHOT.highestBidder)
const remainingSeconds = ref(LIVE_AUCTION_MOCK_SNAPSHOT.remainingSeconds)
const localState = ref<LiveAuctionMockState>(props.mockState)
const isAuctionClosed = ref(false)
let competitorIndex = 0
let bidTimer: number | null = null
let holdTimer: number | null = null

const clearBidTimers = () => {
  if (bidTimer !== null) {
    window.clearTimeout(bidTimer)
    bidTimer = null
  }
  if (holdTimer !== null) {
    window.clearTimeout(holdTimer)
    holdTimer = null
  }
}

// 종료 임박(3초 이하)에 유효 입찰 시 +5초 연장(AUCT-010). 실제 연장 판정은 서버 몫.
// BE 확인 필요: 연장 시점·값은 docs/requests/BE/009 경매 정책 기준으로 대체.
const extendIfClosing = () => {
  if (remainingSeconds.value > 0 && remainingSeconds.value <= EXTEND_THRESHOLD_SECONDS) {
    remainingSeconds.value += EXTEND_SECONDS
  }
}

const nextBid = computed(() => currentBid.value + LIVE_AUCTION_MOCK_SNAPSHOT.increment)

const effectiveState = computed<LiveAuctionMockState | 'SCHEDULED' | 'ENDED' | 'EMPTY'>(() => {
  if (!props.product) return 'EMPTY'
  if (props.status === 'SCHEDULED') return 'SCHEDULED'
  if (props.status === 'ENDED' || props.status === 'CANCELED') return 'ENDED'
  if (isAuctionClosed.value || localState.value === 'WON' || localState.value === 'FAILED') {
    return 'ENDED'
  }
  if (nextBid.value > LIVE_AUCTION_MOCK_SNAPSHOT.availablePoints) return 'INSUFFICIENT_POINTS'
  return localState.value
})

const formattedRemainingTime = computed(() => {
  const minutes = Math.floor(remainingSeconds.value / 60)
  const seconds = remainingSeconds.value % 60

  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
})

const bidButtonLabel = computed(() => {
  if (effectiveState.value === 'PENDING') return '입찰 처리 중'
  if (effectiveState.value === 'LEADING') return '현재 최고 입찰자입니다'
  if (effectiveState.value === 'INSUFFICIENT_POINTS') return '포인트가 부족합니다'
  if (effectiveState.value === 'SCHEDULED') return '경매 시작 전입니다'
  if (effectiveState.value === 'ENDED') return '종료된 경매입니다'
  if (effectiveState.value === 'EMPTY') return '경매 상품이 없습니다'
  return `${nextBid.value.toLocaleString('ko-KR')}P 입찰하기`
})

const isBidDisabled = computed(() => effectiveState.value !== 'BIDDABLE')

const resetMockAuction = () => {
  currentBid.value = props.product?.price ?? LIVE_AUCTION_MOCK_SNAPSHOT.currentBid
  highestBidder.value =
    props.mockState === 'LEADING' ? '나' : LIVE_AUCTION_MOCK_SNAPSHOT.highestBidder
  remainingSeconds.value = LIVE_AUCTION_MOCK_SNAPSHOT.remainingSeconds
  localState.value = props.mockState
  isAuctionClosed.value = false
  competitorIndex = 0

  clearBidTimers()
}

const placeMockBid = () => {
  // AUCT-004 중복 클릭 방지: BIDDABLE 이 아니면(처리 중·홀드·종료) 무시한다.
  if (effectiveState.value !== 'BIDDABLE') return

  // AUCT-005 서버 기준 선착순 판정은 서버 몫 — 여기선 접수 흉내 후 확정한다.
  // BE 확인 필요: 실제 입찰/선착순은 docs/requests/BE/009.
  localState.value = 'PENDING'
  clearBidTimers()

  bidTimer = window.setTimeout(() => {
    currentBid.value = nextBid.value
    highestBidder.value = '나' // 입찰 확인 즉시 최고 입찰자 반영(AUCT-011)
    localState.value = 'LEADING'
    extendIfClosing()
    bidTimer = null

    // AUCT-006 연속 입찰 제한: 최근 성공자는 다른 사람이 입찰하기 전까지 재입찰 불가.
    // → 약 3초 홀드 후 mock 경쟁자가 더 높게 입찰하면 다시 입찰 가능(BIDDABLE) 상태로 돌아간다.
    holdTimer = window.setTimeout(() => {
      if (isAuctionClosed.value || remainingSeconds.value <= 0) return

      currentBid.value += LIVE_AUCTION_MOCK_SNAPSHOT.increment
      highestBidder.value = MOCK_COMPETITORS[competitorIndex % MOCK_COMPETITORS.length]
      competitorIndex += 1
      localState.value = 'BIDDABLE'
      extendIfClosing()
      holdTimer = null
    }, BID_HOLD_MS)
  }, 480)
}

watch(
  () => [props.product?.id, props.mockState, props.status],
  resetMockAuction,
  { immediate: true },
)

const countdownTimer = window.setInterval(() => {
  if (props.status !== 'LIVE' || remainingSeconds.value <= 0) return

  remainingSeconds.value -= 1

  // 정해진 경매 시간이 끝나면 입찰을 마감한다(종료).
  if (remainingSeconds.value <= 0) {
    isAuctionClosed.value = true
    clearBidTimers()
  }
}, 1000)

onBeforeUnmount(() => {
  window.clearInterval(countdownTimer)
  clearBidTimers()
})
</script>

<template>
  <aside class="live-auction-panel" aria-labelledby="live-auction-title">
    <h2 id="live-auction-title">실시간 경매</h2>

    <div class="live-auction-panel__metrics">
      <div class="live-auction-panel__metric live-auction-panel__metric--current">
        <span>현재 입찰가</span>
        <strong>{{ currentBid.toLocaleString('ko-KR') }}P</strong>
      </div>
      <div class="live-auction-panel__metric">
        <span>다음 입찰가</span>
        <strong>{{ nextBid.toLocaleString('ko-KR') }}P</strong>
      </div>
      <div class="live-auction-panel__metric">
        <span>남은 시간</span>
        <strong :class="{ 'live-auction-panel__timer--urgent': remainingSeconds <= 30 }">
          {{ formattedRemainingTime }}
        </strong>
      </div>
      <div class="live-auction-panel__metric">
        <span>최고 입찰자</span>
        <strong>{{ highestBidder }}</strong>
      </div>
    </div>

    <div class="live-auction-panel__actions">
      <div class="live-auction-panel__balance">
        <span>사용 가능</span>
        <strong>{{ LIVE_AUCTION_MOCK_SNAPSHOT.availablePoints.toLocaleString('ko-KR') }}P</strong>
      </div>
      <button
        type="button"
        :disabled="isBidDisabled"
        :aria-busy="effectiveState === 'PENDING'"
        @click="placeMockBid"
      >
        <span v-if="effectiveState === 'PENDING'" aria-hidden="true"></span>
        {{ bidButtonLabel }}
      </button>
    </div>
  </aside>
</template>

<style scoped lang="scss">
.live-auction-panel {
  display: grid;
  min-width: 0;
  min-height: 0;
  padding: 15px 15px 15px 14px;
  border-top: 1px solid var(--color-live-border);
  border-left: 1px solid var(--color-live-border);
  background: var(--color-live-background);
  grid-template-rows: 15px 45px 52px;
  row-gap: 10px;
}

.live-auction-panel h2 {
  color: var(--color-live-text-secondary);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.04em;
  line-height: 15px;
  text-transform: uppercase;
}

.live-auction-panel__metrics {
  display: flex;
  min-width: 0;
  align-items: flex-start;
  gap: var(--space-4);
}

.live-auction-panel__metric {
  min-width: 0;
}

.live-auction-panel__metric span,
.live-auction-panel__balance span {
  display: block;
  color: var(--color-live-text-secondary);
  font-size: 10px;
  line-height: 15px;
  white-space: nowrap;
}

.live-auction-panel__metric strong,
.live-auction-panel__balance strong {
  display: block;
  margin-top: 1px;
  color: var(--color-live-text-primary);
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  line-height: 22px;
  white-space: nowrap;
}

.live-auction-panel__metric--current {
  flex: 1 0 76px;
}

.live-auction-panel__metric--current strong {
  margin-top: 0;
  color: #c43d46;
  font-size: 20px;
  font-weight: 700;
  line-height: 30px;
}

.live-auction-panel__timer--urgent {
  color: var(--color-timer) !important;
}

.live-auction-panel__actions {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: var(--space-3);
}

.live-auction-panel__balance {
  width: 56px;
  flex: 0 0 56px;
}

.live-auction-panel__balance strong {
  font-size: 12px;
  font-weight: 700;
  line-height: 18px;
}

.live-auction-panel__actions button {
  display: inline-flex;
  min-width: 0;
  height: 52px;
  align-items: center;
  justify-content: center;
  padding: 0 var(--space-4);
  border: 0;
  border-radius: 9px;
  background: #c43d46;
  box-shadow: 0 6px 18px rgba(196, 61, 70, 0.2);
  gap: var(--space-2);
  color: #fff;
  font-size: 14px;
  font-weight: 650;
  flex: 1;
  white-space: nowrap;
}

.live-auction-panel__actions button:hover:not(:disabled) {
  background: var(--color-auction);
}

.live-auction-panel__actions button:disabled {
  cursor: not-allowed;
  background: var(--color-live-surface-raised);
  box-shadow: none;
  color: var(--color-live-text-secondary);
}

.live-auction-panel__actions button:focus-visible {
  outline: 3px solid #fff;
  outline-offset: 2px;
}

.live-auction-panel__actions button > span {
  width: 14px;
  height: 14px;
  border: 2px solid currentColor;
  border-top-color: transparent;
  border-radius: 50%;
  animation: live-auction-spin 700ms linear infinite;
}

@keyframes live-auction-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 1100px) {
  .live-auction-panel {
    padding-right: 12px;
    padding-left: 12px;
  }

  .live-auction-panel__metrics {
    gap: var(--space-2);
  }

  .live-auction-panel__metric--current strong {
    font-size: 18px;
  }

  .live-auction-panel__actions button {
    padding: 0 var(--space-2);
    font-size: 12px;
  }
}

@media (max-width: 720px) {
  .live-auction-panel {
    min-height: 164px;
    border-left: 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .live-auction-panel__actions button > span {
    animation: none;
  }
}
</style>
