<script setup lang="ts">
import CategoryProductTabs from '@/domains/home/components/CategoryProductTabs.vue'
import HomeHeroCarousel from '@/domains/home/components/HomeHeroCarousel.vue'
import HomeSearchPanel from '@/domains/home/components/HomeSearchPanel.vue'
import HomeSection from '@/domains/home/components/HomeSection.vue'
import LiveCard from '@/domains/home/components/LiveCard.vue'
import ProductCard from '@/domains/home/components/ProductCard.vue'
import type { HomeViewData } from '@/domains/home/types/homeView.types'
import { ROUTE_PATHS } from '@/shared/constants/routes'

defineProps<{
  homeData: HomeViewData
  wishedProductIds: Set<number>
}>()

const emit = defineEmits<{
  toggleWish: [productId: number]
}>()

const getLivePath = (liveId: number) => `/lives/${liveId}`
const getProductPath = (productId: number) => `/products/${productId}`
</script>

<template>
  <div class="guest-home">
    <HomeSearchPanel />

    <HomeHeroCarousel :home-data="homeData" />

    <HomeSection
      title-id="live-now-title"
      eyebrow="Live now"
      title="지금 진행 중인 라이브"
      :link-to="ROUTE_PATHS.LIVE_LIST"
      :is-empty="homeData.liveNow.length === 0"
      empty-message="지금 진행 중인 라이브가 없습니다."
    >
      <div class="live-grid">
        <LiveCard
          v-for="live in homeData.liveNow"
          :key="live.id"
          :live="live"
          :to="getLivePath(live.id)"
        />
      </div>
    </HomeSection>

    <HomeSection
      title-id="scheduled-live-title"
      eyebrow="Upcoming"
      title="예약 라이브"
      :link-to="ROUTE_PATHS.LIVE_LIST"
      :is-empty="homeData.scheduledLives.length === 0"
      empty-message="예약된 라이브가 없습니다."
    >
      <div class="schedule-grid">
        <LiveCard
          v-for="live in homeData.scheduledLives"
          :key="live.id"
          :live="live"
          variant="scheduled"
          :action-to="ROUTE_PATHS.AUTH_LOGIN"
          action-label="예약하기"
        />
      </div>
    </HomeSection>

    <HomeSection
      title-id="product-title"
      eyebrow="Products"
      title="판매 상품"
      :link-to="ROUTE_PATHS.PRODUCT_LIST"
      :is-empty="homeData.directSaleProducts.length === 0"
      empty-message="판매 중인 상품이 없습니다."
    >
      <div class="product-grid">
        <ProductCard
          v-for="product in homeData.directSaleProducts"
          :key="product.id"
          :product="product"
          :to="getProductPath(product.id)"
          :is-wished="wishedProductIds.has(product.id)"
          @toggle-wish="emit('toggleWish', $event)"
        />
      </div>
    </HomeSection>

    <CategoryProductTabs
      :sections="homeData.categoryProductSections"
      :wished-product-ids="wishedProductIds"
      @toggle-wish="emit('toggleWish', $event)"
    />

    <HomeSection
      title-id="auction-title"
      eyebrow="Auction"
      title="경매 예정 상품"
      :link-to="ROUTE_PATHS.PRODUCT_LIST"
      :is-empty="homeData.upcomingAuctionProducts.length === 0"
      empty-message="경매 예정 상품이 없습니다."
    >
      <div class="product-grid product-grid--auction">
        <ProductCard
          v-for="product in homeData.upcomingAuctionProducts"
          :key="product.id"
          :product="product"
          :to="getProductPath(product.id)"
          badge-label="경매 예정"
          badge-variant="auction"
          price-prefix="가격 "
          :action-to="ROUTE_PATHS.AUTH_LOGIN"
          action-label="경매 알림 받기"
          :is-wished="wishedProductIds.has(product.id)"
          @toggle-wish="emit('toggleWish', $event)"
        />
      </div>
    </HomeSection>

  </div>
</template>

<style scoped lang="scss">
.guest-home {
  display: grid;
  justify-items: stretch;
  gap: var(--space-16);
  padding-bottom: var(--space-16);
}

.live-grid,
.schedule-grid,
.product-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space-5);
}

@media (max-width: 768px) {
  .guest-home {
    gap: var(--space-10);
  }

  .live-grid,
  .schedule-grid,
  .product-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 520px) {
  .live-grid,
  .schedule-grid,
  .product-grid {
    grid-template-columns: 1fr 1fr;
    gap: var(--space-3);
  }

}
</style>
