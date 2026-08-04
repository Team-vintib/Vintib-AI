<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '@/domains/auth/stores/authStore'
import { addWish, removeWish } from '@/domains/product/api/productApi'
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
import ProductPurchaseSummary from '@/domains/product/components/ProductPurchaseSummary.vue'
import ProductSellerLivePanel from '@/domains/product/components/ProductSellerLivePanel.vue'
import LiveTryOnPanel from '@/domains/tryon/components/LiveTryOnPanel.vue'
import type { LiveWatchProduct } from '@/domains/live/types/liveWatch.types'
import type { ProductDetailViewData } from '@/domains/product/types/productDetail.types'
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
const isInCart = ref(false)
const isReminderSet = ref(false)
const isTryOnOpen = ref(false)
const isTryOnExpanded = ref(false)
const actionMessage = ref('')
let actionMessageTimer: ReturnType<typeof setTimeout> | undefined
let loadRequestId = 0

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
    material: detail.material,
    condition: detail.conditionLabel,
    measurements: detail.sizeLabel,
    defectSummary: null,
  }
})

const loadProductDetail = async () => {
  const productId = Number(route.params.productId)
  const requestId = ++loadRequestId

  product.value = null
  loadState.value = 'loading'
  actionMessage.value = ''
  clearTimeout(actionMessageTimer)

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
    isInCart.value = false
    isReminderSet.value = false
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

const handleToggleCart = () => {
  isInCart.value = !isInCart.value
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

const handlePurchase = () =>
  showTemporaryMessage('구매 확인 화면은 후속 스토리에서 연결됩니다.')

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

const handleToggleReminder = () => {
  isReminderSet.value = !isReminderSet.value
}

const handleViewLive = (liveId: number) => {
  void router.push({ name: ROUTE_NAMES.LIVE_WATCH, params: { liveId } })
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
          <p>상품 정보는 계속 확인할 수 있지만 구매와 장바구니 기능은 이용할 수 없습니다.</p>
        </div>
      </section>

      <div class="product-detail__hero">
        <ProductImageGallery
          :images="product.images"
          :selected-image-id="selectedImageId"
          @select-image="selectedImageId = $event"
        />
        <ProductPurchaseSummary
          :product="product"
          :seller="product.seller"
          :is-liked="isLiked"
          :is-in-cart="isInCart"
          @toggle-like="handleToggleLike"
          @toggle-cart="handleToggleCart"
          @open-try-on="handleTryOn"
          @purchase="handlePurchase"
          @view-seller="handleViewSeller"
        />
      </div>

      <ProductPriceDistribution
        :current-product-id="product.id"
        :current-price="product.price"
        :products="product.similarProducts"
        @view-product="handleViewSimilarProduct"
      />

      <p v-if="actionMessage" class="product-detail__action-message" role="status">
        {{ actionMessage }}
      </p>

      <ProductSellerLivePanel
        :linked-live="product.linkedLive"
        :seller-nickname="product.seller.nickname"
        :is-reminder-set="isReminderSet"
        @toggle-reminder="handleToggleReminder"
        @view-live="handleViewLive"
      />
      <ProductDetailInformation :product="product" />
      <AiQualityAnalysisPanel :analysis="product.aiQualityAnalysis" />
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
          :aria-label="isTryOnExpanded ? 'AI 시착 팝업 작게 보기' : 'AI 시착 팝업 전체 화면으로 보기'"
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
  </DefaultLayout>
</template>

<style scoped lang="scss">
.product-detail__back {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 36px;
  margin-bottom: var(--space-4);
  padding: 0 var(--space-3) 0 var(--space-2);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: 600;
  line-height: 18px;
  transition:
    border-color 160ms ease,
    color 160ms ease;
}

.product-detail__back:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.product-detail__back svg {
  width: 18px;
  height: 18px;
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
  font-size: 13px;
  font-weight: 600;
  line-height: 18px;
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
  width: 40px;
  height: 40px;
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
  font-size: 15px;
  font-weight: 700;
  line-height: 24px;
}

.product-detail__sold-banner p {
  margin-top: 2px;
  color: var(--color-text-secondary);
  font-size: 13px;
  line-height: 18px;
}

@media (max-width: 940px) {
  .product-detail__hero {
    grid-template-columns: 1fr;
  }
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
  z-index: 2;
  top: 14px;
  right: 52px;
  width: 30px;
  height: 30px;
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
  width: 15px;
  height: 15px;
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
