<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { getProductDetailViewData } from '@/domains/product/api/productDetailApi'
import AiQualityAnalysisPanel from '@/domains/product/components/AiQualityAnalysisPanel.vue'
import ProductDetailInformation from '@/domains/product/components/ProductDetailInformation.vue'
import ProductImageGallery from '@/domains/product/components/ProductImageGallery.vue'
import ProductPurchaseSummary from '@/domains/product/components/ProductPurchaseSummary.vue'
import ProductSellerLivePanel from '@/domains/product/components/ProductSellerLivePanel.vue'
import type { ProductDetailViewData } from '@/domains/product/types/productDetail.types'
import { ROUTE_NAMES } from '@/shared/constants/routes'
import DefaultLayout from '@/shared/layouts/DefaultLayout.vue'

const route = useRoute()
const router = useRouter()

const product = ref<ProductDetailViewData | null>(null)
const errorMessage = ref('')
const selectedImageId = ref('')
const isLiked = ref(false)
const isInCart = ref(false)
const isReminderSet = ref(false)
const actionMessage = ref('')
let actionMessageTimer: ReturnType<typeof setTimeout> | undefined

const selectedImage = computed(() =>
  product.value?.images.find((image) => image.id === selectedImageId.value),
)

const loadProductDetail = async () => {
  const productId = Number(route.params.productId)

  product.value = null
  errorMessage.value = ''
  actionMessage.value = ''
  clearTimeout(actionMessageTimer)

  if (!Number.isInteger(productId) || productId < 1) {
    errorMessage.value = '올바른 상품 번호가 아닙니다.'
    return
  }

  try {
    product.value = await getProductDetailViewData(productId)
    selectedImageId.value = product.value.images[0]?.id ?? ''
    isLiked.value = product.value.isLiked
    isInCart.value = false
    isReminderSet.value = false
  } catch {
    errorMessage.value = '상품 정보를 불러오지 못했습니다.'
  }
}

const handleToggleLike = () => {
  isLiked.value = !isLiked.value
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

const handleToggleReminder = () => {
  isReminderSet.value = !isReminderSet.value
}

const handleViewLive = (liveId: number) => {
  void router.push({ name: ROUTE_NAMES.LIVE_WATCH, params: { liveId } })
}

watch(
  () => route.params.productId,
  () => {
    void loadProductDetail()
  },
  { immediate: true },
)
</script>

<template>
  <DefaultLayout>
    <section v-if="errorMessage" class="product-detail__message" role="alert">
      <h1>{{ errorMessage }}</h1>
    </section>

    <section v-else-if="!product" class="product-detail__message" aria-live="polite">
      <p>상품 정보를 불러오는 중입니다.</p>
    </section>

    <article v-else class="product-detail">
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

.product-detail__message {
  display: grid;
  min-height: 420px;
  align-content: center;
  justify-items: center;
  gap: var(--space-4);
  color: var(--color-text-secondary);
  text-align: center;
}

.product-detail__message h1 {
  color: var(--color-text-primary);
  font-size: 26px;
  font-weight: 700;
  line-height: 36px;
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

@media (max-width: 940px) {
  .product-detail__hero {
    grid-template-columns: 1fr;
  }
}
</style>
