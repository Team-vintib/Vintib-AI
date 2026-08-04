<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { LIVE_AUCTION_MOCK_STATES } from '@/domains/auction/constants/liveAuctionMockData'
import LiveAuctionPanel from '@/domains/auction/components/LiveAuctionPanel.vue'
import LiveChatOverlay from '@/domains/chat/components/LiveChatOverlay.vue'
import { issueLiveVideoToken } from '@/domains/live/api/liveControlApi'
import {
  isLiveRealtimeApiEnabled,
  LiveRealtimeClient,
} from '@/domains/live/api/liveRealtimeClient'
import {
  cancelLiveReminder,
  getLiveWatchViewData,
  isLiveWatchApiEnabled,
  LiveWatchNotFoundError,
  registerLiveReminder,
} from '@/domains/live/api/liveWatchApi'
import LiveProductQueue from '@/domains/live/components/LiveProductQueue.vue'
import LiveSelectedProduct from '@/domains/live/components/LiveSelectedProduct.vue'
import LiveVideoStage from '@/domains/live/components/LiveVideoStage.vue'
import LiveWatchHeader from '@/domains/live/components/LiveWatchHeader.vue'
import LiveWatchState from '@/domains/live/components/LiveWatchState.vue'
import LiveTryOnPanel from '@/domains/tryon/components/LiveTryOnPanel.vue'
import { LIVE_TRY_ON_MOCK_SCENARIOS } from '@/domains/tryon/types/liveTryOn.types'
import { normalizeApiError } from '@/shared/api/http'
import { ROUTE_NAMES } from '@/shared/constants/routes'
import LiveLayout from '@/shared/layouts/LiveLayout.vue'

import type { LiveAuctionMockState } from '@/domains/auction/types/liveAuction.types'
import type {
  CurrentProductMessage,
  LiveStatusMessage,
  LiveWatchLoadState,
  LiveWatchMockScenario,
  LiveWatchViewData,
} from '@/domains/live/types/liveWatch.types'
import type { LiveTryOnMockScenario } from '@/domains/tryon/types/liveTryOn.types'

const LIVE_WATCH_MOCK_SCENARIOS: LiveWatchMockScenario[] = [
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
const isFollowing = ref(false)
const wishedProductIds = ref<number[]>([])
const isTryOnOpen = ref(false)
const now = ref(Date.now())
const videoConnectionLabel = ref('')
const apiEnabled = isLiveWatchApiEnabled()

const handleToggleReminder = async () => {
  if (!live.value) {
    return
  }

  const next = !live.value.isReminderSet
  live.value.isReminderSet = next

  try {
    const result = next
      ? await registerLiveReminder(live.value.id)
      : await cancelLiveReminder(live.value.id)
    live.value.isReminderSet = result.isReminderSet
  } catch {
    live.value.isReminderSet = !next
  }
}
const realtimeEnabled = isLiveRealtimeApiEnabled()
let loadRequestId = 0
let realtimeClient: LiveRealtimeClient | null = null

const getRouteLiveId = () => {
  const routeValue = Array.isArray(route.params.liveId) ? route.params.liveId[0] : route.params.liveId
  const liveId = Number(routeValue)

  return Number.isInteger(liveId) && liveId > 0 ? liveId : null
}

const getMockScenario = (): LiveWatchMockScenario => {
  const queryValue = Array.isArray(route.query.mock) ? route.query.mock[0] : route.query.mock

  return LIVE_WATCH_MOCK_SCENARIOS.includes(queryValue as LiveWatchMockScenario)
    ? (queryValue as LiveWatchMockScenario)
    : 'default'
}

const auctionMockState = computed<LiveAuctionMockState>(() => {
  const queryValue = Array.isArray(route.query.auction)
    ? route.query.auction[0]
    : route.query.auction

  return LIVE_AUCTION_MOCK_STATES.includes(queryValue as LiveAuctionMockState)
    ? (queryValue as LiveAuctionMockState)
    : 'BIDDABLE'
})

const tryOnMockScenario = computed<LiveTryOnMockScenario>(() => {
  const queryValue = Array.isArray(route.query.tryon)
    ? route.query.tryon[0]
    : route.query.tryon

  return LIVE_TRY_ON_MOCK_SCENARIOS.includes(queryValue as LiveTryOnMockScenario)
    ? (queryValue as LiveTryOnMockScenario)
    : 'ready'
})

const selectedProduct = computed(
  () => live.value?.products.find((product) => product.id === selectedProductId.value) ?? null,
)

const isTryOnAvailable = computed(
  () => live.value?.status === 'LIVE' && selectedProduct.value !== null,
)

const isSelectedProductWished = computed(
  () =>
    selectedProductId.value !== null &&
    wishedProductIds.value.includes(selectedProductId.value),
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

const loadLiveWatch = async () => {
  const requestId = ++loadRequestId
  const liveId = getRouteLiveId()
  const scenario = getMockScenario()

  disconnectRealtime()
  live.value = null
  selectedProductId.value = null
  isTryOnOpen.value = false
  loadState.value = 'loading'
  errorMessage.value = ''
  videoConnectionLabel.value = ''

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

    // 개설자가 접속하면 무조건 판매자 화면으로 보낸다(LiveBroadcastPage의 반대 가드, BE 016 §2.2 isHost).
    // mock 프리뷰(apiEnabled=false)는 isHost가 항상 false이므로 가드를 건너뛴다.
    if (apiEnabled && response.isHost) {
      void router.replace({ name: ROUTE_NAMES.LIVE_BROADCAST, params: { liveId } })
      return
    }

    live.value = response
    selectedProductId.value =
      response.currentProductId ?? response.products.at(0)?.id ?? null
    now.value = Date.now()
    loadState.value = 'success'

    if (response.status === 'LIVE') {
      void loadVideoToken(response.id)
      connectRealtime(response.id)
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
        ? '라이브 방송 정보를 불러오지 못했습니다. 네트워크 상태를 확인해 주세요.'
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

const goToProduct = (productId: number) => {
  void router.push({
    name: ROUTE_NAMES.PRODUCT_DETAIL,
    params: { productId },
  })
}

const toggleWish = () => {
  const productId = selectedProductId.value

  if (productId === null) return

  wishedProductIds.value = wishedProductIds.value.includes(productId)
    ? wishedProductIds.value.filter((id) => id !== productId)
    : [...wishedProductIds.value, productId]
}

const openTryOn = () => {
  if (!isTryOnAvailable.value) return

  isTryOnOpen.value = true
}

const updateViewerCount = (viewerCount: number) => {
  if (!live.value) return

  live.value = {
    ...live.value,
    currentViewerCount: viewerCount,
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

// 방송 상태·현재 상품 전파 구독. 채팅/반응/시청자수는 LiveChatOverlay가 별도 클라이언트로
// 관리하므로 여기서 건드리지 않는다.
const connectRealtime = (liveId: number) => {
  disconnectRealtime()

  if (!realtimeEnabled) return

  realtimeClient = new LiveRealtimeClient({
    onConnect: () => subscribeRealtime(liveId),
  })
  realtimeClient.connect()
}

const subscribeRealtime = (liveId: number) => {
  if (!realtimeClient) return

  realtimeClient.subscribe(`/topic/lives/${liveId}/status`, (body) => {
    if (isLiveStatusMessage(body)) {
      applyStatusMessage(body)
    }
  })

  realtimeClient.subscribe(`/topic/lives/${liveId}/product`, (body) => {
    if (isCurrentProductMessage(body)) {
      applyCurrentProductMessage(body)
    }
  })
}

const disconnectRealtime = () => {
  realtimeClient?.disconnect()
  realtimeClient = null
}

// ENDED·CANCELED면 status만 갱신해 기존 종료 상태 UI(헤더 배지·영상 안내)로 전환한다.
const applyStatusMessage = (message: LiveStatusMessage) => {
  if (!live.value || message.liveId !== live.value.id) return

  if (message.status === 'ENDED' || message.status === 'CANCELED') {
    live.value = {
      ...live.value,
      status: message.status,
      endedAt: message.endedAt ?? live.value.endedAt,
    }
    disconnectRealtime()
  }
}

// 현재 소개 상품 ID만 갱신 → 상품 큐 NOW 배지가 이동한다. 사용자의 선택은 바꾸지 않는다.
const applyCurrentProductMessage = (message: CurrentProductMessage) => {
  if (!live.value || message.liveId !== live.value.id) return

  live.value = {
    ...live.value,
    currentProductId: message.currentProductId,
  }
}

function isLiveStatusMessage(body: unknown): body is LiveStatusMessage {
  return Boolean(
    body &&
      typeof body === 'object' &&
      'liveId' in body &&
      'status' in body &&
      typeof (body as LiveStatusMessage).status === 'string',
  )
}

function isCurrentProductMessage(body: unknown): body is CurrentProductMessage {
  return Boolean(
    body && typeof body === 'object' && 'liveId' in body && 'currentProductId' in body,
  )
}

watch(
  () => [route.params.liveId, route.query.mock],
  () => {
    void loadLiveWatch()
  },
  { immediate: true },
)

watch(isTryOnAvailable, (isAvailable) => {
  if (!isAvailable) {
    isTryOnOpen.value = false
  }
})

const elapsedTimer = window.setInterval(() => {
  now.value = Date.now()
}, 1000)

onBeforeUnmount(() => {
  loadRequestId += 1
  window.clearInterval(elapsedTimer)
  disconnectRealtime()
})
</script>

<template>
  <LiveLayout>
    <div v-if="loadState === 'loading'" class="live-watch-loading" role="status">
      <span class="sr-only">라이브 방송 정보를 불러오는 중입니다.</span>
      <div class="live-watch-loading__header"></div>
      <div class="live-watch-loading__body">
        <aside></aside>
        <main>
          <div></div>
          <div></div>
        </main>
        <aside></aside>
      </div>
    </div>

    <LiveWatchState
      v-else-if="loadState === 'not-found'"
      variant="not-found"
      title="라이브 방송을 찾을 수 없습니다"
      description="삭제되었거나 공개되지 않은 방송입니다. 라이브 목록에서 다른 방송을 확인해 주세요."
      primary-label="라이브 목록으로"
      @primary="router.push({ name: ROUTE_NAMES.LIVE_LIST })"
    />

    <LiveWatchState
      v-else-if="loadState === 'error'"
      variant="error"
      title="라이브 방송을 불러오지 못했습니다"
      :description="errorMessage"
      primary-label="다시 시도"
      secondary-label="라이브 목록으로"
      @primary="loadLiveWatch"
      @secondary="router.push({ name: ROUTE_NAMES.LIVE_LIST })"
    />

    <div v-else-if="live" class="live-watch-page">
      <LiveWatchHeader
        :live="live"
        :elapsed-time="elapsedTime"
        :is-following="isFollowing"
        @back="goBack"
        @toggle-follow="isFollowing = !isFollowing"
      />

      <div class="live-watch-page__body">
        <LiveProductQueue
          :products="live.products"
          :current-product-id="live.currentProductId"
          :selected-product-id="selectedProductId"
          @select="selectedProductId = $event"
        />

        <main class="live-watch-page__content">
          <div
            class="live-watch-page__stage"
            :class="{ 'live-watch-page__stage--try-on': isTryOnOpen }"
          >
            <LiveVideoStage
              :title="live.title"
              :poster-url="live.posterUrl"
              :status="live.status"
              :connection-label="videoConnectionLabel"
              :try-on-disabled="!isTryOnAvailable"
              :try-on-open="isTryOnOpen"
              :show-reminder="live.status === 'SCHEDULED'"
              :reminder-active="live.isReminderSet"
              @open-try-on="openTryOn"
              @toggle-reminder="handleToggleReminder"
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

            <LiveTryOnPanel
              v-if="selectedProduct"
              v-show="isTryOnOpen"
              class="live-watch-page__try-on"
              :product="selectedProduct"
              :mock-scenario="tryOnMockScenario"
              @close="isTryOnOpen = false"
            />
          </div>

          <div class="live-watch-page__details">
            <LiveSelectedProduct
              :product="selectedProduct"
              :is-wished="isSelectedProductWished"
              @view-product="goToProduct"
              @toggle-wish="toggleWish"
            />
            <LiveAuctionPanel
              :product="selectedProduct"
              :status="live.status"
              :mock-state="auctionMockState"
            />
          </div>
        </main>
      </div>
    </div>
  </LiveLayout>
</template>

<style scoped lang="scss">
.live-watch-page {
  min-height: 100vh;
  background: var(--color-live-background);
}

.live-watch-page__body {
  display: grid;
  min-height: calc(100vh - 52px);
  grid-template-columns: 220px minmax(0, 1fr);
}

.live-watch-page__content {
  display: grid;
  min-width: 0;
  min-height: 0;
  height: calc(100vh - 52px);
  grid-template-rows: minmax(420px, 1fr) 164px;
}

.live-watch-page__stage {
  display: grid;
  position: relative;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  grid-template-columns: minmax(0, 1fr);
}

.live-watch-page__stage--try-on {
  grid-template-columns: minmax(0, 1fr) 530px;
}

.live-watch-page__details {
  display: grid;
  min-width: 0;
  min-height: 0;
  grid-template-columns: minmax(0, 1fr) 380px;
}

.live-watch-loading {
  min-height: 100vh;
  background: var(--color-live-background);
}

.live-watch-loading__header {
  height: 52px;
  border-bottom: 1px solid var(--color-live-border);
  background:
    linear-gradient(
      90deg,
      transparent 20%,
      rgba(255, 255, 255, 0.06) 40%,
      transparent 60%
    ),
    var(--color-live-surface);
  background-size: 200% 100%;
  animation: live-watch-shimmer 1.6s infinite linear;
}

.live-watch-loading__body {
  display: grid;
  min-height: calc(100vh - 52px);
  grid-template-columns: 220px minmax(0, 1fr);
}

.live-watch-loading__body > aside {
  border-right: 1px solid var(--color-live-border);
  background: var(--color-live-surface);
}

.live-watch-loading__body > main {
  display: grid;
  grid-template-rows: minmax(420px, 1fr) 164px;
}

.live-watch-loading__body > main > div {
  background:
    linear-gradient(
      105deg,
      transparent 25%,
      rgba(255, 255, 255, 0.05) 42%,
      transparent 58%
    ),
    #151918;
  background-size: 200% 100%;
  animation: live-watch-shimmer 1.6s infinite linear;
}

.live-watch-loading__body > main > div + div {
  border-top: 1px solid var(--color-live-border);
  background-color: var(--color-live-surface);
}

@keyframes live-watch-shimmer {
  to {
    background-position-x: -200%;
  }
}

@media (max-width: 1100px) {
  .live-watch-page__stage--try-on {
    grid-template-columns: minmax(0, 1fr) minmax(400px, 50%);
  }

  .live-watch-page__details {
    grid-template-columns: minmax(0, 1fr) 320px;
  }
}

@media (max-width: 720px) {
  .live-watch-page__body,
  .live-watch-loading__body {
    grid-template-columns: minmax(0, 1fr);
  }

  .live-watch-page__content {
    height: auto;
    grid-template-rows: 320px auto;
  }

  .live-watch-page__stage,
  .live-watch-page__stage--try-on {
    display: block;
  }

  .live-watch-page__stage > :first-child {
    height: 100%;
  }

  .live-watch-page__try-on {
    position: absolute;
    z-index: 4;
    inset: 0;
  }

  .live-watch-page__details {
    grid-template-columns: minmax(0, 1fr);
  }

  .live-watch-loading__body > aside {
    min-height: 140px;
    border-right: 0;
    border-bottom: 1px solid var(--color-live-border);
  }

  .live-watch-loading__body > main {
    grid-template-rows: 320px 180px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .live-watch-loading__header,
  .live-watch-loading__body > main > div {
    animation: none;
  }
}
</style>
