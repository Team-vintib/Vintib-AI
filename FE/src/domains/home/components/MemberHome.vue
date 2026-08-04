<script setup lang="ts">
import { RouterLink } from 'vue-router'

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

const formatCompactNumber = (value: number) => {
  return new Intl.NumberFormat('ko-KR', {
    notation: 'compact',
    maximumFractionDigits: 1,
  }).format(value)
}

const getLivePath = (liveId: number) => `/lives/${liveId}`
const getProductPath = (productId: number) => `/products/${productId}`
const getSellerProfilePath = (sellerId: number) => `/profile/${sellerId}`
</script>

<template>
  <div class="member-home">
    <HomeSearchPanel />

    <HomeHeroCarousel :home-data="homeData" />

    <HomeSection
      title-id="followed-seller-title"
      eyebrow="Following"
      title="내가 팔로우한 판매자"
      :link-to="ROUTE_PATHS.FOLLOWING_HOME"
      :is-empty="homeData.followedSellers.length === 0"
      empty-message="팔로우한 판매자가 없습니다."
    >
      <div class="seller-grid">
        <RouterLink
          v-for="seller in homeData.followedSellers"
          :key="seller.id"
          class="seller-card"
          :to="getSellerProfilePath(seller.id)"
          :aria-label="`${seller.name} 프로필 보기`"
        >
          <span class="seller-card__body">
            <span class="seller-card__profile">
              <span class="seller-card__identity">
                <strong class="seller-card__name">{{ seller.name }}</strong>
              </span>
            </span>
            <span class="seller-card__stats">
              <span>팔로워 {{ formatCompactNumber(seller.followerCount) }}</span>
              <span>팔로잉 {{ formatCompactNumber(seller.followingCount) }}</span>
              <span>판매 상품 {{ formatCompactNumber(seller.newProductCount) }}</span>
              <span>라이브 {{ formatCompactNumber(seller.liveCount) }}</span>
            </span>
          </span>
        </RouterLink>
      </div>
    </HomeSection>

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
          :action-to="getLivePath(live.id)"
          action-label="예약하기"
        />
      </div>
    </HomeSection>

    <HomeSection
      title-id="recommended-product-title"
      eyebrow="Taste pick"
      title="팔로우한 판매자의 상품"
      :link-to="ROUTE_PATHS.PRODUCT_LIST"
      :is-empty="homeData.recommendedProducts.length === 0"
      empty-message="추천할 상품이 없습니다."
    >
      <div class="product-grid">
        <ProductCard
          v-for="product in homeData.recommendedProducts"
          :key="product.id"
          :product="product"
          :to="getProductPath(product.id)"
          :badge-label="product.saleType === 'AUCTION' ? '경매 예정' : '바로 구매'"
          :badge-variant="product.saleType === 'AUCTION' ? 'auction' : 'direct'"
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
      <div class="product-grid">
        <ProductCard
          v-for="product in homeData.upcomingAuctionProducts"
          :key="product.id"
          :product="product"
          :to="getProductPath(product.id)"
          badge-label="경매 예정"
          badge-variant="auction"
          price-prefix="가격 "
          :is-wished="wishedProductIds.has(product.id)"
          @toggle-wish="emit('toggleWish', $event)"
        />
      </div>
    </HomeSection>
  </div>
</template>

<style scoped lang="scss">
.member-home {
  display: grid;
  justify-items: stretch;
  gap: var(--space-16);
  padding-bottom: var(--space-16);
}

.seller-grid,
.live-grid,
.schedule-grid,
.product-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-5);
}

.seller-card {
  position: relative;
  overflow: hidden;
  display: grid;
  min-height: 132px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
  color: inherit;
  transition:
    border-color 220ms ease,
    background-color 220ms ease,
    transform 620ms cubic-bezier(0.22, 1, 0.36, 1);
}

.seller-card:hover {
  border-color: var(--color-border-strong);
  transform: translateY(-3px);
}

.seller-card__body {
  display: grid;
  align-content: center;
  gap: var(--space-4);
  padding: var(--space-5);
}

.seller-card__profile {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.seller-card__identity {
  display: grid;
  min-width: 0;
  gap: 2px;
}

.seller-card__name {
  color: var(--color-text-primary);
  display: -webkit-box;
  overflow: hidden;
  font-size: 16px;
  font-weight: 500;
  line-height: 22px;
  letter-spacing: -0.01em;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.seller-card__stats {
  color: var(--color-text-muted);
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 400;
  letter-spacing: -0.01em;
  line-height: 18px;
  font-variant-numeric: tabular-nums;
}

.seller-card__stats {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2) var(--space-3);
}

@media (max-width: 768px) {
  .member-home {
    gap: var(--space-10);
  }

  .seller-grid,
  .live-grid,
  .schedule-grid,
  .product-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 520px) {
  .seller-grid,
  .live-grid,
  .schedule-grid,
  .product-grid {
    grid-template-columns: 1fr;
    gap: var(--space-3);
  }
}
</style>
