<script setup lang="ts">
import { RouterLink } from 'vue-router'

import CategoryProductTabs from '@/domains/home/components/CategoryProductTabs.vue'
import HomeHero from '@/domains/home/components/HomeHero.vue'
import HomeSearchPanel from '@/domains/home/components/HomeSearchPanel.vue'
import HomeSection from '@/domains/home/components/HomeSection.vue'
import LiveCard from '@/domains/home/components/LiveCard.vue'
import ProductCard from '@/domains/home/components/ProductCard.vue'
import type { HomeLiveStatus, HomeViewData } from '@/domains/home/types/homeView.types'
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

const formatSchedule = (value?: string) => {
  if (!value) {
    return '일정 확인'
  }

  return new Intl.DateTimeFormat('ko-KR', {
    month: 'long',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  }).format(new Date(value))
}

const getLivePath = (liveId: number) => `/lives/${liveId}`
const getProductPath = (productId: number) => `/products/${productId}`
const getSellerLivePath = (liveId?: number) =>
  liveId ? getLivePath(liveId) : ROUTE_PATHS.LIVE_LIST
const getSellerLiveActionQuery = (status?: HomeLiveStatus) =>
  status === 'SCHEDULED' ? { action: 'notify' } : undefined
const getSellerLiveActionLabel = (status?: HomeLiveStatus) =>
  status === 'LIVE' ? '라이브 보기' : '방송 알림 받기'
</script>

<template>
  <div class="member-home">
    <HomeSearchPanel />

    <HomeHero
      title-id="member-home-title"
      eyebrow="For you"
      title="팔로우한 셀러와 취향 상품을 모아봤어요"
      description="관심 셀러의 라이브와 새 상품, 최근 둘러본 취향에 맞는 빈티지 아이템을 바로 확인하세요."
      image-url="https://images.unsplash.com/photo-1483985988355-763728e1935b?auto=format&fit=crop&w=1400&q=80"
    >
      <template #actions>
        <RouterLink class="member-hero__primary" :to="ROUTE_PATHS.FOLLOWING_HOME"
          >팔로잉 보기</RouterLink
        >
        <RouterLink class="member-hero__secondary" :to="ROUTE_PATHS.PRODUCT_LIST"
          >상품 둘러보기</RouterLink
        >
      </template>
    </HomeHero>

    <HomeSection
      title-id="followed-seller-title"
      eyebrow="Following"
      title="내가 팔로우한 판매자"
      :link-to="ROUTE_PATHS.FOLLOWING_HOME"
      :is-empty="homeData.followedSellers.length === 0"
      empty-message="팔로우한 판매자가 없습니다."
    >
      <div class="seller-grid">
        <article v-for="seller in homeData.followedSellers" :key="seller.id" class="seller-card">
          <span class="seller-card__cover">
            <img class="seller-card__cover-image" :src="seller.coverImageUrl" :alt="seller.name" />
            <span
              v-if="seller.liveStatus"
              class="seller-card__status"
              :class="{ 'seller-card__status--live': seller.liveStatus === 'LIVE' }"
            >
              {{ seller.liveStatus === 'LIVE' ? 'LIVE' : formatSchedule(seller.liveAt) }}
            </span>
          </span>
          <span class="seller-card__body">
            <span class="seller-card__profile">
              <img class="seller-card__avatar" :src="seller.profileImageUrl" :alt="seller.name" />
              <span class="seller-card__identity">
                <strong class="seller-card__name">{{ seller.name }}</strong>
              </span>
            </span>
            <span class="seller-card__stats">
              <span>팔로워 {{ formatCompactNumber(seller.followerCount) }}</span>
              <span>판매 상품 {{ seller.newProductCount }}개</span>
            </span>
            <strong class="seller-card__live-title">{{ seller.liveTitle }}</strong>
            <span class="seller-card__time">{{ formatSchedule(seller.liveAt) }}</span>
            <RouterLink
              class="seller-card__action"
              :to="{
                path: getSellerLivePath(seller.liveId),
                query: getSellerLiveActionQuery(seller.liveStatus),
              }"
            >
              {{ getSellerLiveActionLabel(seller.liveStatus) }}
            </RouterLink>
          </span>
        </article>
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
          action-label="방송 알림 받기"
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
  gap: var(--space-12);
  padding-bottom: var(--space-16);
}

.member-hero__primary,
.member-hero__secondary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 48px;
  padding: 0 var(--space-4);
  border-radius: 14px;
  font-weight: 800;
  line-height: 20px;
  white-space: nowrap;
}

.member-hero__primary {
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

.member-hero__secondary {
  border: 1px solid rgba(255, 255, 255, 0.42);
  background: rgba(255, 255, 255, 0.1);
  color: var(--color-text-inverse);
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
  border: 1px solid #e6e1d8;
  border-radius: 20px;
  background: var(--color-surface);
  box-shadow: 0 8px 24px rgb(18 18 18 / 5%);
  transition:
    border-color 160ms ease,
    box-shadow 160ms ease,
    transform 160ms ease;
}

.seller-card:hover {
  border-color: #ded8ce;
  box-shadow: 0 10px 26px rgb(18 18 18 / 7%);
  transform: translateY(-2px);
}

.seller-card {
  display: grid;
}

.seller-card__cover {
  position: relative;
  display: block;
  overflow: hidden;
  background: var(--color-surface-secondary);
}

.seller-card__cover {
  aspect-ratio: 16 / 9;
}

.seller-card__cover::after {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(14, 17, 16, 0.02), rgba(14, 17, 16, 0.42));
  content: '';
}

.seller-card__cover-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.seller-card__status {
  position: absolute;
  z-index: 1;
  top: var(--space-3);
  left: var(--space-3);
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  max-width: calc(100% - var(--space-6));
  padding: 0 10px;
  overflow: hidden;
  border-radius: var(--space-2);
  background: rgba(14, 17, 16, 0.72);
  color: var(--color-text-inverse);
  font-size: 12px;
  font-weight: 700;
  line-height: 18px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.seller-card__status--live {
  background: var(--color-live);
}

.seller-card__body {
  display: grid;
  gap: var(--space-2);
  padding: var(--space-5);
}

.seller-card__profile {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.seller-card__avatar {
  width: 42px;
  height: 42px;
  border: 2px solid var(--color-surface);
  border-radius: 50%;
  object-fit: cover;
}

.seller-card__identity {
  display: grid;
  min-width: 0;
  gap: 2px;
}

.seller-card__name,
.seller-card__live-title {
  color: var(--color-text-primary);
  display: -webkit-box;
  overflow: hidden;
  font-size: 18px;
  font-weight: 700;
  line-height: 26px;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.seller-card__name {
  display: block;
  font-size: 18px;
  font-weight: 600;
  line-height: 24px;
}

.seller-card__stats {
  color: var(--color-text-muted);
  font-size: 13px;
  font-weight: 400;
  line-height: 20px;
}

.seller-card__time {
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: 500;
  line-height: 20px;
}

.seller-card__stats {
  display: flex;
  gap: var(--space-3);
  flex-wrap: wrap;
}

.seller-card__action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: fit-content;
  height: 40px;
  padding: 0 var(--space-4);
  border-radius: 12px;
  justify-self: end;
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-size: 14px;
  font-weight: 600;
  line-height: 20px;
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
