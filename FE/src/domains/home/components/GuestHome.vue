<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import HomeSearchPanel from '@/domains/home/components/HomeSearchPanel.vue'
import HomeSection from '@/domains/home/components/HomeSection.vue'
import LiveCard from '@/domains/home/components/LiveCard.vue'
import ProductCard from '@/domains/home/components/ProductCard.vue'
import type { HomeViewData } from '@/domains/home/types/homeView.types'
import { ROUTE_PATHS } from '@/shared/constants/routes'

const props = defineProps<{
  homeData: HomeViewData
}>()

const guestContentCards = computed(() =>
  props.homeData.contentCards.filter(
    (card) => card.audience === 'guest' || card.audience === 'all',
  ),
)

const getProductPath = (productId: number) => `/products/${productId}`
</script>

<template>
  <div class="guest-home">
    <HomeSearchPanel />

    <section class="home-hero" aria-labelledby="guest-home-title">
      <img
        class="home-hero__image"
        src="https://images.unsplash.com/photo-1496747611176-843222e1e57c?auto=format&fit=crop&w=1400&q=80"
        alt=""
      />
      <div class="home-hero__content">
        <p class="home-hero__eyebrow">Vintage live auction</p>
        <h1 id="guest-home-title" class="home-hero__title">
          라이브로 확인하고 경매로 만나는
          <span class="home-hero__nowrap">빈티지 쇼핑</span>
        </h1>
        <p class="home-hero__description">지금 진행 중인 라이브와 상시 판매 상품을 둘러보세요.</p>
        <div class="home-hero__actions">
          <RouterLink class="home-hero__primary" :to="ROUTE_PATHS.LIVE_LIST"
            >라이브 둘러보기</RouterLink
          >
          <RouterLink class="home-hero__secondary" :to="ROUTE_PATHS.AUTH_LOGIN">로그인</RouterLink>
        </div>
      </div>
    </section>

    <HomeSection
      title-id="live-now-title"
      eyebrow="Live now"
      title="지금 진행 중인 라이브"
      :link-to="ROUTE_PATHS.LIVE_LIST"
      :is-empty="homeData.liveNow.length === 0"
      empty-message="지금 진행 중인 라이브가 없습니다."
    >
      <div class="live-grid">
        <LiveCard v-for="live in homeData.liveNow" :key="live.id" :live="live" />
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
        />
      </div>
    </HomeSection>

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
          badge-label="경매 예정"
          badge-variant="auction"
          price-prefix="가격 "
          :action-to="ROUTE_PATHS.AUTH_LOGIN"
          action-label="경매 알림 받기"
        />
      </div>
    </HomeSection>

    <section class="content-band" aria-label="홈 콘텐츠">
      <RouterLink
        v-for="content in guestContentCards"
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
.guest-home {
  display: grid;
  justify-items: stretch;
  gap: var(--space-12);
  padding-bottom: var(--space-16);
}

.home-hero,
.content-band {
  width: 100%;
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

.home-hero {
  position: relative;
  min-height: 300px;
  overflow: hidden;
  border-radius: var(--radius-media);
  background: var(--color-live-background);
}

.home-hero::after {
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, rgba(14, 17, 16, 0.86), rgba(14, 17, 16, 0.32));
  content: '';
}

.home-hero__image {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.home-hero__content {
  position: relative;
  z-index: 1;
  display: grid;
  max-width: 780px;
  gap: var(--space-4);
  padding: var(--space-10);
}

.home-hero__eyebrow {
  color: var(--color-primary);
  font-size: 13px;
  font-weight: 800;
  line-height: 20px;
}

.home-hero__eyebrow {
  color: var(--color-text-inverse);
}

.home-hero__title {
  color: var(--color-text-inverse);
  font-size: 34px;
  font-weight: 800;
  line-height: 44px;
}

.home-hero__nowrap {
  white-space: nowrap;
}

.home-hero__description {
  color: var(--color-live-text-secondary);
  font-size: 16px;
  line-height: 26px;
}

.home-hero__actions {
  display: flex;
  gap: var(--space-3);
  flex-wrap: wrap;
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

.content-card:hover {
  border-color: #ded8ce;
  box-shadow: 0 10px 26px rgb(18 18 18 / 7%);
  transform: translateY(-2px);
}

.content-card__image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.content-card__shade {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(14, 17, 16, 0.18), rgba(14, 17, 16, 0.82));
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
  .guest-home {
    gap: var(--space-10);
  }

  .home-hero {
    min-height: 260px;
  }

  .home-hero__content {
    padding: var(--space-6);
  }

  .home-hero__title {
    font-size: 28px;
    line-height: 38px;
  }

  .home-hero__description {
    font-size: 15px;
    line-height: 24px;
  }

  .live-grid,
  .schedule-grid,
  .product-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 520px) {
  .home-hero__content {
    padding: var(--space-5);
  }

  .live-grid,
  .schedule-grid,
  .product-grid {
    grid-template-columns: 1fr 1fr;
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
