<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import LiveChatOverlay from '@/domains/chat/components/LiveChatOverlay.vue'
import {
  getLiveWatchViewData,
  isLiveWatchApiEnabled,
  LiveWatchNotFoundError,
} from '@/domains/live/api/liveWatchApi'
import LiveBroadcastHeader from '@/domains/live/components/LiveBroadcastHeader.vue'
import LiveBroadcastInfo from '@/domains/live/components/LiveBroadcastInfo.vue'
import LiveProductQueue from '@/domains/live/components/LiveProductQueue.vue'
import LiveVideoStage from '@/domains/live/components/LiveVideoStage.vue'
import LiveWatchState from '@/domains/live/components/LiveWatchState.vue'
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
const now = ref(Date.now())
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

    live.value = response
    selectedProductId.value = response.currentProductId ?? response.products.at(0)?.id ?? null
    now.value = Date.now()
    loadState.value = 'success'
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

// 판매자 제어(437). 서버 반영 계약이 없어 로컬 상태(mock)만 바꾼다.
// 실제 전환/종료 엔드포인트·시청자 전파는 docs/requests/BE/013 요청 후 연결.
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

const confirmEndBroadcast = () => {
  if (!live.value) return

  live.value = {
    ...live.value,
    status: 'ENDED',
    endedAt: new Date(now.value).toISOString(),
  }
  isEndConfirmOpen.value = false
}

const updateViewerCount = (viewerCount: number) => {
  if (!live.value) return

  live.value = {
    ...live.value,
    currentViewerCount: viewerCount,
  }
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
      <LiveBroadcastHeader
        :live="live"
        :elapsed-time="elapsedTime"
        @back="goBack"
        @end-broadcast="requestEndBroadcast"
      />

      <div class="live-broadcast-page__body">
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

          <p v-if="transitionNotice" class="live-broadcast-page__notice" role="status">
            {{ transitionNotice }}
          </p>

          <div
            v-if="live.status === 'ENDED'"
            class="live-broadcast-page__ended"
            role="status"
          >
            <strong>방송을 종료했습니다</strong>
            <p>시청자에게 방송이 종료된 것으로 표시됩니다.</p>
            <button type="button" @click="router.push({ name: ROUTE_NAMES.LIVE_LIST })">
              라이브 목록으로
            </button>
          </div>
        </main>

        <aside class="live-broadcast-page__control">
          <LiveBroadcastInfo :live="live" :elapsed-time="elapsedTime" />

          <!-- 경매 설정 패널 자리 — 436에서 구현 -->
          <section class="live-broadcast-page__auction-slot" aria-label="경매 설정">
            <div class="live-broadcast-page__slot-head">
              <h2>경매 설정</h2>
              <span>준비 중</span>
            </div>
            <p class="live-broadcast-page__slot-body">
              {{
                selectedProduct
                  ? `‘${selectedProduct.title}’ 상품의 경매 시작가·증가폭·시간 설정 패널이 이 자리에 들어갑니다.`
                  : '상품을 선택하면 경매 설정 패널이 이 자리에 표시됩니다.'
              }}
            </p>
            <p class="live-broadcast-page__slot-note">경매 설정 패널 · 436에서 구현</p>
          </section>
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

.live-broadcast-page__auction-slot {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-4);
  border: 1px dashed var(--color-live-border);
  border-radius: var(--radius-control);
  background: var(--color-live-surface);
}

.live-broadcast-page__slot-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.live-broadcast-page__slot-head h2 {
  color: var(--color-live-text-primary);
  font-size: 13px;
  font-weight: 700;
}

.live-broadcast-page__slot-head span {
  display: inline-flex;
  align-items: center;
  min-height: 20px;
  padding: 0 7px;
  border-radius: var(--radius-badge);
  background: var(--color-live-surface-raised);
  color: var(--color-live-text-secondary);
  font-size: 10px;
  font-weight: 700;
}

.live-broadcast-page__slot-body {
  color: var(--color-live-text-secondary);
  font-size: 12px;
  line-height: 18px;
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

.live-broadcast-page__ended {
  display: grid;
  position: absolute;
  z-index: 4;
  inset: 0;
  align-content: center;
  justify-items: center;
  gap: var(--space-3);
  padding: var(--space-6);
  background: rgba(6, 8, 7, 0.78);
  text-align: center;
  backdrop-filter: blur(3px);
}

.live-broadcast-page__ended strong {
  color: #fff;
  font-size: 20px;
  font-weight: 800;
}

.live-broadcast-page__ended p {
  max-width: 320px;
  color: var(--color-live-text-secondary);
  font-size: 13px;
  line-height: 20px;
}

.live-broadcast-page__ended button {
  min-height: 42px;
  margin-top: var(--space-2);
  padding: 0 var(--space-6);
  border: 0;
  border-radius: var(--radius-control);
  background: var(--color-live);
  color: var(--color-text-inverse);
  font-size: 14px;
  font-weight: 700;
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
