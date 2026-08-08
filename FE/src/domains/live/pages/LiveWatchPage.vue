<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { getCurrentAuction, isAuctionEventMessage } from '@/domains/auction/api/auctionApi'
import LiveAuctionPanel from '@/domains/auction/components/LiveAuctionPanel.vue'
import LiveAuctionResultOverlay from '@/domains/auction/components/LiveAuctionResultOverlay.vue'
import LiveAuctionStartOverlay from '@/domains/auction/components/LiveAuctionStartOverlay.vue'
import { useAuthStore } from '@/domains/auth/stores/authStore'
import LiveChatOverlay from '@/domains/chat/components/LiveChatOverlay.vue'
import { getMyProfile } from '@/domains/my/api/myApi'
import { createOrder, updateOrderAddress } from '@/domains/order/api/orderApi'
import PurchaseConfirmDialog from '@/domains/order/components/PurchaseConfirmDialog.vue'
import { LiveRealtimeClient } from '@/domains/live/api/liveRealtimeClient'
import {
  cancelLiveReminder,
  getLiveWatchViewData,
  isLiveWatchApiEnabled,
  LiveWatchNotFoundError,
  registerLiveReminder,
} from '@/domains/live/api/liveWatchApi'
import LiveDirectSalePanel from '@/domains/live/components/LiveDirectSalePanel.vue'
import LiveProductQueue from '@/domains/live/components/LiveProductQueue.vue'
import { LIVE_TOPICS } from '@/domains/live/constants/liveRealtimeTopics'
import LiveSelectedProduct from '@/domains/live/components/LiveSelectedProduct.vue'
import LiveVideoStage from '@/domains/live/components/LiveVideoStage.vue'
import LiveWatchHeader from '@/domains/live/components/LiveWatchHeader.vue'
import LiveWatchState from '@/domains/live/components/LiveWatchState.vue'
import { addWish, getWishProductIds, removeWish } from '@/domains/product/api/productApi'
import { useWishStore } from '@/domains/product/stores/wishStore'
import { getPointBalance } from '@/domains/point/api/pointApi'
import { dispatchPointBalanceUpdated } from '@/domains/point/utils/pointBalanceEvents'
import { followUser, getPublicProfile, unfollowUser } from '@/domains/profile/api/profileApi'
import { useFollowStore } from '@/domains/profile/stores/followStore'
import LiveTryOnPanel from '@/domains/tryon/components/LiveTryOnPanel.vue'
import { LIVE_TRY_ON_MOCK_SCENARIOS } from '@/domains/tryon/types/liveTryOn.types'
import { normalizeApiError } from '@/shared/api/http'
import { ROUTE_NAMES } from '@/shared/constants/routes'
import LiveLayout from '@/shared/layouts/LiveLayout.vue'

import type { AuctionSnapshot } from '@/domains/auction/types/liveAuction.types'
import type { OrderAddressInput } from '@/domains/order/types/order.types'
import type {
  CurrentProductMessage,
  LiveStatusMessage,
  LiveWatchLoadState,
  LiveWatchMockScenario,
  LiveWatchProduct,
  LiveWatchViewData,
  ProductSoldMessage,
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
const authStore = useAuthStore()
const wishStore = useWishStore()
const live = ref<LiveWatchViewData | null>(null)
const loadState = ref<LiveWatchLoadState>('loading')
const errorMessage = ref('')
const selectedProductId = ref<number | null>(null)
const followStore = useFollowStore()
const isFollowingHost = computed(() =>
  live.value
    ? followStore.getFollowState(live.value.hostId, { followerCount: 0, isFollowing: false })
        .isFollowing
    : false,
)
const pendingWishProductId = ref<number | null>(null)
const wishMessage = ref('')
const purchaseProductId = ref<number | null>(null)
const isPurchaseDialogOpen = ref(false)
const isPurchaseBalanceLoading = ref(false)
const isPurchaseSubmitting = ref(false)
const purchasePointBalance = ref<number | null>(null)
const purchaseInitialAddress = ref<OrderAddressInput | null>(null)
const purchaseErrorMessage = ref('')
const purchaseMessage = ref('')
const isTryOnOpen = ref(false)
const now = ref(Date.now())
const auctionSnapshot = ref<AuctionSnapshot | null>(null)
const isAuctionLoading = ref(false)
const auctionLoadError = ref('')
const dismissedAuctionResultId = ref<number | null>(null)
const announcedAuctionId = ref<number | null>(null)
// 경매 시작 알림 — 확인 시 그 상품으로 이동해야 해서 제목만이 아니라 productId도 들고 있는다.
const startedAuction = ref<{ productId: number; title: string } | null>(null)
let startNoticeTimer: number | undefined
const apiEnabled = isLiveWatchApiEnabled()

const loadHostFollowState = async (hostId: number) => {
  try {
    const hostProfile = await getPublicProfile(hostId)
    followStore.setFollowState(hostId, {
      followerCount: hostProfile.followerCount,
      isFollowing: hostProfile.isFollowing,
    })
  } catch {
    // 팔로우 상태 보강 실패는 무시한다 — 버튼은 기본값(false)으로 남는다.
  }
}

const handleToggleFollow = async () => {
  if (!live.value || followStore.isPending(live.value.hostId)) {
    return
  }

  const hostId = live.value.hostId
  const previousState = followStore.getFollowState(hostId, { followerCount: 0, isFollowing: false })

  if (previousState.isFollowing && !window.confirm('팔로우를 취소하시겠습니까?')) {
    return
  }

  const nextIsFollowing = !previousState.isFollowing

  followStore.setPending(hostId, true)
  followStore.setFollowState(hostId, { isFollowing: nextIsFollowing })

  try {
    if (previousState.isFollowing) {
      await unfollowUser(hostId)
    } else {
      const response = await followUser(hostId)
      followStore.setFollowState(hostId, {
        followerCount: response.followerCount,
        isFollowing: response.isFollowing,
      })
    }
  } catch {
    followStore.setFollowState(hostId, previousState)
  } finally {
    followStore.setPending(hostId, false)
  }
}

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
let loadRequestId = 0
let statusSubscription: ReturnType<LiveRealtimeClient['subscribe']> | null = null
let currentProductSubscription: ReturnType<LiveRealtimeClient['subscribe']> | null = null
let productSoldSubscription: ReturnType<LiveRealtimeClient['subscribe']> | null = null
let auctionSubscription: ReturnType<LiveRealtimeClient['subscribe']> | null = null

const getRouteLiveId = () => {
  const routeValue = Array.isArray(route.params.liveId)
    ? route.params.liveId[0]
    : route.params.liveId
  const liveId = Number(routeValue)

  return Number.isInteger(liveId) && liveId > 0 ? liveId : null
}

const getMockScenario = (): LiveWatchMockScenario => {
  const queryValue = Array.isArray(route.query.mock) ? route.query.mock[0] : route.query.mock

  return LIVE_WATCH_MOCK_SCENARIOS.includes(queryValue as LiveWatchMockScenario)
    ? (queryValue as LiveWatchMockScenario)
    : 'default'
}

const tryOnMockScenario = computed<LiveTryOnMockScenario>(() => {
  const queryValue = Array.isArray(route.query.tryon) ? route.query.tryon[0] : route.query.tryon

  return LIVE_TRY_ON_MOCK_SCENARIOS.includes(queryValue as LiveTryOnMockScenario)
    ? (queryValue as LiveTryOnMockScenario)
    : 'ready'
})

const selectedProduct = computed(
  () => live.value?.products.find((product) => product.id === selectedProductId.value) ?? null,
)

const purchaseProduct = computed(
  () => live.value?.products.find((product) => product.id === purchaseProductId.value) ?? null,
)

// saleType이 비어 있어도 saleStatus로 경매 상품을 가려낸다(BE 016 §6-B — DRAFT 상품은 saleType이 null).
const isAuctionProduct = (product: LiveWatchProduct) =>
  product.saleType === 'AUCTION' ||
  product.saleStatus === 'AUCTION_SCHEDULED' ||
  product.saleStatus === 'AUCTION_IN_PROGRESS'

// 시청자가 지금 보고 있는(큐에서 고른) 상품이 경매 대상인지 — 그 상품의 경매가 걸려 있을 때만
// 경매 패널을 유지한다. 다른 상품의 경매가 돌고 있어도 정찰제 상품을 고르면 정찰제 패널로 바꾼다.
const isSelectedProductOnAuction = computed(() => {
  const snapshot = auctionSnapshot.value

  return Boolean(
    snapshot &&
    snapshot.productId === selectedProductId.value &&
    (snapshot.status === 'RUNNING' || snapshot.status === 'READY'),
  )
})

// 패널은 시청자가 고른 상품을 기준으로 가른다. 경매 상품이 아니면 정찰제 구매 패널을 띄우고,
// saleType이 null로 와도 가격이 붙어 있으면 정찰제로 본다 — 실제 구매 가능 여부는
// LiveDirectSalePanel이 saleStatus/price로 다시 막는다.
const isDirectSaleSelected = computed(() => {
  const product = selectedProduct.value

  if (!product) return false
  if (isSelectedProductOnAuction.value) return false
  if (isAuctionProduct(product)) return false

  return product.saleType === 'DIRECT_SALE' || product.price !== null
})

const isTryOnAvailable = computed(
  () => live.value?.status === 'LIVE' && selectedProduct.value !== null,
)

const isSelectedProductWished = computed(
  () => selectedProductId.value !== null && wishStore.isProductWished(selectedProductId.value),
)

const auctionWin = computed(() => {
  const snapshot = auctionSnapshot.value

  if (
    dismissedAuctionResultId.value === snapshot?.auctionId ||
    snapshot?.status !== 'SUCCESS' ||
    !snapshot.highestBidderNickname
  ) {
    return null
  }

  return {
    winnerNickname: snapshot.highestBidderNickname,
    winningBid: snapshot.currentPrice,
    productTitle: snapshot.productTitle,
  }
})

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

  clearRealtimeSubscriptions()
  live.value = null
  selectedProductId.value = null
  purchaseProductId.value = null
  isPurchaseDialogOpen.value = false
  purchaseMessage.value = ''
  isTryOnOpen.value = false
  loadState.value = 'loading'
  errorMessage.value = ''
  auctionSnapshot.value = null
  auctionLoadError.value = ''
  dismissedAuctionResultId.value = null

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
    selectedProductId.value = response.currentProductId ?? response.products.at(0)?.id ?? null
    now.value = Date.now()
    loadState.value = 'success'
    void loadHostFollowState(response.hostId)
    void loadProductWishState(response.products.map((product) => product.id))
    void loadAuction(response.id)
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

const loadAuction = async (liveId: number) => {
  if (!apiEnabled) {
    auctionSnapshot.value = null
    isAuctionLoading.value = false
    auctionLoadError.value = ''
    return
  }

  isAuctionLoading.value = true
  auctionLoadError.value = ''

  try {
    const snapshot = await getCurrentAuction(liveId)
    if (live.value?.id === liveId) {
      auctionSnapshot.value = snapshot
      // 접속 시점에 이미 진행 중인 경매는 '시작 알림'을 띄우지 않는다(이미 announced 처리).
      announcedAuctionId.value = snapshot?.status === 'RUNNING' ? snapshot.auctionId : null
    }
  } catch (error) {
    if (live.value?.id === liveId) {
      auctionSnapshot.value = null
      auctionLoadError.value =
        error instanceof Error ? error.message : '경매 정보를 불러오지 못했습니다.'
    }
  } finally {
    if (live.value?.id === liveId) {
      isAuctionLoading.value = false
    }
  }
}

const applyAuctionSnapshot = (snapshot: AuctionSnapshot | null) => {
  auctionSnapshot.value = snapshot
  auctionLoadError.value = ''

  // 경매가 새로 시작(RUNNING)되면 시청자에게 팝업으로 알린다.
  if (
    snapshot &&
    snapshot.status === 'RUNNING' &&
    snapshot.auctionId !== announcedAuctionId.value
  ) {
    announcedAuctionId.value = snapshot.auctionId
    startedAuction.value = {
      productId: snapshot.productId,
      title: snapshot.productTitle || '상품',
    }
    window.clearTimeout(startNoticeTimer)
    startNoticeTimer = window.setTimeout(() => {
      startedAuction.value = null
    }, 4000)
  }

  // 낙찰(SUCCESS)되면 그 상품은 즉시 SOLD가 되므로 상품 큐에도 바로 반영한다.
  if (snapshot && snapshot.status === 'SUCCESS' && live.value) {
    const soldProduct = live.value.products.find((product) => product.id === snapshot.productId)
    if (soldProduct) {
      soldProduct.saleStatus = 'SOLD'
    }
  }
}

const closeAuctionResult = () => {
  dismissedAuctionResultId.value = auctionSnapshot.value?.auctionId ?? null
}

// 시작 알림의 확인을 누르면 그 경매 상품으로 바로 들어간다 — 상품이 선택되면 아래 패널도
// 경매로 전환된다(isDirectSaleSelected가 경매 상품을 걸러낸다).
// 알림이 저절로 사라지는 경우(4초 타임아웃)에는 선택을 건드리지 않는다.
const enterStartedAuction = () => {
  const started = startedAuction.value

  window.clearTimeout(startNoticeTimer)
  startedAuction.value = null

  if (started) {
    selectedProductId.value = started.productId
  }
}

const showLeaveConfirm = ref(false)

// 시청자가 라이브에서 나가려 하면 확인 모달을 띄우고, 확인 시 홈으로 보낸다.
const goBack = () => {
  showLeaveConfirm.value = true
}

const confirmLeave = () => {
  showLeaveConfirm.value = false
  void router.push({ name: ROUTE_NAMES.HOME })
}

const cancelLeave = () => {
  showLeaveConfirm.value = false
}

const showEndedNotice = ref(false)

const leaveEndedLive = () => {
  showEndedNotice.value = false
  void router.push({ name: ROUTE_NAMES.HOME })
}

// 시청자가 큐에서 상품을 고르면 그 선택을 기준으로 상세 정보와 구매·경매 패널이 바뀐다.
// 판매자가 다음 상품으로 넘어가면 다시 그쪽으로 맞춰진다(applyCurrentProductMessage).
const selectQueueProduct = (productId: number) => {
  selectedProductId.value = productId
}

const goToProduct = (productId: number) => {
  void router.push({
    name: ROUTE_NAMES.PRODUCT_DETAIL,
    params: { productId },
  })
}

const openDirectPurchase = async () => {
  const currentLive = live.value
  const product = selectedProduct.value

  if (
    !currentLive ||
    !product ||
    currentLive.isHost ||
    currentLive.status !== 'LIVE' ||
    product.saleType !== 'DIRECT_SALE' ||
    product.saleStatus !== 'ON_SALE' ||
    product.price === null
  ) {
    return
  }

  if (!authStore.isAuthenticated || !authStore.user) {
    await router.push({
      name: ROUTE_NAMES.AUTH_LOGIN,
      query: { redirect: route.fullPath },
    })
    return
  }

  purchaseProductId.value = product.id
  purchaseErrorMessage.value = ''
  purchaseMessage.value = ''
  isPurchaseDialogOpen.value = true
  isPurchaseBalanceLoading.value = true
  purchasePointBalance.value = null
  purchaseInitialAddress.value = null

  const [balanceResult, profileResult] = await Promise.allSettled([
    getPointBalance(authStore.user.id),
    getMyProfile(authStore.user.id),
  ])

  if (balanceResult.status === 'fulfilled') {
    purchasePointBalance.value = balanceResult.value.available
  }

  if (profileResult.status === 'fulfilled' && profileResult.value.address.trim() !== '') {
    const profile = profileResult.value
    purchaseInitialAddress.value = {
      recipientName: profile.name,
      recipientPhone: profile.phoneNumber,
      zipcode: profile.postalCode ?? '',
      address1: profile.address,
      address2: profile.detailAddress,
    }
  }

  isPurchaseBalanceLoading.value = false
}

const closePurchaseDialog = () => {
  if (isPurchaseSubmitting.value) return

  isPurchaseDialogOpen.value = false
  purchaseErrorMessage.value = ''
}

const refreshPurchasePointBalance = async (userId: number) => {
  const balance = await getPointBalance(userId).catch(() => null)

  if (balance) {
    purchasePointBalance.value = balance.available
    dispatchPointBalanceUpdated({ userId, balance })
  }
}

const handlePurchaseSubmit = async (address: OrderAddressInput) => {
  const currentLive = live.value
  const product = purchaseProduct.value
  const userId = authStore.user?.id

  if (
    !currentLive ||
    !product ||
    !userId ||
    product.saleType !== 'DIRECT_SALE' ||
    product.saleStatus !== 'ON_SALE'
  ) {
    return
  }

  isPurchaseSubmitting.value = true
  purchaseErrorMessage.value = ''

  try {
    const order = await createOrder(product.id, currentLive.id)

    product.saleStatus = 'SOLD'
    isPurchaseDialogOpen.value = false

    try {
      await updateOrderAddress(order.orderId, address)
      purchaseMessage.value = '구매가 완료되었습니다.'
    } catch {
      purchaseMessage.value =
        '구매는 완료됐지만 배송지 등록에 실패했습니다. 구매 내역에서 다시 입력해 주세요.'
    }

    await refreshPurchasePointBalance(userId)
  } catch (error) {
    const apiError = normalizeApiError(error)
    purchaseErrorMessage.value =
      apiError.code === 'W001'
        ? '포인트가 부족합니다. 충전 후 다시 시도해 주세요.'
        : apiError.message

    if (apiError.code === 'W001') {
      await refreshPurchasePointBalance(userId)
    }
  } finally {
    isPurchaseSubmitting.value = false
  }
}

const loadProductWishState = async (productIds: number[]) => {
  wishStore.hydrateProducts(productIds.map((id) => ({ id, isWished: false })))

  if (!authStore.isAuthenticated || !authStore.user?.id || productIds.length === 0) {
    return
  }

  try {
    const wishedProductIds = new Set(await getWishProductIds(authStore.user.id))
    wishStore.hydrateWishedProductIds([...wishedProductIds])
    wishStore.hydrateProducts(
      productIds.map((id) => ({
        id,
        isWished: wishedProductIds.has(id),
      })),
    )
  } catch {
    wishMessage.value = '찜 상태를 불러오지 못했습니다.'
  }
}

const toggleWish = async () => {
  const productId = selectedProductId.value

  if (productId === null || pendingWishProductId.value === productId) return

  if (!authStore.isAuthenticated || !authStore.user?.id) {
    await router.push({ name: ROUTE_NAMES.AUTH_LOGIN })
    return
  }

  const wasWished = wishStore.isProductWished(productId)

  pendingWishProductId.value = productId
  wishMessage.value = ''
  wishStore.setProductWish(productId, !wasWished)

  try {
    if (wasWished) {
      await removeWish(authStore.user.id, productId)
    } else {
      await addWish(authStore.user.id, productId)
    }
  } catch {
    wishStore.setProductWish(productId, wasWished)
    wishMessage.value = '찜 상태를 변경하지 못했습니다. 잠시 후 다시 시도해 주세요.'
  } finally {
    pendingWishProductId.value = null
  }
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
    peakViewerCount: Math.max(live.value.peakViewerCount, viewerCount),
  }
}

// 시청 화면의 STOMP 연결은 LiveChatOverlay 하나만 쓴다(연결 2개 → 세션 2개로 시청자수가
// 2배 집계되던 문제 수정). 오버레이가 연결되면(realtime-ready) 그 연결에 방송 상태·현재
// 상품 구독만 얹는다. 채팅/반응/시청자수 구독과 발행은 계속 오버레이가 담당한다.
const handleRealtimeReady = (client: LiveRealtimeClient) => {
  clearRealtimeSubscriptions()

  const liveId = live.value?.id
  if (liveId === undefined) return

  statusSubscription = client.subscribe(LIVE_TOPICS.status(liveId), (body) => {
    if (isLiveStatusMessage(body)) {
      applyStatusMessage(body)
    }
  })

  currentProductSubscription = client.subscribe(LIVE_TOPICS.currentProduct(liveId), (body) => {
    if (isCurrentProductMessage(body)) {
      applyCurrentProductMessage(body)
    }
  })

  productSoldSubscription = client.subscribe(LIVE_TOPICS.productSold(liveId), (body) => {
    if (isProductSoldMessage(body)) {
      applyProductSoldMessage(body)
    }
  })

  auctionSubscription = client.subscribe(LIVE_TOPICS.auctions(liveId), (body) => {
    if (isAuctionEventMessage(body) && body.auction.liveId === liveId) {
      applyAuctionSnapshot(body.auction)
    }
  })
}

const clearRealtimeSubscriptions = () => {
  statusSubscription?.unsubscribe()
  currentProductSubscription?.unsubscribe()
  productSoldSubscription?.unsubscribe()
  auctionSubscription?.unsubscribe()
  statusSubscription = null
  currentProductSubscription = null
  productSoldSubscription = null
  auctionSubscription = null
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
    clearRealtimeSubscriptions()
    showEndedNotice.value = true
  }
}

// 판매자가 소개 상품을 바꾸면 시청자 선택도 그 상품으로 맞춘다 — 방송이 지금 다루는 상품이
// 선택 상품 정보·구매/경매 패널에 그대로 떠야 한다. 시청자가 다른 상품을 눌러 보고 있었더라도
// 다음 전환 때 방송을 따라간다(-430 QA).
const applyCurrentProductMessage = (message: CurrentProductMessage) => {
  if (!live.value || message.liveId !== live.value.id) return

  live.value = {
    ...live.value,
    currentProductId: message.currentProductId,
  }

  if (message.currentProductId !== null) {
    selectedProductId.value = message.currentProductId
  }
}

// 정찰제 즉시구매로 팔린 상품을 큐에서 판매완료로 바꾼다. 구매 당사자도 같은 이벤트를 받지만
// 이미 로컬에서 SOLD로 바꾼 뒤라 같은 값을 다시 넣는 것뿐이다(멱등) — 자기 이벤트를 거르지 않는다.
const applyProductSoldMessage = (message: ProductSoldMessage) => {
  if (!live.value || message.liveId !== live.value.id) return

  const soldProduct = live.value.products.find((product) => product.id === message.productId)

  if (soldProduct) {
    soldProduct.saleStatus = 'SOLD'
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

function isProductSoldMessage(body: unknown): body is ProductSoldMessage {
  return Boolean(
    body &&
    typeof body === 'object' &&
    'liveId' in body &&
    'productId' in body &&
    Number.isInteger((body as ProductSoldMessage).productId),
  )
}

function isCurrentProductMessage(body: unknown): body is CurrentProductMessage {
  return Boolean(body && typeof body === 'object' && 'liveId' in body && 'currentProductId' in body)
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

watch(selectedProductId, () => {
  wishMessage.value = ''
  purchaseMessage.value = ''
})

const elapsedTimer = window.setInterval(() => {
  now.value = Date.now()
}, 1000)

onBeforeUnmount(() => {
  loadRequestId += 1
  window.clearInterval(elapsedTimer)
  window.clearTimeout(startNoticeTimer)
  clearRealtimeSubscriptions()
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
        :is-following="isFollowingHost"
        @back="goBack"
        @toggle-follow="handleToggleFollow"
      />

      <div class="live-watch-page__body">
        <LiveProductQueue
          :products="live.products"
          :current-product-id="live.currentProductId"
          :selected-product-id="selectedProductId"
          @select="selectQueueProduct"
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
              :live-id="live.id"
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
                  @realtime-ready="handleRealtimeReady"
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

            <LiveAuctionResultOverlay
              v-if="auctionWin"
              :winner-nickname="auctionWin.winnerNickname"
              :winning-bid="auctionWin.winningBid"
              :product-title="auctionWin.productTitle"
              @close="closeAuctionResult"
            />

            <LiveAuctionStartOverlay
              v-if="startedAuction"
              :product-title="startedAuction.title"
              @close="enterStartedAuction"
            />
          </div>

          <div class="live-watch-page__details">
            <LiveSelectedProduct
              :product="selectedProduct"
              :is-wished="isSelectedProductWished"
              :is-wish-pending="pendingWishProductId === selectedProductId"
              :wish-message="wishMessage"
              @view-product="goToProduct"
              @toggle-wish="toggleWish"
            />
            <LiveDirectSalePanel
              v-if="selectedProduct && isDirectSaleSelected"
              :product="selectedProduct"
              :live-status="live.status"
              :is-host="live.isHost"
              :message="purchaseMessage"
              @purchase="openDirectPurchase"
            />
            <LiveAuctionPanel
              v-else
              :snapshot="auctionSnapshot"
              :live-status="live.status"
              :is-loading="isAuctionLoading"
              :load-error="auctionLoadError"
              @snapshot-change="applyAuctionSnapshot"
            />
          </div>
        </main>
      </div>
    </div>

    <PurchaseConfirmDialog
      v-if="isPurchaseDialogOpen && purchaseProduct && purchaseProduct.price !== null"
      :product-title="purchaseProduct.title"
      :product-price="purchaseProduct.price"
      :product-thumbnail-url="purchaseProduct.thumbnailUrl ?? ''"
      :point-balance="purchasePointBalance"
      :is-balance-loading="isPurchaseBalanceLoading"
      :is-submitting="isPurchaseSubmitting"
      :error-message="purchaseErrorMessage"
      :initial-address="purchaseInitialAddress"
      @close="closePurchaseDialog"
      @submit="handlePurchaseSubmit"
    />

    <div v-if="showLeaveConfirm" class="live-watch-page__modal-backdrop" @click.self="cancelLeave">
      <div
        class="live-watch-page__modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="live-leave-title"
      >
        <h2 id="live-leave-title">라이브에서 나가시겠어요?</h2>
        <p>나가면 홈 화면으로 이동합니다.</p>
        <div class="live-watch-page__modal-actions">
          <button type="button" class="live-watch-page__modal-cancel" @click="cancelLeave">
            취소
          </button>
          <button type="button" class="live-watch-page__modal-confirm" @click="confirmLeave">
            나가기
          </button>
        </div>
      </div>
    </div>

    <div v-if="showEndedNotice" class="live-watch-page__modal-backdrop">
      <div
        class="live-watch-page__modal"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="live-ended-title"
      >
        <h2 id="live-ended-title">라이브가 종료되었습니다</h2>
        <p>방송이 종료되어 더 이상 시청할 수 없습니다.</p>
        <div class="live-watch-page__modal-actions">
          <button type="button" class="live-watch-page__modal-confirm" @click="leaveEndedLive">
            홈으로 가기
          </button>
        </div>
      </div>
    </div>
  </LiveLayout>
</template>

<style scoped lang="scss">
.live-watch-page {
  min-height: 100vh;
  background: var(--color-live-background);
}

.live-watch-page__modal-backdrop {
  display: grid;
  position: fixed;
  z-index: var(--z-top);
  inset: 0;
  place-items: center;
  padding: var(--space-4);
  background: rgba(4, 6, 5, 0.62);
}

.live-watch-page__modal {
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

.live-watch-page__modal h2 {
  color: var(--color-live-text-primary);
  font-size: 17px;
  font-weight: var(--font-weight-extrabold);
}

.live-watch-page__modal p {
  color: var(--color-live-text-secondary);
  font-size: var(--font-size-caption);
  line-height: var(--line-height-control);
}

.live-watch-page__modal-actions {
  display: flex;
  margin-top: var(--space-3);
  gap: var(--space-2);
}

.live-watch-page__modal-actions button {
  flex: 1;
  min-height: var(--button-height-tight);
  border-radius: var(--radius-control);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-bold);
}

.live-watch-page__modal-cancel {
  border: 1px solid var(--color-live-border);
  background: transparent;
  color: var(--color-live-text-primary);
}

.live-watch-page__modal-confirm {
  border: 1px solid var(--color-accent);
  background: var(--color-accent);
  color: var(--color-primary-strong);
}

.live-watch-page__modal-cancel:hover {
  background: var(--color-live-surface-raised);
}

.live-watch-page__modal-confirm:hover {
  opacity: 0.92;
}

.live-watch-page__body {
  display: grid;
  min-height: calc(100vh - var(--button-height-major));
  grid-template-columns: 220px minmax(0, 1fr);
}

.live-watch-page__content {
  display: grid;
  min-width: 0;
  min-height: 0;
  height: calc(100vh - var(--button-height-major));
  grid-template-rows: minmax(340px, 1fr) 260px;
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
  height: var(--button-height-major);
  border-bottom: 1px solid var(--color-live-border);
  background:
    linear-gradient(90deg, transparent 20%, rgba(255, 255, 255, 0.06) 40%, transparent 60%),
    var(--color-live-surface);
  background-size: 200% 100%;
  animation: live-watch-shimmer 1.6s infinite linear;
}

.live-watch-loading__body {
  display: grid;
  min-height: calc(100vh - var(--button-height-major));
  grid-template-columns: 220px minmax(0, 1fr);
}

.live-watch-loading__body > aside {
  border-right: 1px solid var(--color-live-border);
  background: var(--color-live-surface);
}

.live-watch-loading__body > main {
  display: grid;
  grid-template-rows: minmax(340px, 1fr) 290px;
}

.live-watch-loading__body > main > div {
  background:
    linear-gradient(105deg, transparent 25%, rgba(255, 255, 255, 0.05) 42%, transparent 58%),
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
    grid-template-rows: var(--surface-min-height-lg) auto;
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
    grid-template-rows: var(--surface-min-height-lg) 180px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .live-watch-loading__header,
  .live-watch-loading__body > main > div {
    animation: none;
  }
}
</style>
