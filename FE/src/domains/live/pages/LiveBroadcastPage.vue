<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import LiveAuctionResultOverlay from '@/domains/auction/components/LiveAuctionResultOverlay.vue'
import SellerAuctionPanel from '@/domains/auction/components/SellerAuctionPanel.vue'
import { LIVE_AUCTION_MOCK_RESULT } from '@/domains/auction/constants/liveAuctionMockData'
import LiveChatOverlay from '@/domains/chat/components/LiveChatOverlay.vue'
import { issueLiveVideoToken, updateLiveStatus } from '@/domains/live/api/liveControlApi'
import {
  getLiveWatchViewData,
  isLiveWatchApiEnabled,
  LiveWatchNotFoundError,
} from '@/domains/live/api/liveWatchApi'
import LiveBroadcastEndDashboard from '@/domains/live/components/LiveBroadcastEndDashboard.vue'
import LiveBroadcastHeader from '@/domains/live/components/LiveBroadcastHeader.vue'
import LiveBroadcastInfo from '@/domains/live/components/LiveBroadcastInfo.vue'
import LiveProductQueue from '@/domains/live/components/LiveProductQueue.vue'
import LiveUnsoldManage from '@/domains/live/components/LiveUnsoldManage.vue'
import LiveVideoStage from '@/domains/live/components/LiveVideoStage.vue'
import LiveWatchState from '@/domains/live/components/LiveWatchState.vue'
import type { BroadcastEndSummary } from '@/domains/live/constants/liveBroadcastEndMock'
import { normalizeApiError } from '@/shared/api/http'
import { ROUTE_NAMES } from '@/shared/constants/routes'
import LiveLayout from '@/shared/layouts/LiveLayout.vue'

import type {
  LiveWatchLoadState,
  LiveWatchMockScenario,
  LiveWatchViewData,
} from '@/domains/live/types/liveWatch.types'

const LIVE_BROADCAST_MOCK_SCENARIOS: LiveWatchMockScenario[] = [
  'default',
  'loading',
  'error',
  'not-found',
  'empty-products',
  'scheduled',
  'ended',
]

const route = useRoute()
const router = useRouter()
const live = ref<LiveWatchViewData | null>(null)
const loadState = ref<LiveWatchLoadState>('loading')
const errorMessage = ref('')
const selectedProductId = ref<number | null>(null)
// 441 판매자 낙찰 이벤트 — 경매 낙찰 시 방송 영상 위 축하 오버레이(시청자 434 재사용) 표시용.
const auctionWin = ref<{
  winnerNickname: string
  winningBid: number
  productTitle: string | null
} | null>(null)
// 438/440 방송 종료 화면 단계: 대시보드 → (미낙찰 있으면) 남은 상품 관리.
const endView = ref<'dashboard' | 'manage'>('dashboard')
const now = ref(Date.now())
const videoConnectionLabel = ref('')
// 방송 상세는 시청자와 같은 GET /lives/{liveId} 실 API를 재사용한다(VITE_LIVE_WATCH_API_ENABLED).
// 판매자 전용 상태(방송 소유자 여부·currentProductId 등)는 BE 미제공 → liveWatchApi에서 null/fallback.
// (BE 확인 필요: docs/requests/BE/007 3.5, docs/requests/BE/013)
const apiEnabled = isLiveWatchApiEnabled()
let loadRequestId = 0

const getRouteLiveId = () => {
  const routeValue = Array.isArray(route.params.liveId)
    ? route.params.liveId[0]
    : route.params.liveId
  const liveId = Number(routeValue)

  return Number.isInteger(liveId) && liveId > 0 ? liveId : null
}

const getMockScenario = (): LiveWatchMockScenario => {
  const queryValue = Array.isArray(route.query.mock) ? route.query.mock[0] : route.query.mock

  return LIVE_BROADCAST_MOCK_SCENARIOS.includes(queryValue as LiveWatchMockScenario)
    ? (queryValue as LiveWatchMockScenario)
    : 'default'
}

const selectedProduct = computed(
  () => live.value?.products.find((product) => product.id === selectedProductId.value) ?? null,
)

const elapsedSeconds = computed(() => {
  if (!live.value?.startedAt) return 0

  const startedAt = new Date(live.value.startedAt).getTime()
  const endAt =
    live.value.status === 'ENDED' && live.value.endedAt
      ? new Date(live.value.endedAt).getTime()
      : now.value

  if (!Number.isFinite(startedAt) || !Number.isFinite(endAt)) return 0

  return Math.max(0, Math.floor((endAt - startedAt) / 1000))
})

const elapsedTime = computed(() => {
  const hours = Math.floor(elapsedSeconds.value / 3600)
  const minutes = Math.floor((elapsedSeconds.value % 3600) / 60)
  const seconds = elapsedSeconds.value % 60

  return [String(hours), minutes, seconds]
    .map((unit, index) => (index === 0 ? unit : String(unit).padStart(2, '0')))
    .join(':')
})

const loadLiveBroadcast = async () => {
  const requestId = ++loadRequestId
  const liveId = getRouteLiveId()
  const scenario = getMockScenario()

  live.value = null
  selectedProductId.value = null
  loadState.value = 'loading'
  errorMessage.value = ''
  isEndConfirmOpen.value = false
  auctionWin.value = null
  endView.value = 'dashboard'
  transitionNotice.value = ''
  videoConnectionLabel.value = ''
  window.clearTimeout(transitionNoticeTimer)

  if (liveId === null) {
    loadState.value = 'not-found'
    return
  }

  if (!apiEnabled && scenario === 'loading') {
    return
  }

  try {
    const response = await getLiveWatchViewData(liveId, scenario)

    if (requestId !== loadRequestId) return

    live.value = response
    selectedProductId.value = response.currentProductId ?? response.products.at(0)?.id ?? null
    now.value = Date.now()
    loadState.value = 'success'

    if (response.status === 'LIVE') {
      void loadVideoToken(response.id)
    }

    // mock 확인용: ?win 쿼리면 낙찰 축하 오버레이를 바로 띄운다(실사용 트리거는 handleAuctionEnded).
    if (false && !apiEnabled && route.query.win !== undefined) {
      auctionWin.value = {
        winnerNickname: LIVE_AUCTION_MOCK_RESULT.winnerNickname,
        winningBid: LIVE_AUCTION_MOCK_RESULT.winningBid,
        productTitle: selectedProduct.value?.title ?? null,
      }
    }
  } catch (error) {
    if (requestId !== loadRequestId) return

    if (error instanceof LiveWatchNotFoundError) {
      loadState.value = 'not-found'
      return
    }

    const apiError = normalizeApiError(error)

    errorMessage.value =
      apiError.code === 'UNKNOWN_ERROR' || apiError.code === 'NETWORK_ERROR'
        ? '방송 정보를 불러오지 못했습니다. 네트워크 상태를 확인해 주세요.'
        : apiError.message
    loadState.value = 'error'
  }
}

const goBack = () => {
  if (window.history.length > 1) {
    router.back()
    return
  }

  void router.push({ name: ROUTE_NAMES.LIVE_LIST })
}

// 판매자 제어(437/439). 서버 반영 계약이 아직 없어 로컬 상태(Mock 전용)만 바꾼다. — BE 확인 필요
//   · 방송 종료: POST /lives/{liveId}/end
//   · 현재 상품 전환: PATCH /lives/{liveId}/current-product
// 실제 엔드포인트·시청자 전파(STOMP)는 docs/requests/BE/013 확정 후 연결한다.
const isEndConfirmOpen = ref(false)
const transitionNotice = ref('')
let transitionNoticeTimer: number | undefined

const canTransition = computed(
  () =>
    live.value?.status === 'LIVE' &&
    selectedProductId.value !== null &&
    selectedProductId.value !== live.value?.currentProductId,
)

const transitionToSelectedProduct = () => {
  if (!live.value || !canTransition.value || selectedProductId.value === null) return

  const nextProduct = live.value.products.find(
    (product) => product.id === selectedProductId.value,
  )

  live.value = { ...live.value, currentProductId: selectedProductId.value }

  transitionNotice.value = nextProduct
    ? `‘${nextProduct.title}’(으)로 넘어갔습니다`
    : '현재 상품을 전환했습니다'

  window.clearTimeout(transitionNoticeTimer)
  transitionNoticeTimer = window.setTimeout(() => {
    transitionNotice.value = ''
  }, 2600)
}

const requestEndBroadcast = () => {
  if (live.value?.status !== 'LIVE') return

  isEndConfirmOpen.value = true
}

const cancelEndBroadcast = () => {
  isEndConfirmOpen.value = false
}

const confirmEndBroadcast = async () => {
  if (!live.value) return

  try {
    const response = await updateLiveStatus(live.value.id, 'ENDED')

    live.value = {
      ...live.value,
      status: response.status,
      endedAt: new Date(now.value).toISOString(),
    }
    isEndConfirmOpen.value = false
  } catch (error) {
    transitionNotice.value =
      error instanceof Error ? error.message : '방송을 종료하지 못했습니다.'

    window.clearTimeout(transitionNoticeTimer)
    transitionNoticeTimer = window.setTimeout(() => {
      transitionNotice.value = ''
    }, 2600)
  }
}

const loadVideoToken = async (liveId: number) => {
  videoConnectionLabel.value = '영상 토큰 발급 중'

  try {
    const token = await issueLiveVideoToken(liveId)
    videoConnectionLabel.value =
      token.role === 'PUBLISHER' ? '송출 토큰 발급 완료' : '시청 토큰 발급 완료'
  } catch {
    videoConnectionLabel.value = '영상 토큰 발급 실패'
  }
}

const updateViewerCount = (viewerCount: number) => {
  if (!live.value) return

  live.value = {
    ...live.value,
    currentViewerCount: viewerCount,
  }
}

const handleAuctionEnded = (result: {
  outcome: 'WON' | 'FAILED'
  winnerNickname: string | null
  winningBid: number
  productTitle: string | null
}) => {
  // 낙찰(WON)일 때만 축하 오버레이. 미낙찰은 패널 표기(ENDED_FAILED)로 충분.
  auctionWin.value =
    result.outcome === 'WON' && result.winnerNickname
      ? {
          winnerNickname: result.winnerNickname,
          winningBid: result.winningBid,
          productTitle: result.productTitle,
        }
      : null
}

const closeAuctionWin = () => {
  auctionWin.value = null
}

// 438 방송 종료 대시보드 — 종료 시 방송 요약(mock). 실제 경매 결과/방송 요약 API 없음(docs/requests/BE/009, 013).
// ?result=sold 이면 전부 낙찰(미낙찰 처리 섹션 숨김 확인용).
const broadcastSummary = computed<BroadcastEndSummary>(() => ({
  productCount: live.value?.products.length ?? 0,
  soldCount: 0,
  unsoldCount: 0,
  totalSales: 0,
  results: [],
}))

const unsoldProducts = computed(() => {
  const unsoldIds = new Set(
    broadcastSummary.value.results
      .filter((result) => result.outcome === 'UNSOLD')
      .map((result) => result.productId),
  )

  return (live.value?.products ?? []).filter((product) => unsoldIds.has(product.id))
})

watch(
  () => [route.params.liveId, route.query.mock],
  () => {
    void loadLiveBroadcast()
  },
  { immediate: true },
)

const elapsedTimer = window.setInterval(() => {
  now.value = Date.now()
}, 1000)

onBeforeUnmount(() => {
  loadRequestId += 1
  window.clearInterval(elapsedTimer)
  window.clearTimeout(transitionNoticeTimer)
})
</script>

<template>
  <LiveLayout>
    <div v-if="loadState === 'loading'" class="live-broadcast-loading" role="status">
      <span class="sr-only">방송 정보를 불러오는 중입니다.</span>
      <div class="live-broadcast-loading__header"></div>
      <div class="live-broadcast-loading__body">
        <aside></aside>
        <main></main>
        <aside></aside>
      </div>
    </div>

    <LiveWatchState
      v-else-if="loadState === 'not-found'"
      variant="not-found"
      title="방송을 찾을 수 없습니다"
      description="삭제되었거나 접근할 수 없는 방송입니다. 라이브 목록에서 다시 확인해 주세요."
      primary-label="라이브 목록으로"
      @primary="router.push({ name: ROUTE_NAMES.LIVE_LIST })"
    />

    <LiveWatchState
      v-else-if="loadState === 'error'"
      variant="error"
      title="방송 정보를 불러오지 못했습니다"
      :description="errorMessage"
      primary-label="다시 시도"
      secondary-label="라이브 목록으로"
      @primary="loadLiveBroadcast"
      @secondary="router.push({ name: ROUTE_NAMES.LIVE_LIST })"
    />

    <div v-else-if="live" class="live-broadcast-page">
      <LiveBroadcastEndDashboard
        v-if="live.status === 'ENDED' && endView === 'dashboard'"
        :title="live.title"
        :elapsed-time="elapsedTime"
        :peak-viewer-count="live.peakViewerCount"
        :summary="broadcastSummary"
        @manage-unsold="endView = 'manage'"
        @to-list="router.push({ name: ROUTE_NAMES.LIVE_LIST })"
      />

      <LiveUnsoldManage
        v-else-if="live.status === 'ENDED' && endView === 'manage'"
        :products="unsoldProducts"
        @back="endView = 'dashboard'"
        @to-list="router.push({ name: ROUTE_NAMES.LIVE_LIST })"
      />

      <LiveBroadcastHeader
        v-if="live.status !== 'ENDED'"
        :live="live"
        :elapsed-time="elapsedTime"
        @back="goBack"
        @end-broadcast="requestEndBroadcast"
      />

      <div v-if="live.status !== 'ENDED'" class="live-broadcast-page__body">
        <aside class="live-broadcast-page__queue">
          <LiveProductQueue
            :products="live.products"
            :current-product-id="live.currentProductId"
            :selected-product-id="selectedProductId"
            @select="selectedProductId = $event"
          />

          <!-- 상품 전환(넘어가는 알림) — 437 -->
          <div class="live-broadcast-page__queue-action">
            <button
              class="live-broadcast-page__transition"
              type="button"
              :disabled="!canTransition"
              @click="transitionToSelectedProduct"
            >
              선택 상품으로 전환
            </button>
            <p class="live-broadcast-page__slot-note">
              {{
                live.status !== 'LIVE'
                  ? '방송 중일 때 상품을 전환할 수 있습니다.'
                  : canTransition
                    ? '선택한 상품을 현재 소개 상품으로 바꿉니다.'
                    : '큐에서 다른 상품을 선택하면 전환할 수 있습니다.'
              }}
            </p>
          </div>
        </aside>

        <main class="live-broadcast-page__stage">
          <LiveVideoStage
            :title="live.title"
            :poster-url="live.posterUrl"
            :status="live.status"
            :connection-label="videoConnectionLabel"
            :show-try-on="false"
          >
            <template #overlay>
              <LiveChatOverlay
                :live-id="live.id"
                :host-id="live.hostId"
                :status="live.status"
                @viewer-count="updateViewerCount"
              />
            </template>
          </LiveVideoStage>

          <LiveAuctionResultOverlay
            v-if="auctionWin"
            :winner-nickname="auctionWin.winnerNickname"
            :winning-bid="auctionWin.winningBid"
            :product-title="auctionWin.productTitle"
            @close="closeAuctionWin"
          />

          <p v-if="transitionNotice" class="live-broadcast-page__notice" role="status">
            {{ transitionNotice }}
          </p>
        </main>

        <aside class="live-broadcast-page__control">
          <LiveBroadcastInfo :live="live" :elapsed-time="elapsedTime" />

          <SellerAuctionPanel
            :live-id="live.id"
            :product="selectedProduct"
            :status="live.status"
            @auction-ended="handleAuctionEnded"
          />
        </aside>
      </div>

      <div
        v-if="isEndConfirmOpen"
        class="live-broadcast-page__modal-backdrop"
        @click.self="cancelEndBroadcast"
      >
        <div
          class="live-broadcast-page__modal"
          role="dialog"
          aria-modal="true"
          aria-labelledby="end-broadcast-title"
        >
          <h2 id="end-broadcast-title">방송을 종료할까요?</h2>
          <p>종료하면 시청자에게 방송이 끝난 것으로 표시되고, 다시 시작할 수 없습니다.</p>
          <div class="live-broadcast-page__modal-actions">
            <button
              type="button"
              class="live-broadcast-page__modal-cancel"
              @click="cancelEndBroadcast"
            >
              취소
            </button>
            <button
              type="button"
              class="live-broadcast-page__modal-confirm"
              @click="confirmEndBroadcast"
            >
              방송 종료
            </button>
          </div>
        </div>
      </div>
    </div>
  </LiveLayout>
</template>

<style scoped lang="scss">
.live-broadcast-page {
  min-height: 100vh;
  background: var(--color-live-background);
}

.live-broadcast-page__body {
  display: grid;
  min-height: calc(100vh - 52px);
  height: calc(100vh - 52px);
  grid-template-columns: 240px minmax(0, 1fr) 360px;
}

.live-broadcast-page__queue {
  display: flex;
  min-height: 0;
  flex-direction: column;
  border-right: 1px solid var(--color-live-border);
  background: var(--color-live-background);
}

.live-broadcast-page__queue > :first-child {
  flex: 1;
  min-height: 0;
}

.live-broadcast-page__queue-action {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: var(--space-3);
  border-top: 1px solid var(--color-live-border);
}

.live-broadcast-page__transition {
  min-height: 40px;
  border: 1px solid var(--color-live);
  border-radius: var(--radius-control);
  background: color-mix(in srgb, var(--color-live) 18%, transparent);
  color: var(--color-live-text-primary);
  font-size: 13px;
  font-weight: 700;
}

.live-broadcast-page__transition:hover:not(:disabled) {
  background: color-mix(in srgb, var(--color-live) 30%, transparent);
}

.live-broadcast-page__transition:disabled {
  border-color: var(--color-live-border);
  background: transparent;
  color: var(--color-live-text-secondary);
  opacity: 0.6;
}

.live-broadcast-page__stage {
  display: grid;
  position: relative;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  grid-template-columns: minmax(0, 1fr);
}

.live-broadcast-page__control {
  display: flex;
  min-height: 0;
  flex-direction: column;
  gap: var(--space-3);
  overflow-y: auto;
  padding: var(--space-4);
  border-left: 1px solid var(--color-live-border);
  background: var(--color-live-background);
}

.live-broadcast-page__slot-note {
  color: var(--color-live-text-secondary);
  font-size: 10px;
  letter-spacing: 0.02em;
  opacity: 0.75;
}

.live-broadcast-page__notice {
  position: absolute;
  z-index: 3;
  top: var(--space-4);
  left: 50%;
  max-width: calc(100% - var(--space-8));
  padding: 8px 16px;
  border: 1px solid var(--color-live-border);
  border-radius: var(--radius-chip);
  background: rgba(10, 12, 11, 0.86);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  text-align: center;
  backdrop-filter: blur(8px);
  transform: translateX(-50%);
  animation: live-broadcast-notice 200ms ease-out;
}

@keyframes live-broadcast-notice {
  from {
    opacity: 0;
    transform: translate(-50%, -6px);
  }
}

.live-broadcast-page__modal-backdrop {
  display: grid;
  position: fixed;
  z-index: 50;
  inset: 0;
  place-items: center;
  padding: var(--space-4);
  background: rgba(4, 6, 5, 0.62);
}

.live-broadcast-page__modal {
  display: flex;
  width: 100%;
  max-width: 360px;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-6);
  border: 1px solid var(--color-live-border);
  border-radius: var(--radius-card);
  background: var(--color-live-surface);
}

.live-broadcast-page__modal h2 {
  color: var(--color-live-text-primary);
  font-size: 17px;
  font-weight: 800;
}

.live-broadcast-page__modal p {
  color: var(--color-live-text-secondary);
  font-size: 13px;
  line-height: 20px;
}

.live-broadcast-page__modal-actions {
  display: flex;
  margin-top: var(--space-3);
  gap: var(--space-2);
}

.live-broadcast-page__modal-actions button {
  flex: 1;
  min-height: 42px;
  border-radius: var(--radius-control);
  font-size: 14px;
  font-weight: 700;
}

.live-broadcast-page__modal-cancel {
  border: 1px solid var(--color-live-border);
  background: transparent;
  color: var(--color-live-text-primary);
}

.live-broadcast-page__modal-confirm {
  border: 1px solid color-mix(in srgb, var(--color-error) 55%, transparent);
  background: var(--color-error);
  color: #fff;
}

.live-broadcast-page__modal-cancel:hover {
  background: var(--color-live-surface-raised);
}

.live-broadcast-page__modal-confirm:hover {
  opacity: 0.92;
}

.live-broadcast-loading {
  min-height: 100vh;
  background: var(--color-live-background);
}

.live-broadcast-loading__header {
  height: 52px;
  border-bottom: 1px solid var(--color-live-border);
  background: var(--color-live-surface);
}

.live-broadcast-loading__body {
  display: grid;
  min-height: calc(100vh - 52px);
  grid-template-columns: 240px minmax(0, 1fr) 360px;
}

.live-broadcast-loading__body > aside {
  border-right: 1px solid var(--color-live-border);
  background: var(--color-live-surface);
}

.live-broadcast-loading__body > aside:last-child {
  border-right: 0;
  border-left: 1px solid var(--color-live-border);
}

.live-broadcast-loading__body > main {
  background: #101413;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

@media (max-width: 1100px) {
  .live-broadcast-page__body,
  .live-broadcast-loading__body {
    grid-template-columns: 220px minmax(0, 1fr) 320px;
  }
}

@media (max-width: 900px) {
  .live-broadcast-page__body {
    height: auto;
    grid-template-columns: minmax(0, 1fr);
    grid-auto-rows: min-content;
  }

  .live-broadcast-page__queue {
    border-right: 0;
    border-bottom: 1px solid var(--color-live-border);
  }

  .live-broadcast-page__stage {
    min-height: 360px;
  }

  .live-broadcast-page__control {
    border-left: 0;
    border-top: 1px solid var(--color-live-border);
  }

  .live-broadcast-loading__body {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
