<script setup lang="ts">
import { RouterLink } from 'vue-router'

import CategoryProductTabs from '@/domains/home/components/CategoryProductTabs.vue'
import HomeHero from '@/domains/home/components/HomeHero.vue'
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

    <HomeHero
      title-id="guest-home-title"
      eyebrow="Vintage live auction"
      title="라이브로 확인하고 경매로 만나는"
      nowrap-suffix="빈티지 쇼핑"
      description="지금 진행 중인 라이브와 상시 판매 상품을 둘러보세요."
      image-url="https://images.unsplash.com/photo-1496747611176-843222e1e57c?auto=format&fit=crop&w=1400&q=80"
    >
      <template #actions>
        <RouterLink class="home-hero__primary" :to="ROUTE_PATHS.LIVE_LIST"
          >라이브 둘러보기</RouterLink
        >
        <RouterLink class="home-hero__secondary" :to="ROUTE_PATHS.AUTH_LOGIN">로그인</RouterLink>
      </template>
    </HomeHero>

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
          action-label="방송 알림 받기"
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
  gap: var(--space-12);
  padding-bottom: var(--space-16);
}

.home-hero__primary,
.home-hero__secondary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 48px;
  padding: 0 var(--space-4);
  border-radius: 14px;
  font-weight: 700;
  line-height: 20px;
  white-space: nowrap;
}

.home-hero__primary {
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

.home-hero__secondary {
  border: 1px solid rgba(255, 255, 255, 0.42);
  background: rgba(255, 255, 255, 0.1);
  color: var(--color-text-inverse);
}

.live-grid,
.schedule-grid,
.product-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
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
