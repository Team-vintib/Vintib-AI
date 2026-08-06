<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import {
  getAuctionErrorMessage,
  getCurrentAuction,
  placeAuctionBid,
} from '@/domains/auction/api/auctionApi'
import { useAuthStore } from '@/domains/auth/stores/authStore'
import { getPointBalance } from '@/domains/point/api/pointApi'
import { ROUTE_NAMES } from '@/shared/constants/routes'

import type { AuctionSnapshot } from '@/domains/auction/types/liveAuction.types'
import type { LiveWatchStatus } from '@/domains/live/types/liveWatch.types'

const props = defineProps<{
  snapshot: AuctionSnapshot | null
  liveStatus: LiveWatchStatus
  isLoading: boolean
  loadError: string
}>()

const emit = defineEmits<{
  'snapshot-change': [snapshot: AuctionSnapshot | null]
}>()

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const slideValue = ref(0)
const isSubmitting = ref(false)
const bidError = ref('')
const availablePoints = ref<number | null>(null)
const isBalanceLoading = ref(false)
const clockNow = ref(Date.now())
const snapshotReceivedAt = ref(Date.now())
const remainingAtReceiptMs = ref(0)

const updateCountdownAnchor = (snapshot: AuctionSnapshot | null) => {
  snapshotReceivedAt.value = Date.now()
  remainingAtReceiptMs.value =
    snapshot?.endsAt && snapshot.serverNow
      ? Math.max(0, new Date(snapshot.endsAt).getTime() - new Date(snapshot.serverNow).getTime())
      : 0
}

const remainingSeconds = computed(() => {
  if (!props.snapshot?.endsAt || props.snapshot.status !== 'RUNNING') {
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

const isHighestBidder = computed(
  () =>
    Boolean(authStore.user?.id) &&
    props.snapshot?.highestBidderId === authStore.user?.id,
)

const hasEnoughPoints = computed(
  () =>
    availablePoints.value !== null &&
    props.snapshot !== null &&
    availablePoints.value >= props.snapshot.nextBidPrice,
)

const canBid = computed(
  () =>
    props.liveStatus === 'LIVE' &&
    props.snapshot?.status === 'RUNNING' &&
    remainingSeconds.value > 0 &&
    authStore.isAuthenticated &&
    !isHighestBidder.value &&
    hasEnoughPoints.value &&
    !isSubmitting.value,
)

const sliderLabel = computed(() => {
  if (isSubmitting.value) return '입찰 처리 중'
  if (!authStore.isAuthenticated) return '로그인 후 입찰 가능'
  if (props.snapshot?.status !== 'RUNNING') return '경매 진행 대기'
  if (remainingSeconds.value <= 0) return '경매 마감 확인 중'
  if (isHighestBidder.value) return '현재 최고 입찰자입니다'
  if (isBalanceLoading.value) return '포인트 확인 중'
  if (!hasEnoughPoints.value) return '포인트가 부족합니다'
  return '오른쪽으로 밀어서 입찰'
})

const loadAvailablePoints = async () => {
  const userId = authStore.user?.id

  if (!authStore.isAuthenticated || !userId) {
    availablePoints.value = null
    return
  }

  isBalanceLoading.value = true

  try {
    availablePoints.value = (await getPointBalance(userId)).available
  } catch {
    availablePoints.value = null
  } finally {
    isBalanceLoading.value = false
  }
}

const submitBid = async () => {
  const snapshot = props.snapshot

  if (!snapshot || !canBid.value) {
    slideValue.value = 0
    return
  }

  isSubmitting.value = true
  bidError.value = ''

  try {
    const nextSnapshot = await placeAuctionBid(snapshot.auctionId, snapshot.nextBidPrice)
    emit('snapshot-change', nextSnapshot)
    await loadAvailablePoints()
  } catch (error) {
    bidError.value = getAuctionErrorMessage(error)

    try {
      emit('snapshot-change', await getCurrentAuction(snapshot.liveId))
    } catch {
      // 입찰 오류 문구를 유지하고 다음 STOMP snapshot을 기다린다.
    }
  } finally {
    isSubmitting.value = false
    slideValue.value = 0
  }
}

const completeSlide = () => {
  if (slideValue.value >= 95) {
    void submitBid()
    return
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
  () => props.snapshot,
  (snapshot, previousSnapshot) => {
    updateCountdownAnchor(snapshot)
    slideValue.value = 0

    if (
      authStore.user?.id &&
      previousSnapshot?.highestBidderId === authStore.user.id &&
      snapshot?.highestBidderId !== authStore.user.id
    ) {
      void loadAvailablePoints()
    }
  },
  { immediate: true },
)

watch(
  () => authStore.user?.id,
  () => {
    void loadAvailablePoints()
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
  <aside class="live-auction-panel" aria-labelledby="live-auction-title">
    <div class="live-auction-panel__header">
      <h2 id="live-auction-title">실시간 경매</h2>
      <span v-if="snapshot" class="live-auction-panel__status">
        {{
          snapshot.status === 'RUNNING'
            ? '진행 중'
            : snapshot.status === 'READY'
              ? '시작 대기'
              : snapshot.status === 'SUCCESS'
                ? '낙찰'
                : snapshot.status === 'FAILED'
                  ? '유찰'
                  : '종료'
        }}
      </span>
    </div>

    <div v-if="isLoading" class="live-auction-panel__empty" role="status">
      <strong>경매 정보를 불러오는 중입니다.</strong>
    </div>

    <div v-else-if="loadError" class="live-auction-panel__empty" role="alert">
      <strong>경매 정보를 불러오지 못했습니다.</strong>
      <p>{{ loadError }}</p>
    </div>

    <div v-else-if="!snapshot" class="live-auction-panel__empty">
      <strong>현재 진행 중인 경매가 없습니다.</strong>
      <p>판매자가 경매를 시작하면 이곳에 입찰 정보가 표시됩니다.</p>
    </div>

    <div v-else-if="snapshot.status === 'READY'" class="live-auction-panel__empty">
      <strong>{{ snapshot.productTitle || '선택 상품' }}</strong>
      <p>판매자가 경매 시작을 준비하고 있습니다.</p>
    </div>

    <div
      v-else-if="snapshot.status === 'SUCCESS' || snapshot.status === 'FAILED'"
      class="live-auction-panel__result"
    >
      <strong>{{ snapshot.status === 'SUCCESS' ? '낙찰 완료' : '유찰' }}</strong>
      <p v-if="snapshot.status === 'SUCCESS'">
        {{ snapshot.highestBidderNickname }} · {{ snapshot.currentPrice.toLocaleString('ko-KR') }}P
      </p>
      <p v-else>입찰 없이 경매가 종료되었습니다.</p>
    </div>

    <template v-else-if="snapshot.status === 'RUNNING'">
      <div class="live-auction-panel__metrics">
        <div>
          <span>현재 입찰가</span>
          <strong>
            {{
              snapshot.currentPrice > 0
                ? `${snapshot.currentPrice.toLocaleString('ko-KR')}P`
                : '입찰 전'
            }}
          </strong>
        </div>
        <div>
          <span>남은 시간</span>
          <strong :class="{ 'live-auction-panel__urgent': remainingSeconds <= 10 }">
            {{ formattedRemaining }}
          </strong>
        </div>
        <div
          class="live-auction-panel__bidder"
          :class="{ 'live-auction-panel__bidder--active': snapshot.highestBidderNickname }"
        >
          <span>최고 입찰자</span>
          <strong>{{ snapshot.highestBidderNickname || '입찰 대기 중' }}</strong>
        </div>
        <div>
          <span>입찰 수</span>
          <strong>{{ snapshot.bidCount.toLocaleString('ko-KR') }}회</strong>
        </div>
      </div>

      <div v-if="snapshot.extensionCount > 0" class="live-auction-panel__extension">
        자동 연장 {{ snapshot.extensionCount }}회
      </div>

      <div class="live-auction-panel__next">
        <span>다음 입찰가</span>
        <strong>{{ snapshot.nextBidPrice.toLocaleString('ko-KR') }}P</strong>
      </div>

      <div
        class="live-auction-panel__slider"
        :class="{ 'live-auction-panel__slider--disabled': !canBid }"
        :style="{ '--slide-progress': `${slideValue}%` }"
      >
        <input
          v-model.number="slideValue"
          type="range"
          min="0"
          max="100"
          step="1"
          :disabled="!canBid"
          :aria-label="`${snapshot.nextBidPrice.toLocaleString('ko-KR')}포인트 입찰`"
          @change="completeSlide"
        />
        <span aria-hidden="true">{{ sliderLabel }}</span>
      </div>

      <button
        v-if="!authStore.isAuthenticated"
        class="live-auction-panel__login"
        type="button"
        @click="goToLogin"
      >
        로그인
      </button>

      <p class="live-auction-panel__balance">
        사용 가능 포인트
        <strong>{{ availablePoints === null ? '-' : `${availablePoints.toLocaleString('ko-KR')}P` }}</strong>
      </p>
      <p v-if="bidError" class="live-auction-panel__error" role="alert">{{ bidError }}</p>
    </template>
  </aside>
</template>

<style scoped lang="scss">
.live-auction-panel {
  display: flex;
  min-width: 0;
  min-height: 0;
  flex-direction: column;
  gap: var(--space-3);
  overflow-y: auto;
  padding: 18px 24px;
  border-top: 1px solid var(--color-live-border);
  border-left: 1px solid var(--color-live-border);
  background: var(--color-surface-raised);
}

.live-auction-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.live-auction-panel h2 {
  color: var(--color-accent);
  font-family: var(--font-mono);
  font-size: var(--font-size-badge);
  font-weight: var(--font-weight-regular);
  letter-spacing: 0.2em;
  line-height: var(--line-height-tight);
  text-transform: uppercase;
}

.live-auction-panel__status,
.live-auction-panel__extension {
  padding: 3px 8px;
  border-radius: var(--radius-badge);
  background: color-mix(in srgb, var(--color-auction) 18%, transparent);
  color: var(--color-auction);
  font-size: var(--font-size-badge);
  font-weight: var(--font-weight-bold);
}

.live-auction-panel__empty,
.live-auction-panel__result {
  display: grid;
  min-height: 88px;
  align-content: center;
  gap: var(--space-1);
  color: var(--color-live-text-secondary);
  font-size: var(--font-size-xs);
  line-height: 1.5;
}

.live-auction-panel__empty strong,
.live-auction-panel__result strong {
  color: var(--color-live-text-primary);
  font-size: var(--font-size-caption);
}

.live-auction-panel__metrics {
  display: grid;
  gap: 8px var(--space-4);
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.live-auction-panel__metrics span,
.live-auction-panel__next span,
.live-auction-panel__balance {
  display: block;
  color: var(--color-live-text-secondary);
  font-size: var(--font-size-badge);
}

.live-auction-panel__metrics strong {
  display: block;
  margin-top: 2px;
  overflow: hidden;
  color: var(--color-live-text-primary);
  font-family: var(--font-mono);
  font-size: var(--font-size-xs);
  font-variant-numeric: tabular-nums;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.live-auction-panel__urgent,
.live-auction-panel__next strong {
  color: var(--color-auction) !important;
}

.live-auction-panel__bidder--active span,
.live-auction-panel__bidder--active strong {
  color: var(--color-auction);
}

.live-auction-panel__bidder--active strong {
  font-weight: var(--font-weight-bold);
}

.live-auction-panel__extension {
  align-self: flex-start;
}

.live-auction-panel__next {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
}

.live-auction-panel__next strong {
  font-family: var(--font-mono);
  font-size: var(--font-size-lg);
  font-variant-numeric: tabular-nums;
}

.live-auction-panel__slider {
  position: relative;
  flex-shrink: 0;
  height: var(--button-height-compact);
  overflow: hidden;
  border: 1px solid var(--color-auction);
  border-radius: 999px;
  background:
    linear-gradient(
      90deg,
      color-mix(in srgb, var(--color-auction) 35%, transparent) 0 var(--slide-progress),
      var(--color-live-background) var(--slide-progress) 100%
    );
}

.live-auction-panel__slider input {
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

.live-auction-panel__slider input:active {
  cursor: grabbing;
}

.live-auction-panel__slider input::-webkit-slider-thumb {
  width: 36px;
  height: 36px;
  border: 0;
  border-radius: 50%;
  appearance: none;
  background: var(--color-auction);
  box-shadow: 0 0 0 2px var(--color-live-background);
}

.live-auction-panel__slider input::-moz-range-thumb {
  width: 36px;
  height: 36px;
  border: 0;
  border-radius: 50%;
  background: var(--color-auction);
}

.live-auction-panel__slider > span {
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

.live-auction-panel__slider--disabled {
  border-color: var(--color-live-border);
  opacity: 0.65;
}

.live-auction-panel__login {
  min-height: var(--button-height-2xs);
  border: 1px solid var(--color-live-border);
  border-radius: var(--radius-control);
  background: var(--color-live-background);
  color: var(--color-live-text-primary);
  font-size: var(--font-size-xs);
}

.live-auction-panel__balance {
  display: flex;
  justify-content: space-between;
}

.live-auction-panel__balance strong {
  color: var(--color-live-text-primary);
  font-variant-numeric: tabular-nums;
}

.live-auction-panel__error {
  color: var(--color-error);
  font-size: var(--font-size-xs);
  line-height: var(--line-height-snug);
}
</style>
