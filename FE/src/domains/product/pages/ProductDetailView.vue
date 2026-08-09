<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '@/domains/auth/stores/authStore'
import { getMyProfile } from '@/domains/my/api/myApi'
import { createOrder, updateOrderAddress } from '@/domains/order/api/orderApi'
import PurchaseConfirmDialog from '@/domains/order/components/PurchaseConfirmDialog.vue'
import type { OrderAddressInput } from '@/domains/order/types/order.types'
import { addWish, getProductAiModelCutStatus, removeWish } from '@/domains/product/api/productApi'
import { useWishStore } from '@/domains/product/stores/wishStore'
import {
  getProductDetailViewData,
  ProductDetailNotFoundError,
} from '@/domains/product/api/productDetailApi'
import AiQualityAnalysisPanel from '@/domains/product/components/AiQualityAnalysisPanel.vue'
import ProductDetailInformation from '@/domains/product/components/ProductDetailInformation.vue'
import ProductDetailSkeleton from '@/domains/product/components/ProductDetailSkeleton.vue'
import ProductDetailStatePanel from '@/domains/product/components/ProductDetailStatePanel.vue'
import ProductImageGallery from '@/domains/product/components/ProductImageGallery.vue'
import ProductPriceDistribution from '@/domains/product/components/ProductPriceDistribution.vue'
import ProductPriceEstimateCard from '@/domains/product/components/ProductPriceEstimateCard.vue'
import ProductPurchaseSummary from '@/domains/product/components/ProductPurchaseSummary.vue'
import ProductSellerLivePanel from '@/domains/product/components/ProductSellerLivePanel.vue'
import ProductSimilarRecommendation from '@/domains/product/components/ProductSimilarRecommendation.vue'
import { getPointBalance } from '@/domains/point/api/pointApi'
import { dispatchPointBalanceUpdated } from '@/domains/point/utils/pointBalanceEvents'
import LiveTryOnPanel from '@/domains/tryon/components/LiveTryOnPanel.vue'
import type { LiveWatchProduct } from '@/domains/live/types/liveWatch.types'
import type {
  ProductAiModelCutStatus,
  ProductDetailViewData,
} from '@/domains/product/types/productDetail.types'
import { normalizeApiError } from '@/shared/api/http'
import { ROUTE_NAMES } from '@/shared/constants/routes'
import DefaultLayout from '@/shared/layouts/DefaultLayout.vue'

type ProductDetailLoadState = 'loading' | 'success' | 'error' | 'not-found'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const wishStore = useWishStore()

const product = ref<ProductDetailViewData | null>(null)
const loadState = ref<ProductDetailLoadState>('loading')
const selectedImageId = ref('')
const isTryOnOpen = ref(false)
const isTryOnExpanded = ref(false)
const actionMessage = ref('')
let actionMessageTimer: ReturnType<typeof setTimeout> | undefined
let loadRequestId = 0

const aiModelCutStatus = ref<ProductAiModelCutStatus>('NONE')
const aiModelCutImageUrl = ref<string | null>(null)
let aiModelCutPollToken = 0
// 워커가 job마다 VLM/FLUX/CatVTON을 순차로 새로 로드하는 구조라(6GB급 GPU 전제) 완료까지
// 4분 넘게 걸릴 수 있다(-517 로컬 테스트에서 확인) — ProductRegistrationPage.vue와 동일한 값.
const AI_MODEL_CUT_POLL_INTERVAL_MS = 5_000
const AI_MODEL_CUT_POLL_TIMEOUT_MS = 600_000

const isPurchaseDialogOpen = ref(false)
const purchasePointBalance = ref<number | null>(null)
const isPurchaseBalanceLoading = ref(false)
const isPurchaseSubmitting = ref(false)
const purchaseErrorMessage = ref('')
const purchaseSuccessOrderId = ref<number | null>(null)
const purchaseInitialAddress = ref<OrderAddressInput | null>(null)

const isSold = computed(() => product.value?.saleStatus === 'SOLD')
const isLiked = computed(() =>
  product.value ? wishStore.isProductWished(product.value.id, product.value.isLiked) : false,
)

// 상품 상세 상품을 AI 시착 패널(LiveTryOnPanel)이 받는 형태로 어댑트.
// LiveTryOnPanel(TRYON-004)은 mock 생성 흐름을 유지한 채 재사용한다.
const tryOnProduct = computed<LiveWatchProduct | null>(() => {
  if (!product.value) return null

  const detail = product.value

  return {
    id: detail.id,
    title: detail.title,
    brandName: detail.brand,
    price: detail.price,
    thumbnailUrl: detail.images[0]?.url ?? null,
    saleType: detail.saleType === 'AUCTION' ? 'AUCTION' : 'DIRECT_SALE',
    saleStatus: null,
    material: detail.material,
    condition: detail.conditionLabel,
    measurements: detail.sizeLabel,
    defectSummary: null,
  }
})

// 갤러리 썸네일 맨 끝에 AI 착용컷 완성 이미지를 추가로 보여준다(생성 전/실패 시엔 상품
// 실사진만 노출 — 맨 아래 상태 섹션에서 진행 상태를 따로 안내한다).
const galleryImages = computed(() => {
  if (!product.value) return []

  if (aiModelCutStatus.value !== 'COMPLETED' || !aiModelCutImageUrl.value) {
    return product.value.images
  }

  return [
    ...product.value.images,
    {
      id: 'ai-model-cut',
      url: aiModelCutImageUrl.value,
      alt: `${product.value.title} AI 모델 시착 이미지`,
      label: 'AI 시착',
    },
  ]
})

const sleep = (ms: number) => new Promise<void>((resolve) => window.setTimeout(resolve, ms))

// 등록 시 켠 AI 착용컷의 생성 상태를 상품 상세 마지막에 보여준다. 아직 안 끝났으면
// ProductRegistrationPage.vue의 완료 화면과 동일한 폴링 패턴으로 완료·실패까지 반복
// 조회한다. 실패해도 상품 상세 자체는 이미 정상 표시된 상태라 조용히 멈춘다(보조 기능).
const pollAiModelCutStatus = async (productId: number) => {
  const token = ++aiModelCutPollToken
  const deadline = Date.now() + AI_MODEL_CUT_POLL_TIMEOUT_MS

  while (Date.now() < deadline) {
    if (token !== aiModelCutPollToken) return

    try {
      const result = await getProductAiModelCutStatus(productId)
      if (token !== aiModelCutPollToken) return

      aiModelCutStatus.value = result.status
      aiModelCutImageUrl.value = result.imageUrl

      if (result.status === 'COMPLETED' || result.status === 'FAILED' || result.status === 'NONE') {
        return
      }
    } catch {
      // 일시적 오류일 수 있다 — 다음 폴링에서 재시도, 화면 상태는 건드리지 않는다.
    }

    await sleep(AI_MODEL_CUT_POLL_INTERVAL_MS)
  }
}

const loadProductDetail = async () => {
  const productId = Number(route.params.productId)
  const requestId = ++loadRequestId

  product.value = null
  loadState.value = 'loading'
  actionMessage.value = ''
  purchaseSuccessOrderId.value = null
  clearTimeout(actionMessageTimer)
  aiModelCutPollToken += 1
  aiModelCutStatus.value = 'NONE'
  aiModelCutImageUrl.value = null

  if (!Number.isInteger(productId) || productId < 1) {
    loadState.value = 'not-found'
    return
  }

  try {
    await authStore.validateStoredSession()

    if (requestId !== loadRequestId) return

    const nextProduct = await getProductDetailViewData(productId)

    if (requestId !== loadRequestId) return

    product.value = nextProduct
    wishStore.hydrateProducts([{ id: nextProduct.id, isLiked: nextProduct.isLiked }])
    loadState.value = 'success'
    selectedImageId.value = nextProduct.images[0]?.id ?? ''

    if (nextProduct.aiModelCut) {
      aiModelCutStatus.value = nextProduct.aiModelCut.status
      aiModelCutImageUrl.value = nextProduct.aiModelCut.imageUrl

      if (
        nextProduct.aiModelCut.status === 'PENDING' ||
        nextProduct.aiModelCut.status === 'PROCESSING'
      ) {
        void pollAiModelCutStatus(nextProduct.id)
      }
    }
  } catch (error) {
    if (requestId !== loadRequestId) return

    loadState.value = error instanceof ProductDetailNotFoundError ? 'not-found' : 'error'
  }
}

const handleToggleLike = async () => {
  if (!product.value) {
    return
  }

  if (!authStore.isAuthenticated || !authStore.user?.id) {
    await router.push({ name: ROUTE_NAMES.AUTH_LOGIN })
    return
  }

  const wasLiked = wishStore.isProductWished(product.value.id, product.value.isLiked)
  wishStore.setProductWish(product.value.id, !wasLiked)

  try {
    if (wasLiked) {
      await removeWish(authStore.user.id, product.value.id)
    } else {
      await addWish(authStore.user.id, product.value.id)
    }
  } catch {
    wishStore.setProductWish(product.value.id, wasLiked)
    showTemporaryMessage('찜 상태를 변경하지 못했습니다. 잠시 후 다시 시도해 주세요.')
  }
}

const showTemporaryMessage = (message: string) => {
  clearTimeout(actionMessageTimer)
  actionMessage.value = message
  actionMessageTimer = setTimeout(() => {
    actionMessage.value = ''
  }, 2400)
}

const handleTryOn = () => {
  // 상품 가상 시착(TRYON-003): 등록 상품 이미지를 회원 전신 사진에 합성.
  // BE 시착 생성/전신 사진 조회 API가 미구현이라 패널은 mock으로 동작한다.
  //   → 요청: docs/requests/BE/007-live-tryon-contract.md (3.4 시착 프로필 / 3.6 상품 시착 생성)
  if (!product.value) return

  isTryOnExpanded.value = false
  isTryOnOpen.value = true
}

const closeTryOn = () => {
  isTryOnOpen.value = false
  isTryOnExpanded.value = false
}

const toggleTryOnExpanded = () => {
  isTryOnExpanded.value = !isTryOnExpanded.value
}

const handleTryOnKeydown = (event: KeyboardEvent) => {
  if (event.key === 'Escape') closeTryOn()
}

const handlePurchase = async () => {
  if (!product.value) return

  if (!authStore.isAuthenticated || !authStore.user) {
    await router.push({ name: ROUTE_NAMES.AUTH_LOGIN, query: { redirect: route.fullPath } })
    return
  }

  purchaseErrorMessage.value = ''
  purchaseSuccessOrderId.value = null
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

const handlePurchaseSubmit = async (address: OrderAddressInput) => {
  if (!product.value || !authStore.user) return

  const userId = authStore.user.id
  isPurchaseSubmitting.value = true
  purchaseErrorMessage.value = ''

  try {
    const order = await createOrder(product.value.id)

    clearTimeout(actionMessageTimer)
    product.value.saleStatus = 'SOLD'
    isPurchaseDialogOpen.value = false
    purchaseSuccessOrderId.value = order.orderId

    try {
      await updateOrderAddress(order.orderId, address)
      actionMessage.value = '구매가 완료되었습니다.'
    } catch {
      // 주문 자체는 이미 생성됐으므로 상품은 판매완료로 반영하고, 배송지는 구매 내역에서 재입력하도록 안내한다.
      actionMessage.value =
        '구매는 완료됐지만 배송지 등록에 실패했습니다. 구매 내역에서 다시 입력해 주세요.'
    }

    const nextBalance = await getPointBalance(userId).catch(() => null)
    if (nextBalance) {
      dispatchPointBalanceUpdated({ userId, balance: nextBalance })
    }
  } catch (error) {
    purchaseErrorMessage.value = normalizeApiError(error).message
  } finally {
    isPurchaseSubmitting.value = false
  }
}

const handleViewSeller = () => {
  if (!product.value) return

  void router.push({
    name: ROUTE_NAMES.PROFILE,
    params: { userId: product.value.seller.id },
  })
}

const handleViewSimilarProduct = (productId: number) => {
  void router.push({ name: ROUTE_NAMES.PRODUCT_DETAIL, params: { productId } })
}

const handleViewLive = (liveId: number) => {
  void router.push({ name: ROUTE_NAMES.LIVE_WATCH, params: { liveId } })
}

// 경매 진행 중 상품의 '라이브에서 입찰하기' — 연결된 라이브가 진행 중일 때만 입장한다.
const handleGoToLiveAuction = () => {
  const linkedLive = product.value?.linkedLive
  if (linkedLive?.status === 'LIVE') {
    handleViewLive(linkedLive.id)
  }
}

const handleGoToProductList = () => {
  void router.push({ name: ROUTE_NAMES.PRODUCT_LIST })
}

const goBack = () => {
  if (window.history.length > 1) {
    router.back()
    return
  }

  void router.push({ name: ROUTE_NAMES.PRODUCT_LIST })
}

watch(
  () => route.params.productId,
  () => {
    void loadProductDetail()
  },
  { immediate: true },
)

watch(isTryOnOpen, (open) => {
  if (open) {
    window.addEventListener('keydown', handleTryOnKeydown)
  } else {
    window.removeEventListener('keydown', handleTryOnKeydown)
  }
})

onBeforeUnmount(() => {
  loadRequestId += 1
  aiModelCutPollToken += 1
  clearTimeout(actionMessageTimer)
  window.removeEventListener('keydown', handleTryOnKeydown)
})
</script>

<template>
  <DefaultLayout>
    <button class="product-detail__back" type="button" @click="goBack">
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="m15 18-6-6 6-6" />
      </svg>
      뒤로가기
    </button>

    <ProductDetailSkeleton v-if="loadState === 'loading'" />

    <ProductDetailStatePanel
      v-else-if="loadState === 'error'"
      variant="error"
      title="상품 정보를 불러오지 못했습니다"
      description="네트워크 상태를 확인한 후 다시 시도해 주세요. 문제가 계속되면 잠시 후 다시 방문해 주세요."
      primary-label="다시 시도"
      secondary-label="상품 목록"
      @primary="loadProductDetail"
      @secondary="handleGoToProductList"
    />

    <ProductDetailStatePanel
      v-else-if="loadState === 'not-found'"
      variant="not-found"
      title="상품을 찾을 수 없습니다"
      description="삭제되었거나 공개되지 않은 상품입니다. 상품 목록에서 다른 빈티지 상품을 확인해 보세요."
      primary-label="상품 목록으로"
      @primary="handleGoToProductList"
    />

    <article v-else-if="product" class="product-detail">
      <section v-if="isSold" class="product-detail__sold-banner" role="status">
        <div aria-hidden="true">
          <svg viewBox="0 0 24 24">
            <path d="m7 12 3 3 7-7" />
            <circle cx="12" cy="12" r="9" />
          </svg>
        </div>
        <div>
          <strong>판매가 완료된 상품입니다</strong>
          <p>상품 정보는 계속 확인할 수 있지만 구매 기능은 이용할 수 없습니다.</p>
        </div>
      </section>

      <div class="product-detail__hero">
        <ProductImageGallery
          :images="galleryImages"
          :selected-image-id="selectedImageId"
          @select-image="selectedImageId = $event"
        />
        <ProductPurchaseSummary
          :product="product"
          :seller="product.seller"
          :is-liked="isLiked"
          @toggle-like="handleToggleLike"
          @open-try-on="handleTryOn"
          @purchase="handlePurchase"
          @go-live="handleGoToLiveAuction"
          @view-seller="handleViewSeller"
        />
      </div>

      <ProductPriceEstimateCard :estimate="product.priceEstimate" />

      <ProductPriceDistribution
        :current-product-id="product.id"
        :current-price="product.saleType === 'AUCTION' ? null : product.price"
        :products="product.similarProducts"
        @view-product="handleViewSimilarProduct"
      />

      <p v-if="actionMessage" class="product-detail__action-message" role="status">
        {{ actionMessage }}
        <RouterLink
          v-if="purchaseSuccessOrderId"
          :to="{ name: ROUTE_NAMES.MY_ORDER_DETAIL, params: { orderId: purchaseSuccessOrderId } }"
        >
          구매 내역 보기
        </RouterLink>
      </p>

      <ProductSellerLivePanel
        :linked-live="product.linkedLive"
        :seller-nickname="product.seller.nickname"
        @view-live="handleViewLive"
      />
      <ProductDetailInformation :product="product" />
      <AiQualityAnalysisPanel
        v-if="product.aiQualityAnalysis"
        :analysis="product.aiQualityAnalysis"
      />
      <ProductSimilarRecommendation
        :product-id="product.id"
        :category-id="product.categoryId"
        :brand="product.brand"
      />

      <section
        v-if="aiModelCutStatus !== 'NONE'"
        class="product-detail__ai-model-cut"
        aria-label="AI 모델 시착 이미지"
      >
        <h2 class="product-detail__ai-model-cut-title">AI 모델 시착</h2>

        <div class="product-detail__ai-model-cut-status" role="status">
          <template v-if="aiModelCutStatus === 'PENDING' || aiModelCutStatus === 'PROCESSING'">
            <span class="product-detail__ai-model-cut-spinner" aria-hidden="true"></span>
            <p>생성중입니다. 완료되면 여기에 표시됩니다.</p>
          </template>
          <template v-else-if="aiModelCutStatus === 'COMPLETED' && aiModelCutImageUrl">
            <img
              :src="aiModelCutImageUrl"
              alt="AI 모델 시착 이미지"
              class="product-detail__ai-model-cut-image"
            />
          </template>
          <template v-else-if="aiModelCutStatus === 'FAILED'">
            <p>AI 모델 시착 이미지 생성에 실패했습니다.</p>
          </template>
        </div>
      </section>
    </article>

    <div
      v-if="product && isTryOnOpen && tryOnProduct"
      class="product-try-on-popup"
      :class="{ 'product-try-on-popup--expanded': isTryOnExpanded }"
      role="dialog"
      aria-label="AI 가상 시착"
    >
      <div class="product-try-on-popup__frame">
        <button
          type="button"
          class="product-try-on-popup__expand"
          :aria-label="
            isTryOnExpanded ? 'AI 시착 팝업 작게 보기' : 'AI 시착 팝업 전체 화면으로 보기'
          "
          @click="toggleTryOnExpanded"
        >
          <svg v-if="!isTryOnExpanded" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M4 9V4h5M4 4l6 6M20 15v5h-5M20 20l-6-6" />
          </svg>
          <svg v-else viewBox="0 0 24 24" aria-hidden="true">
            <path d="M10 4v5H5M10 9 4 3M14 20v-5h5M14 15l6 6" />
          </svg>
        </button>
        <LiveTryOnPanel :product="tryOnProduct" @close="closeTryOn" />
      </div>
    </div>

    <PurchaseConfirmDialog
      v-if="product && isPurchaseDialogOpen"
      :product-title="product.title"
      :product-price="product.price"
      :product-thumbnail-url="product.images[0]?.url ?? ''"
      :point-balance="purchasePointBalance"
      :is-balance-loading="isPurchaseBalanceLoading"
      :is-submitting="isPurchaseSubmitting"
      :error-message="purchaseErrorMessage"
      :initial-address="purchaseInitialAddress"
      @close="closePurchaseDialog"
      @submit="handlePurchaseSubmit"
    />
  </DefaultLayout>
</template>

<style scoped lang="scss">
.product-detail__back {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: var(--button-height-small);
  margin-bottom: var(--space-4);
  padding: 0 var(--space-3) 0 var(--space-2);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-snug);
  transition:
    border-color var(--transition-base),
    color var(--transition-base);
}

.product-detail__back:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.product-detail__back svg {
  width: var(--icon-size-sm);
  height: var(--icon-size-sm);
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.8;
}

.product-detail__back:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

.product-detail__hero {
  display: grid;
  grid-template-columns: minmax(0, 1.08fr) minmax(390px, 0.92fr);
  align-items: start;
  gap: var(--space-12);
}

.product-detail__action-message {
  margin-top: var(--space-6);
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-control);
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-snug);
}

.product-detail__action-message a {
  margin-left: var(--space-2);
  color: inherit;
  text-decoration: underline;
}

.product-detail__sold-banner {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  margin-bottom: var(--space-8);
  padding: var(--space-4) var(--space-5);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-control);
  background: var(--color-surface-secondary);
}

.product-detail__sold-banner > div:first-child {
  display: grid;
  flex: 0 0 auto;
  width: var(--button-height-sm);
  height: var(--button-height-sm);
  border-radius: 50%;
  background: var(--color-surface);
  color: var(--color-text-secondary);
  place-items: center;
}

.product-detail__sold-banner svg {
  width: 22px;
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.8;
}

.product-detail__sold-banner strong {
  font-size: var(--font-size-body);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-body);
}

.product-detail__sold-banner p {
  margin-top: 2px;
  color: var(--color-text-secondary);
  font-size: var(--font-size-caption);
  line-height: var(--line-height-snug);
}

@media (max-width: 940px) {
  .product-detail__hero {
    grid-template-columns: 1fr;
  }
}

.product-detail__ai-model-cut {
  margin-top: var(--space-8);
}

.product-detail__ai-model-cut-title {
  margin-bottom: var(--space-4);
  font-size: var(--font-size-md-plus);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-snug);
}

.product-detail__ai-model-cut-status {
  display: grid;
  justify-items: center;
  gap: var(--space-3);
  width: 100%;
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
}

.product-detail__ai-model-cut-status p {
  max-width: var(--prose-max-width);
  color: var(--color-text-secondary);
  line-height: var(--line-height-body);
}

.product-detail__ai-model-cut-spinner {
  width: 28px;
  height: 28px;
  border: 3px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: product-detail-ai-model-cut-spin 0.8s linear infinite;
}

@keyframes product-detail-ai-model-cut-spin {
  to {
    transform: rotate(360deg);
  }
}

.product-detail__ai-model-cut-image {
  max-width: 320px;
  border-radius: var(--radius-control);
  object-fit: cover;
}

/* AI 시착 팝업 — 기본은 우하단 고정 floating(스크롤해도 보이고 뒤 페이지 조작 가능),
   확대 버튼을 누르면 전체 화면 중앙 모달로 커진다. 닫기는 패널의 X 버튼(@close). */
.product-try-on-popup {
  position: fixed;
  right: var(--space-6);
  bottom: var(--space-6);
  z-index: 120;
}

.product-try-on-popup__frame {
  position: relative;
  width: min(380px, calc(100vw - 24px));
  height: min(72vh, 640px);
  overflow: hidden;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-control);
}

.product-try-on-popup--expanded {
  display: grid;
  right: auto;
  bottom: auto;
  padding: var(--space-4);
  background: rgba(4, 6, 5, 0.62);
  inset: 0;
  place-items: center;
  backdrop-filter: blur(2px);
}

.product-try-on-popup--expanded .product-try-on-popup__frame {
  width: min(460px, 100%);
  height: min(88vh, 780px);
}

.product-try-on-popup__expand {
  display: grid;
  position: absolute;
  z-index: var(--z-layer-2);
  top: 14px;
  right: 52px;
  width: var(--badge-height-lg);
  height: var(--badge-height-lg);
  padding: 0;
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-radius: var(--radius-control);
  background: rgba(23, 27, 26, 0.92);
  color: rgba(255, 255, 255, 0.72);
  place-items: center;
}

.product-try-on-popup__expand:hover {
  border-color: var(--color-border-underline);
  color: var(--color-text-primary);
}

.product-try-on-popup__expand svg {
  width: var(--icon-size-xs);
  height: var(--icon-size-xs);
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.8;
}

@media (max-width: 720px) {
  .product-try-on-popup:not(.product-try-on-popup--expanded) {
    right: var(--space-3);
    bottom: var(--space-3);
  }

  .product-try-on-popup:not(.product-try-on-popup--expanded) .product-try-on-popup__frame {
    width: calc(100vw - 24px);
    height: min(70vh, 560px);
  }
}
</style>
