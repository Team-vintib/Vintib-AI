<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import { getProductDetailViewData } from '@/domains/product/api/productDetailApi'
import AiQualityAnalysisPanel from '@/domains/product/components/AiQualityAnalysisPanel.vue'
import ProductDetailInformation from '@/domains/product/components/ProductDetailInformation.vue'
import ProductImageGallery from '@/domains/product/components/ProductImageGallery.vue'
import ProductPurchaseSummary from '@/domains/product/components/ProductPurchaseSummary.vue'
import ProductSellerLivePanel from '@/domains/product/components/ProductSellerLivePanel.vue'
import type { ProductDetailViewData } from '@/domains/product/types/productDetail.types'
import DefaultLayout from '@/shared/layouts/DefaultLayout.vue'

const route = useRoute()

const product = ref<ProductDetailViewData | null>(null)
const errorMessage = ref('')

const loadProductDetail = async () => {
  const productId = Number(route.params.productId)

  if (!Number.isInteger(productId) || productId < 1) {
    errorMessage.value = '올바른 상품 번호가 아닙니다.'
    return
  }

  try {
    product.value = await getProductDetailViewData(productId)
  } catch {
    errorMessage.value = '상품 정보를 불러오지 못했습니다.'
  }
}

onMounted(() => {
  void loadProductDetail()
})
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
        <ProductImageGallery :images="product.images" />
        <ProductPurchaseSummary :product="product" :seller="product.seller" />
      </div>

      <ProductSellerLivePanel :linked-live="product.linkedLive" />
      <ProductDetailInformation :product="product" />
      <AiQualityAnalysisPanel :analysis="product.aiQualityAnalysis" />
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

@media (max-width: 940px) {
  .product-detail__hero {
    grid-template-columns: 1fr;
  }
}
</style>
