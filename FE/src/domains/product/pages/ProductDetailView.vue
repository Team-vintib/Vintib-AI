<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '@/domains/auth/stores/authStore'
import { addWish, removeWish } from '@/domains/product/api/productApi'
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
import type {
  ProductDetailMockScenario,
  ProductDetailViewData,
} from '@/domains/product/types/productDetail.types'
import { ROUTE_NAMES } from '@/shared/constants/routes'
import DefaultLayout from '@/shared/layouts/DefaultLayout.vue'

type ProductDetailLoadState = 'loading' | 'success' | 'error' | 'not-found'

const PRODUCT_DETAIL_MOCK_SCENARIOS: ProductDetailMockScenario[] = [
  'default',
  'loading',
  'error',
  'not-found',
  'sold',
  'ai-not-requested',
  'ai-analyzing',
  'ai-no-findings',
  'ai-failed',
]

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const product = ref<ProductDetailViewData | null>(null)
const loadState = ref<ProductDetailLoadState>('loading')
const selectedImageId = ref('')
const isLiked = ref(false)
const isInCart = ref(false)
const isReminderSet = ref(false)
const actionMessage = ref('')
let actionMessageTimer: ReturnType<typeof setTimeout> | undefined
let loadRequestId = 0

const selectedImage = computed(() =>
  product.value?.images.find((image) => image.id === selectedImageId.value),
)

const isSold = computed(() => product.value?.saleStatus === 'SOLD')

const getMockScenario = (): ProductDetailMockScenario => {
  const queryValue = Array.isArray(route.query.mock) ? route.query.mock[0] : route.query.mock

  return PRODUCT_DETAIL_MOCK_SCENARIOS.includes(queryValue as ProductDetailMockScenario)
    ? (queryValue as ProductDetailMockScenario)
    : 'default'
}

const loadProductDetail = async () => {
  const productId = Number(route.params.productId)
  const requestId = ++loadRequestId
  const scenario = getMockScenario()

  product.value = null
  loadState.value = 'loading'
  actionMessage.value = ''
  clearTimeout(actionMessageTimer)

  if (!Number.isInteger(productId) || productId < 1) {
    loadState.value = 'not-found'
    return
  }

  if (scenario === 'loading') return

  try {
    const nextProduct = await getProductDetailViewData(productId, scenario)

    if (requestId !== loadRequestId) return

    product.value = nextProduct
    loadState.value = 'success'
    selectedImageId.value = nextProduct.images[0]?.id ?? ''
    isLiked.value = nextProduct.isLiked
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

  const wasLiked = isLiked.value
  isLiked.value = !wasLiked

  try {
    if (wasLiked) {
      await removeWish(authStore.user.id, product.value.id)
    } else {
      await addWish(authStore.user.id, product.value.id)
    }
  } catch {
    isLiked.value = wasLiked
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

const handleTryOn = () => showTemporaryMessage('상품 AI 시착 화면은 준비 중입니다.')

const handlePurchase = () =>
  showTemporaryMessage('구매 확인 화면은 후속 스토리에서 연결됩니다.')

const handleViewSeller = () => showTemporaryMessage('판매자 프로필 화면은 준비 중입니다.')

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

watch(
  () => [route.params.productId, route.query.mock],
  () => {
    void loadProductDetail()
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  loadRequestId += 1
  clearTimeout(actionMessageTimer)
})
</script>

<template>
  <DefaultLayout>
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
        :is-reminder-set="isReminderSet"
        @toggle-reminder="handleToggleReminder"
        @view-live="handleViewLive"
      />
      <ProductDetailInformation :product="product" />
      <AiQualityAnalysisPanel
        :analysis="product.aiQualityAnalysis"
        :selected-image="selectedImage"
      />
    </article>
  </DefaultLayout>
</template>

<style scoped lang="scss">
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
</style>
