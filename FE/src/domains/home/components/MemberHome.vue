<script setup lang="ts">
import { RouterLink } from 'vue-router'

import CategoryProductTabs from '@/domains/home/components/CategoryProductTabs.vue'
import HomeHeroCarousel from '@/domains/home/components/HomeHeroCarousel.vue'
import HomeSearchPanel from '@/domains/home/components/HomeSearchPanel.vue'
import HomeSection from '@/domains/home/components/HomeSection.vue'
import LiveCard from '@/domains/home/components/LiveCard.vue'
import ProductCard from '@/domains/home/components/ProductCard.vue'
import type { HomePopularHostLive, HomeViewData } from '@/domains/home/types/homeView.types'
import type { ProductCategoryTabSection } from '@/domains/product/types/productList.types'
import { ROUTE_PATHS } from '@/shared/constants/routes'

defineProps<{
  homeData: HomeViewData
  wishedProductIds: Set<number>
  productGradeLabels: Map<number, string>
  popularHostLive: HomePopularHostLive | null
  categoryProductTabs: ProductCategoryTabSection[]
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

// 아바타 로드에 실패하면 대체 이미지를 새로 추가하는 대신 빈 원형 프레임만 남긴다.
const handleAvatarError = (event: Event) => {
  if (event.target instanceof HTMLImageElement) {
    event.target.style.visibility = 'hidden'
  }
}
</script>

<template>
  <div class="member-home">
    <HomeSearchPanel />

    <HomeHeroCarousel :home-data="homeData" :popular-host-live="popularHostLive" />

    <HomeSection
      title-id="followed-seller-title"
      eyebrow="Following"
      title="팔로우 중인 판매자"
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
          <span class="seller-card__avatar">
            <img
              v-if="seller.profileImageUrl"
              :src="seller.profileImageUrl"
              :alt="seller.name"
              @error="handleAvatarError"
            />
          </span>
          <span class="seller-card__body">
            <strong class="seller-card__name">{{ seller.name }}</strong>
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
          :grade-label="productGradeLabels.get(product.id)"
          :is-wished="wishedProductIds.has(product.id)"
          @toggle-wish="emit('toggleWish', $event)"
        />
      </div>
    </HomeSection>

    <CategoryProductTabs
      :sections="categoryProductTabs"
      :wished-product-ids="wishedProductIds"
      @toggle-wish="emit('toggleWish', $event)"
    />

    <HomeSection
      title-id="auction-title"
      eyebrow="Auction"
      title="경매 예정 상품"
      :link-to="{ path: ROUTE_PATHS.PRODUCT_LIST, query: { saleType: 'AUCTION' } }"
      :is-empty="homeData.upcomingAuctionProducts.length === 0"
      empty-message="경매 예정 상품이 없습니다."
    >
      <div class="product-grid">
        <ProductCard
          v-for="product in homeData.upcomingAuctionProducts"
          :key="product.id"
          :product="product"
          :to="getProductPath(product.id)"
          :grade-label="productGradeLabels.get(product.id)"
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

.seller-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space-5);
}

.live-grid,
.schedule-grid,
.product-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space-5);
}

// 낮고 컴팩트한 카드: 얇은 border만, 채워진 배경 박스는 두지 않는다.
// hover도 뜨지 않고 보더 대비만 미세하게 바뀐다. 아바타는 왼쪽, 닉네임·통계는 오른쪽에 배치한다.
.seller-card {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  color: inherit;
  transition: border-color var(--transition-standard);
}

.seller-card:hover {
  border-color: var(--color-border-strong);
}

.seller-card__avatar {
  overflow: hidden;
  display: grid;
  flex: 0 0 auto;
  place-items: center;
  width: var(--space-16);
  height: var(--space-16);
  border: 1px solid var(--color-border);
  border-radius: 50%;
  background: var(--color-image-frame);
}

.seller-card__avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  filter: saturate(0.88) contrast(1.04) brightness(0.95);
}

.seller-card__body {
  display: grid;
  justify-items: start;
  min-width: 0;
  width: 100%;
  gap: var(--space-1);
}

.seller-card__name {
  color: var(--color-text-primary);
  overflow: hidden;
  max-width: 100%;
  font-size: var(--font-size-body);
  font-weight: var(--font-weight-medium);
  line-height: var(--line-height-comfortable);
  letter-spacing: -0.01em;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.seller-card__stats {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-start;
  gap: var(--space-1) var(--space-3);
  color: var(--color-text-muted);
  font-family: var(--font-mono);
  font-size: var(--font-size-2xs);
  font-weight: var(--font-weight-regular);
  letter-spacing: -0.01em;
  line-height: var(--line-height-snug);
  font-variant-numeric: tabular-nums;
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
