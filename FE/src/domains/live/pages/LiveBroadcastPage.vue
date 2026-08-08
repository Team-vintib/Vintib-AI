<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'

import {
  getBroadcastSummary,
  getCurrentAuction,
  getLiveUnsoldProducts,
  isAuctionEventMessage,
} from '@/domains/auction/api/auctionApi'
import LiveAuctionResultOverlay from '@/domains/auction/components/LiveAuctionResultOverlay.vue'
import LiveAuctionStartOverlay from '@/domains/auction/components/LiveAuctionStartOverlay.vue'
import SellerAuctionPanel from '@/domains/auction/components/SellerAuctionPanel.vue'
import LiveChatOverlay from '@/domains/chat/components/LiveChatOverlay.vue'
import { patchCurrentProduct, updateLiveStatus } from '@/domains/live/api/liveControlApi'
import {
  getLiveWatchViewData,
  isLiveWatchApiEnabled,
  LiveWatchNotFoundError,
} from '@/domains/live/api/liveWatchApi'
import LiveBroadcastEndDashboard from '@/domains/live/components/LiveBroadcastEndDashboard.vue'
import LiveBroadcastHeader from '@/domains/live/components/LiveBroadcastHeader.vue'
import LiveBroadcastInfo from '@/domains/live/components/LiveBroadcastInfo.vue'
import LiveProductQueue from '@/domains/live/components/LiveProductQueue.vue'
import { LIVE_TOPICS } from '@/domains/live/constants/liveRealtimeTopics'
import LiveUnsoldManage from '@/domains/live/components/LiveUnsoldManage.vue'
import LiveVideoStage from '@/domains/live/components/LiveVideoStage.vue'
import LiveWatchState from '@/domains/live/components/LiveWatchState.vue'
import { LiveRealtimeClient } from '@/domains/live/api/liveRealtimeClient'
import { normalizeApiError } from '@/shared/api/http'
import { ROUTE_NAMES } from '@/shared/constants/routes'
import LiveLayout from '@/shared/layouts/LiveLayout.vue'

import type {
  LiveWatchLoadState,
  LiveWatchMockScenario,
  LiveWatchViewData,
  ProductSoldMessage,
} from '@/domains/live/types/liveWatch.types'
import type {
  AuctionSnapshot,
  BroadcastEndSummary,
  LiveUnsoldProduct,
} from '@/domains/auction/types/liveAuction.types'

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
const auctionSnapshot = ref<AuctionSnapshot | null>(null)
const auctionLoading = ref(false)
const auctionError = ref('')
const announcedAuctionId = ref<number | null>(null)
const startedAuctionTitle = ref<string | null>(null)
let startNoticeTimer: number | undefined
// 438/440 방송 종료 화면 단계: 대시보드 → (미낙찰 있으면) 남은 상품 관리.
const endView = ref<'dashboard' | 'manage'>('dashboard')
const broadcastSummary = ref<BroadcastEndSummary | null>(null)
const unsoldProducts = ref<LiveUnsoldProduct[]>([])
const resultLoading = ref(false)
const resultError = ref('')
const now = ref(Date.now())
// 방송 상세는 시청자와 같은 GET /lives/{liveId} 실 API를 재사용한다(VITE_LIVE_WATCH_API_ENABLED).
// 소유자 판정(isHost)·현재 소개 상품(currentProductId)은 BE 016 §2.1·§2.5에서 제공된다.
// isHost는 로그인 토큰이 실려야 채워지므로(비회원/비로그인은 false), host가 아니면 시청 페이지로 보낸다.
// apiEnabled가 false인 mock 프리뷰에서는 isHost가 항상 false라 판매자 화면 가드/실 API 호출을 건너뛴다.
const apiEnabled = isLiveWatchApiEnabled()
let loadRequestId = 0
let auctionSubscription: ReturnType<LiveRealtimeClient['subscribe']> | null = null
let productSoldSubscription: ReturnType<LiveRealtimeClient['subscribe']> | null = null

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

// 방송 후 판매 방식을 정할 수 있는 상품. BE 유찰 목록(GET /lives/{id}/unsold-products)은
// **경매를 걸었다가 유찰된 상품만** 준다 — 경매를 한 번도 안 건 미판매 상품(경매 예정 그대로,
// 정찰제인데 안 팔림)은 빠져서 관리 화면 자체를 못 열었다. 요약의 미판매 결과로 그 빈틈을 메운다.
const manageableUnsoldProducts = computed<LiveUnsoldProduct[]>(() => {
  const linkedById = new Map(live.value?.products.map((product) => [product.id, product]) ?? [])
  const fromAuction = unsoldProducts.value.map((product) => ({
    ...product,
    // 판매 방식은 편성 상품 목록에서 붙인다 — 상품 상세는 상품에 따라 500이 난다(요청 029).
    saleType: linkedById.get(product.productId)?.saleType ?? null,
  }))
  const known = new Set(fromAuction.map((product) => product.productId))
  const fromSummary = (broadcastSummary.value?.results ?? [])
    .filter((result) => result.status === 'UNSOLD' && !known.has(result.productId))
    .map((result) => {
      const linked = linkedById.get(result.productId)

      return {
        productId: result.productId,
        title: result.title,
        thumbnailUrl: result.thumbnailUrl ?? linked?.thumbnailUrl ?? null,
        // 경매를 건 적이 없으니 시작가가 없다. 정찰제면 등록가를 기본값으로 준다.
        startPrice: linked?.price ?? null,
        saleType: linked?.saleType ?? null,
      }
    })

  return [...fromAuction, ...fromSummary]
})

// 미판매 상품 처리 결과를 편성 상품에 반영한다 — 대시보드로 돌아갔을 때 상품별 결과의
// 가격과 판매 방식 배지가 방금 바꾼 값으로 보여야 한다.
const applyUnsoldHandled = (result: {
  productId: number
  saleType: 'DIRECT_SALE' | 'AUCTION'
  price: number | null
}) => {
  const product = live.value?.products.find((item) => item.id === result.productId)

  if (!product) return

  product.saleType = result.saleType
  product.price = result.price
  product.saleStatus = result.saleType === 'DIRECT_SALE' ? 'ON_SALE' : 'AUCTION_SCHEDULED'
}

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

const loadAuction = async (liveId: number) => {
  auctionSnapshot.value = null
  auctionError.value = ''

  if (!apiEnabled) {
    auctionLoading.value = false
    return
  }

  auctionLoading.value = true
  try {
    const snapshot = await getCurrentAuction(liveId)
    if (live.value?.id === liveId) {
      auctionSnapshot.value = snapshot
      announcedAuctionId.value = snapshot?.status === 'RUNNING' ? snapshot.auctionId : null
    }
  } catch (error) {
    if (live.value?.id === liveId) {
      auctionError.value =
        normalizeApiError(error).message || '현재 경매 정보를 불러오지 못했습니다.'
    }
  } finally {
    if (live.value?.id === liveId) {
      auctionLoading.value = false
    }
  }
}

const loadBroadcastResults = async (liveId: number) => {
  broadcastSummary.value = null
  unsoldProducts.value = []
  resultError.value = ''

  if (!apiEnabled) {
    resultLoading.value = false
    return
  }

  resultLoading.value = true
  const [summaryResult, unsoldResult] = await Promise.allSettled([
    getBroadcastSummary(liveId),
    getLiveUnsoldProducts(liveId),
  ])

  if (live.value?.id !== liveId) return

  if (summaryResult.status === 'fulfilled') {
    broadcastSummary.value = summaryResult.value
  }
  if (unsoldResult.status === 'fulfilled') {
    unsoldProducts.value = unsoldResult.value
  }

  if (summaryResult.status === 'rejected') {
    resultError.value =
      normalizeApiError(summaryResult.reason).message || '방송 결과를 불러오지 못했습니다.'
  } else if (unsoldResult.status === 'rejected') {
    resultError.value = '유찰 상품 목록을 불러오지 못했습니다. 다시 시도해 주세요.'
  }

  resultLoading.value = false
}

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
  auctionSnapshot.value = null
  auctionError.value = ''
  announcedAuctionId.value = null
  startedAuctionTitle.value = null
  broadcastSummary.value = null
  unsoldProducts.value = []
  resultError.value = ''
  endView.value = 'dashboard'
  transitionNotice.value = ''
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

    // 판매자 전용 화면. host가 아니면(로그인 안 됨 포함) 시청 페이지로 돌려보낸다(BE 016 §2.2).
    // mock 프리뷰(apiEnabled=false)는 isHost가 항상 false이므로 가드를 건너뛴다.
    if (apiEnabled && !response.isHost) {
      void router.replace({ name: ROUTE_NAMES.LIVE_WATCH, params: { liveId } })
      return
    }

    live.value = response
    selectedProductId.value = response.currentProductId ?? response.products.at(0)?.id ?? null
    now.value = Date.now()
    loadState.value = 'success'

    if (response.status === 'LIVE') {
      void loadAuction(response.id)
    }

    if (response.status === 'ENDED') {
      void loadBroadcastResults(response.id)
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
  // 방송 중이면 바로 나가지 않고 종료 확인 팝업을 먼저 띄운다.
  if (live.value?.status === 'LIVE') {
    isEndConfirmOpen.value = true
    return
  }

  void router.push({ name: ROUTE_NAMES.HOME })
}

// 판매자 제어(437/439). BE 013/016으로 확정된 실 API에 연결한다.
//   · 방송 종료: PATCH /lives/{liveId}/status (status ENDED) — 시청자 전파 /topic/lives/{id}/status
//   · 현재 상품 전환: PATCH /lives/{liveId}/current-product — 시청자 전파 /topic/lives/{id}/product
// mock 프리뷰(apiEnabled=false)에서는 로컬 상태만 바꾼다(BE 없음).
const isEndConfirmOpen = ref(false)
const isEndingBroadcast = ref(false)
const endError = ref('')
const transitionNotice = ref('')
let transitionNoticeTimer: number | undefined

const canTransition = computed(
  () =>
    live.value?.status === 'LIVE' &&
    selectedProductId.value !== null &&
    selectedProductId.value !== live.value?.currentProductId,
)

const showTransitionNotice = (message: string) => {
  transitionNotice.value = message

  window.clearTimeout(transitionNoticeTimer)
  transitionNoticeTimer = window.setTimeout(() => {
    transitionNotice.value = ''
  }, 2600)
}

const transitionToSelectedProduct = async () => {
  if (!live.value || !canTransition.value || selectedProductId.value === null) return
  // 판매자 전용 액션. 실 API 모드에서는 host만 허용(비host는 이미 시청 화면으로 리다이렉트됨).
  if (apiEnabled && !live.value.isHost) return

  const liveId = live.value.id
  const nextProductId = selectedProductId.value
  const previousProductId = live.value.currentProductId
  const nextProduct = live.value.products.find((product) => product.id === nextProductId)

  // 낙관적 업데이트 — 성공하면 /topic/lives/{id}/product로도 같은 값이 되돌아온다.
  live.value = { ...live.value, currentProductId: nextProductId }
  showTransitionNotice(
    nextProduct ? `‘${nextProduct.title}’(으)로 넘어갔습니다` : '현재 상품을 전환했습니다',
  )

  // mock 프리뷰에서는 BE가 없으므로 로컬 전환만 하고 끝낸다.
  if (!apiEnabled) return

  try {
    const response = await patchCurrentProduct(liveId, nextProductId)

    // 서버가 확정한 값으로 맞춘다(로드가 다시 돌아 live가 교체됐으면 건드리지 않는다).
    if (live.value && live.value.id === liveId) {
      live.value = { ...live.value, currentProductId: response.currentProductId }
    }
  } catch (error) {
    // 실패하면 이전 소개 상품으로 되돌린다.
    if (live.value && live.value.id === liveId) {
      live.value = { ...live.value, currentProductId: previousProductId }
    }

    showTransitionNotice(error instanceof Error ? error.message : '상품을 전환하지 못했습니다.')
  }
}

const requestEndBroadcast = () => {
  if (live.value?.status !== 'LIVE') return

  endError.value = ''
  isEndConfirmOpen.value = true
}

const cancelEndBroadcast = () => {
  if (isEndingBroadcast.value) return

  isEndConfirmOpen.value = false
  endError.value = ''
}

const confirmEndBroadcast = async () => {
  if (!live.value || isEndingBroadcast.value) return
  // 판매자 전용 액션. 실 API 모드에서는 host만 허용.
  if (apiEnabled && !live.value.isHost) return

  isEndingBroadcast.value = true
  endError.value = ''

  try {
    const response = await updateLiveStatus(live.value.id, 'ENDED')

    live.value = {
      ...live.value,
      status: response.status,
      // 종료 응답의 endedAt(오프셋 없는 KST 벽시계)을 그대로 쓴다 — toISOString 왕복 금지(BE 016 §1).
      endedAt: response.endedAt,
    }
    isEndConfirmOpen.value = false
    void loadBroadcastResults(live.value.id)
  } catch (error) {
    // 종료는 멱등이 아니다 — 이미 종료·취소된 방송이면 L007(400)이 온다(BE 013 #3).
    // 이 경우 에러가 아니라 '이미 끝난 것'으로 보고 종료 대시보드 흐름으로 넘어간다.
    const normalized = normalizeApiError(error)
    if (normalized.code === 'L007') {
      live.value = { ...live.value, status: 'ENDED' }
      isEndConfirmOpen.value = false
      void loadBroadcastResults(live.value.id)
      return
    }

    // 그 외 실패는 모달을 닫지 않고 에러(코드 포함)를 모달 안에 계속 표시해 재시도/닫기를 선택하게 한다.
    // HTTP 200 + success:false로 오면 코드 없는 순수 Error라 normalize가 UNKNOWN이 되므로 그때는 원문 메시지를 쓴다.
    const rawMessage = error instanceof Error ? error.message : ''
    endError.value =
      normalized.code === 'UNKNOWN_ERROR'
        ? rawMessage || '방송을 종료하지 못했습니다.'
        : `${normalized.message}${normalized.code ? ` (${normalized.code})` : ''}`
  } finally {
    isEndingBroadcast.value = false
  }
}

// 방송 중(LIVE)에 페이지를 벗어나려 하면(브라우저 뒤로 등) 바로 나가지 않고 종료 확인 팝업을 띄운다.
onBeforeRouteLeave(() => {
  if (live.value?.status === 'LIVE') {
    isEndConfirmOpen.value = true
    return false
  }

  return true
})

// 방송 중(LIVE)엔 탭 닫기·새로고침도 실수로 방송이 끊기지 않도록 브라우저 기본 이탈 경고를 띄운다.
const handleBeforeUnload = (event: BeforeUnloadEvent) => {
  if (live.value?.status === 'LIVE') {
    event.preventDefault()
    event.returnValue = ''
  }
}
window.addEventListener('beforeunload', handleBeforeUnload)

const updateViewerCount = (viewerCount: number) => {
  if (!live.value) return

  live.value = {
    ...live.value,
    currentViewerCount: viewerCount,
    peakViewerCount: Math.max(live.value.peakViewerCount, viewerCount),
  }
}

const applyAuctionSnapshot = (snapshot: AuctionSnapshot) => {
  auctionSnapshot.value = snapshot
  auctionError.value = ''

  auctionWin.value =
    snapshot.status === 'SUCCESS' && snapshot.highestBidderNickname
      ? {
          winnerNickname: snapshot.highestBidderNickname,
          winningBid: snapshot.currentPrice,
          productTitle: snapshot.productTitle,
        }
      : null

  // 경매가 새로 시작(RUNNING)되면 팝업으로 알린다(시청자 화면과 동일).
  if (snapshot.status === 'RUNNING' && snapshot.auctionId !== announcedAuctionId.value) {
    announcedAuctionId.value = snapshot.auctionId
    startedAuctionTitle.value = snapshot.productTitle || '상품'
    window.clearTimeout(startNoticeTimer)
    startNoticeTimer = window.setTimeout(() => {
      startedAuctionTitle.value = null
    }, 4000)
  }

  // 낙찰(SUCCESS)되면 그 상품은 즉시 SOLD가 되므로 상품 큐에도 바로 반영한다.
  if (snapshot.status === 'SUCCESS' && live.value) {
    const soldProduct = live.value.products.find((product) => product.id === snapshot.productId)
    if (soldProduct) {
      soldProduct.saleStatus = 'SOLD'
    }
  }
}

const clearAuctionSubscription = () => {
  auctionSubscription?.unsubscribe()
  productSoldSubscription?.unsubscribe()
  auctionSubscription = null
  productSoldSubscription = null
}

const handleRealtimeReady = (client: LiveRealtimeClient) => {
  if (!live.value || !client.connected()) return

  const liveId = live.value.id

  clearAuctionSubscription()
  auctionSubscription = client.subscribe(LIVE_TOPICS.auctions(liveId), (body) => {
    if (isAuctionEventMessage(body) && body.auction.liveId === live.value?.id) {
      applyAuctionSnapshot(body.auction)
    }
  })

  // 시청 화면과 같은 구독 — 판매자도 정찰제로 팔린 상품을 바로 알아야 한다. 모르면 이미 팔린
  // 상품에 경매를 걸려다 뒤늦게 거절당한다(BE 계약: 경매 낙찰은 이 토픽으로 오지 않는다).
  productSoldSubscription = client.subscribe(LIVE_TOPICS.productSold(liveId), (body) => {
    if (isProductSoldMessage(body)) {
      applyProductSoldMessage(body)
    }
  })
}

const applyProductSoldMessage = (message: ProductSoldMessage) => {
  if (!live.value || message.liveId !== live.value.id) return

  const soldProduct = live.value.products.find((product) => product.id === message.productId)

  if (soldProduct) {
    soldProduct.saleStatus = 'SOLD'
  }
}

function isProductSoldMessage(body: unknown): body is ProductSoldMessage {
  return Boolean(
    body &&
    typeof body === 'object' &&
    'liveId' in body &&
    'productId' in body &&
    Number.isInteger((body as ProductSoldMessage).productId),
  )
}

const closeAuctionWin = () => {
  auctionWin.value = null
}

const dismissAuctionStart = () => {
  window.clearTimeout(startNoticeTimer)
  startedAuctionTitle.value = null
}

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
  clearAuctionSubscription()
  window.removeEventListener('beforeunload', handleBeforeUnload)
  window.clearInterval(elapsedTimer)
  window.clearTimeout(transitionNoticeTimer)
  window.clearTimeout(startNoticeTimer)
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
        :products="live.products"
        :manageable-unsold-count="manageableUnsoldProducts.length"
        :is-loading="resultLoading"
        :error-message="resultError"
        @retry="loadBroadcastResults(live.id)"
        @manage-unsold="endView = 'manage'"
        @to-list="router.push({ name: ROUTE_NAMES.HOME })"
      />

      <LiveUnsoldManage
        v-else-if="live.status === 'ENDED' && endView === 'manage'"
        :products="manageableUnsoldProducts"
        @handled="applyUnsoldHandled"
        @back="endView = 'dashboard'"
        @to-list="router.push({ name: ROUTE_NAMES.HOME })"
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

        <main class="live-broadcast-page__content">
          <div class="live-broadcast-page__stage">
            <LiveVideoStage
              :title="live.title"
              :poster-url="live.posterUrl"
              :status="live.status"
              :live-id="live.id"
              :show-try-on="false"
            >
              <template #overlay>
                <LiveChatOverlay
                  :live-id="live.id"
                  :host-id="live.hostId"
                  :status="live.status"
                  @viewer-count="updateViewerCount"
                  @realtime-ready="handleRealtimeReady"
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

            <LiveAuctionStartOverlay
              v-if="startedAuctionTitle"
              :product-title="startedAuctionTitle"
              @close="dismissAuctionStart"
            />

            <p v-if="transitionNotice" class="live-broadcast-page__notice" role="status">
              {{ transitionNotice }}
            </p>
          </div>

          <div class="live-broadcast-page__details">
            <SellerAuctionPanel
              :live-id="live.id"
              :product="selectedProduct"
              :status="live.status"
              :snapshot="auctionSnapshot"
              :is-loading="auctionLoading"
              :load-error="auctionError"
              @snapshot-change="applyAuctionSnapshot"
              @auction-closed="applyAuctionSnapshot"
            />

            <LiveBroadcastInfo :live="live" :elapsed-time="elapsedTime" />
          </div>
        </main>
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
          <p v-if="endError" class="live-broadcast-page__modal-error" role="alert">
            {{ endError }}
          </p>
          <div class="live-broadcast-page__modal-actions">
            <button
              type="button"
              class="live-broadcast-page__modal-cancel"
              :disabled="isEndingBroadcast"
              @click="cancelEndBroadcast"
            >
              {{ endError ? '닫기' : '취소' }}
            </button>
            <button
              type="button"
              class="live-broadcast-page__modal-confirm"
              :disabled="isEndingBroadcast"
              @click="confirmEndBroadcast"
            >
              {{ isEndingBroadcast ? '종료 중…' : endError ? '다시 시도' : '방송 종료' }}
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
  min-height: calc(100vh - var(--button-height-major));
  height: calc(100vh - var(--button-height-major));
  grid-template-columns: 220px minmax(0, 1fr);
}

/* 시청 화면과 동일: 영상(위) / 방송 정보·경매(아래) */
.live-broadcast-page__content {
  display: grid;
  min-width: 0;
  min-height: 0;
  grid-template-rows: minmax(340px, 1fr) 260px;
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
  min-height: var(--button-height-sm);
  border: 1px solid var(--color-live);
  border-radius: var(--radius-control);
  background: color-mix(in srgb, var(--color-live) 18%, transparent);
  color: var(--color-live-text-primary);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-bold);
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

.live-broadcast-page__details {
  display: grid;
  min-width: 0;
  min-height: 0;
  grid-template-columns: minmax(0, 1fr) 300px;
  border-top: 1px solid var(--color-live-border);
  background: var(--color-live-background);
}

.live-broadcast-page__details > * {
  min-width: 0;
  min-height: 0;
  overflow-y: auto;
}

.live-broadcast-page__details > :last-child {
  padding: var(--space-4);
}

.live-broadcast-page__details > * + * {
  border-left: 1px solid var(--color-live-border);
}

.live-broadcast-page__slot-note {
  color: var(--color-live-text-secondary);
  font-size: var(--font-size-badge);
  letter-spacing: 0.02em;
  opacity: 0.75;
}

.live-broadcast-page__notice {
  position: absolute;
  z-index: var(--z-layer-3);
  top: var(--space-4);
  left: 50%;
  max-width: calc(100% - var(--space-8));
  padding: 8px 16px;
  border: 1px solid var(--color-live-border);
  border-radius: var(--radius-chip);
  background: rgba(10, 12, 11, 0.86);
  color: var(--color-primary-strong);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-semibold);
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
  z-index: var(--z-top);
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
  font-weight: var(--font-weight-extrabold);
}

.live-broadcast-page__modal p {
  color: var(--color-live-text-secondary);
  font-size: var(--font-size-caption);
  line-height: var(--line-height-control);
}

.live-broadcast-page__modal .live-broadcast-page__modal-error {
  color: var(--color-error);
  font-weight: var(--font-weight-semibold);
}

.live-broadcast-page__modal-actions button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.live-broadcast-page__modal-actions {
  display: flex;
  margin-top: var(--space-3);
  gap: var(--space-2);
}

.live-broadcast-page__modal-actions button {
  flex: 1;
  min-height: var(--button-height-tight);
  border-radius: var(--radius-control);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-bold);
}

.live-broadcast-page__modal-cancel {
  border: 1px solid var(--color-live-border);
  background: transparent;
  color: var(--color-live-text-primary);
}

.live-broadcast-page__modal-confirm {
  border: 1px solid color-mix(in srgb, var(--color-error) 55%, transparent);
  background: var(--color-error);
  color: var(--color-primary-strong);
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
  height: var(--button-height-major);
  border-bottom: 1px solid var(--color-live-border);
  background: var(--color-live-surface);
}

.live-broadcast-loading__body {
  display: grid;
  min-height: calc(100vh - var(--button-height-major));
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
  .live-broadcast-page__body {
    grid-template-columns: 200px minmax(0, 1fr);
  }

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

  .live-broadcast-page__content {
    height: auto;
    grid-template-rows: var(--surface-min-height-xl) auto;
  }

  .live-broadcast-page__stage {
    min-height: var(--surface-min-height-xl);
  }

  .live-broadcast-page__details {
    grid-template-columns: minmax(0, 1fr);
  }

  .live-broadcast-loading__body {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
