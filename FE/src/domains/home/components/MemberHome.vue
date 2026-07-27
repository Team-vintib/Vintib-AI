<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import HomeSearchPanel from '@/domains/home/components/HomeSearchPanel.vue'
import HomeSection from '@/domains/home/components/HomeSection.vue'
import LiveCard from '@/domains/home/components/LiveCard.vue'
import ProductCard from '@/domains/home/components/ProductCard.vue'
import { homeMockData } from '@/domains/home/constants/homeMockData'
import type { HomeLiveStatus } from '@/domains/home/types/homeView.types'
import { ROUTE_PATHS } from '@/shared/constants/routes'

const memberContentCards = computed(() =>
  homeMockData.contentCards.filter((card) => card.audience === 'member' || card.audience === 'all'),
)

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

    <section class="member-hero" aria-labelledby="member-home-title">
      <img
        class="member-hero__image"
        src="https://images.unsplash.com/photo-1483985988355-763728e1935b?auto=format&fit=crop&w=1400&q=80"
        alt=""
      />
      <div class="member-hero__content">
        <p class="member-hero__eyebrow">For you</p>
        <h1 id="member-home-title" class="member-hero__title">
          팔로우한 셀러와 취향 상품을 모아봤어요
        </h1>
        <p class="member-hero__description">
          관심 셀러의 라이브와 새 상품, 최근 둘러본 취향에 맞는 빈티지 아이템을 바로 확인하세요.
        </p>
        <div class="member-hero__actions">
          <RouterLink class="member-hero__primary" :to="ROUTE_PATHS.FOLLOWING_HOME"
            >팔로잉 보기</RouterLink
          >
          <RouterLink class="member-hero__secondary" :to="ROUTE_PATHS.PRODUCT_LIST"
            >상품 둘러보기</RouterLink
          >
        </div>
      </div>
    </section>

    <HomeSection
      title-id="followed-seller-title"
      eyebrow="Following"
      title="내가 팔로우한 판매자"
      :link-to="ROUTE_PATHS.FOLLOWING_HOME"
    >
      <div class="seller-grid">
        <article
          v-for="seller in homeMockData.followedSellers"
          :key="seller.id"
          class="seller-card"
        >
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
                <span class="seller-card__specialty">{{ seller.specialty }}</span>
              </span>
            </span>
            <span class="seller-card__stats">
              <span>팔로워 {{ formatCompactNumber(seller.followerCount) }}</span>
              <span>새 상품 {{ seller.newProductCount }}개</span>
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
    >
      <div class="live-grid">
        <LiveCard
          v-for="live in homeMockData.liveNow"
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
    >
      <div class="schedule-grid">
        <LiveCard
          v-for="live in homeMockData.scheduledLives"
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
      title="내 취향의 빈티지 상품"
      :link-to="ROUTE_PATHS.PRODUCT_LIST"
    >
      <div class="product-grid">
        <ProductCard
          v-for="product in homeMockData.recommendedProducts"
          :key="product.id"
          :product="product"
          :to="getProductPath(product.id)"
          :badge-label="product.saleType === 'AUCTION' ? '경매 예정' : '바로 구매'"
          :badge-variant="product.saleType === 'AUCTION' ? 'auction' : 'direct'"
        />
      </div>
    </HomeSection>

    <HomeSection
      title-id="auction-title"
      eyebrow="Auction"
      title="경매 예정 상품"
      :link-to="ROUTE_PATHS.PRODUCT_LIST"
    >
      <div class="product-grid">
        <ProductCard
          v-for="product in homeMockData.upcomingAuctionProducts"
          :key="product.id"
          :product="product"
          :to="getProductPath(product.id)"
          badge-label="경매 예정"
          badge-variant="auction"
          price-prefix="가격 "
        />
      </div>
    </HomeSection>

    <section class="content-band" aria-label="회원 홈 콘텐츠">
      <RouterLink
        v-for="content in memberContentCards"
        :key="content.id"
        class="content-card"
        :to="content.targetPath"
      >
        <img class="content-card__image" :src="content.imageUrl" :alt="content.title" />
        <span class="content-card__shade" />
        <span class="content-card__body">
          <strong class="content-card__title">{{ content.title }}</strong>
          <span class="content-card__description">{{ content.description }}</span>
          <span class="content-card__cta">{{ content.ctaLabel }}</span>
        </span>
      </RouterLink>
    </section>
  </div>
</template>

<style scoped lang="scss">
.member-home {
  display: grid;
  justify-items: stretch;
  gap: var(--space-12);
  padding-bottom: var(--space-16);
}

.member-hero,
.content-band {
  width: 100%;
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

.member-hero {
  position: relative;
  min-height: 300px;
  overflow: hidden;
  border-radius: var(--radius-media);
  background: var(--color-live-background);
}

.member-hero::after {
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, rgba(14, 17, 16, 0.86), rgba(14, 17, 16, 0.28));
  content: '';
}

.member-hero__image {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.member-hero__content {
  position: relative;
  z-index: 1;
  display: grid;
  max-width: 760px;
  gap: var(--space-4);
  padding: var(--space-10);
}

.member-hero__eyebrow {
  color: var(--color-primary);
  font-size: 13px;
  font-weight: 800;
  line-height: 20px;
}

.member-hero__eyebrow {
  color: var(--color-text-inverse);
}

.member-hero__title {
  color: var(--color-text-inverse);
  font-size: 34px;
  font-weight: 800;
  line-height: 44px;
}

.member-hero__description {
  color: var(--color-live-text-secondary);
  font-size: 16px;
  line-height: 26px;
}

.member-hero__actions {
  display: flex;
  gap: var(--space-3);
  flex-wrap: wrap;
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

.seller-card,
.content-card {
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

.seller-card:hover,
.content-card:hover {
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

.seller-card__cover-image,
.content-card__image {
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

.seller-card__specialty,
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

.seller-card__specialty {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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

.content-band {
  display: grid;
}

.content-card {
  height: 150px;
  min-height: 0;
}

.content-card__image {
  position: absolute;
  inset: 0;
}

.content-card__shade {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(14, 17, 16, 0.18), rgba(14, 17, 16, 0.82));
}

.content-card__body {
  position: absolute;
  z-index: 1;
  right: var(--space-8);
  bottom: var(--space-5);
  left: var(--space-8);
  display: grid;
  max-width: 520px;
  gap: var(--space-2);
}

.content-card__title {
  color: var(--color-text-inverse);
  font-size: 24px;
  font-weight: 800;
  line-height: 34px;
}

.content-card__description {
  color: var(--color-live-text-secondary);
}

.content-card__cta {
  color: var(--color-text-inverse);
  font-weight: 800;
}

@media (max-width: 768px) {
  .member-home {
    gap: var(--space-10);
  }

  .member-hero {
    min-height: 260px;
  }

  .member-hero__content {
    padding: var(--space-6);
  }

  .member-hero__title {
    font-size: 28px;
    line-height: 38px;
  }

  .member-hero__description {
    font-size: 15px;
    line-height: 24px;
  }

  .seller-grid,
  .live-grid,
  .schedule-grid,
  .product-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 520px) {
  .member-hero__content {
    padding: var(--space-5);
  }

  .seller-grid,
  .live-grid,
  .schedule-grid,
  .product-grid {
    grid-template-columns: 1fr;
    gap: var(--space-3);
  }

  .content-card__body {
    right: var(--space-4);
    bottom: var(--space-4);
    left: var(--space-4);
  }

  .content-card {
    height: 132px;
  }
}
</style>
