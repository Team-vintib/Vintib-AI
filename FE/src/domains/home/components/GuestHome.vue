<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import { homeMockData } from '@/domains/home/constants/homeMockData'
import { ROUTE_PATHS } from '@/shared/constants/routes'

const guestContentCards = computed(() =>
  homeMockData.contentCards.filter((card) => card.audience === 'guest' || card.audience === 'all'),
)

const formatPrice = (value?: number) => {
  if (value === undefined) {
    return '가격 확인'
  }

  return `${value.toLocaleString('ko-KR')}원`
}

const formatSchedule = (value?: string) => {
  if (!value) {
    return '일정 확인'
  }

  return new Intl.DateTimeFormat('ko-KR', {
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

const getLivePath = (liveId: number) => `/lives/${liveId}`
const getProductPath = (productId: number) => `/products/${productId}`
</script>

<template>
  <div class="guest-home">
    <section class="home-search-panel" aria-label="홈 검색">
      <form class="home-search" role="search" @submit.prevent>
        <input class="home-search__input" type="search" placeholder="브랜드, 상품, 라이브 검색" />
        <RouterLink class="home-search__button" :to="ROUTE_PATHS.SEARCH">검색</RouterLink>
      </form>
    </section>

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
          <RouterLink class="home-hero__primary" :to="ROUTE_PATHS.LIVE_LIST">라이브 둘러보기</RouterLink>
          <RouterLink class="home-hero__secondary" :to="ROUTE_PATHS.AUTH_LOGIN">로그인</RouterLink>
        </div>
      </div>
    </section>

    <section class="home-section" aria-labelledby="live-now-title">
      <div class="home-section__header">
        <div>
          <p class="home-section__eyebrow">Live now</p>
          <h2 id="live-now-title" class="home-section__title">지금 진행 중인 라이브</h2>
        </div>
        <RouterLink class="home-section__link" :to="ROUTE_PATHS.LIVE_LIST">전체보기</RouterLink>
      </div>

      <div class="live-grid">
        <article
          v-for="live in homeMockData.liveNow"
          :key="live.id"
          class="live-card"
        >
          <span class="live-card__media">
            <img class="live-card__image" :src="live.thumbnailUrl" :alt="live.title" />
            <span class="live-card__badge">LIVE</span>
          </span>
          <span class="live-card__body">
            <strong class="live-card__title">{{ live.title }}</strong>
            <span class="live-card__meta">판매자 {{ live.hostName }}</span>
            <span class="live-card__meta">시작 시간 {{ formatSchedule(live.startedAt) }}</span>
          </span>
        </article>
      </div>
    </section>

    <section class="home-section" aria-labelledby="scheduled-live-title">
      <div class="home-section__header">
        <div>
          <p class="home-section__eyebrow">Upcoming</p>
          <h2 id="scheduled-live-title" class="home-section__title">예약 라이브</h2>
        </div>
        <RouterLink class="home-section__link" :to="ROUTE_PATHS.LIVE_LIST">전체보기</RouterLink>
      </div>

      <div class="schedule-grid">
        <article
          v-for="live in homeMockData.scheduledLives"
          :key="live.id"
          class="schedule-card"
        >
          <span class="schedule-card__media">
            <img class="schedule-card__image" :src="live.thumbnailUrl" :alt="live.title" />
            <RouterLink class="schedule-card__action schedule-card__action--media" :to="ROUTE_PATHS.AUTH_LOGIN">
              알림받기
            </RouterLink>
          </span>
          <span class="schedule-card__body">
            <strong class="schedule-card__title">{{ live.title }}</strong>
            <span class="schedule-card__meta">판매자 {{ live.hostName }}</span>
            <span class="schedule-card__meta">예정 일자 {{ formatSchedule(live.scheduledAt) }}</span>
            <span class="schedule-card__meta">예정 상품 {{ live.scheduledProductCount ?? 0 }}개</span>
          </span>
        </article>
      </div>
    </section>

    <section class="home-section" aria-labelledby="product-title">
      <div class="home-section__header">
        <div>
          <p class="home-section__eyebrow">Products</p>
          <h2 id="product-title" class="home-section__title">판매 상품</h2>
        </div>
        <RouterLink class="home-section__link" :to="ROUTE_PATHS.PRODUCT_LIST">전체보기</RouterLink>
      </div>

      <div class="product-grid">
        <RouterLink
          v-for="product in homeMockData.directSaleProducts"
          :key="product.id"
          class="product-card"
          :to="getProductPath(product.id)"
        >
          <span class="product-card__media">
            <img class="product-card__image" :src="product.primaryImageUrl" :alt="product.title" />
          </span>
          <span class="product-card__body">
            <span class="product-card__brand">{{ product.brandName }}</span>
            <span class="product-card__seller">판매자 {{ product.sellerName }}</span>
            <strong class="product-card__title">{{ product.title }}</strong>
            <span class="product-card__price-text">{{ formatPrice(product.price) }}</span>
            <span class="product-card__meta">{{ product.categoryName }}</span>
          </span>
        </RouterLink>
      </div>
    </section>

    <section class="home-section" aria-labelledby="auction-title">
      <div class="home-section__header">
        <div>
          <p class="home-section__eyebrow">Auction</p>
          <h2 id="auction-title" class="home-section__title">경매 예정 상품</h2>
        </div>
        <RouterLink class="home-section__link" :to="ROUTE_PATHS.PRODUCT_LIST">전체보기</RouterLink>
      </div>

      <div class="product-grid product-grid--auction">
        <article
          v-for="product in homeMockData.upcomingAuctionProducts"
          :key="product.id"
          class="product-card"
        >
          <span class="product-card__media">
            <img class="product-card__image" :src="product.primaryImageUrl" :alt="product.title" />
            <RouterLink class="product-card__action product-card__action--media" :to="ROUTE_PATHS.AUTH_LOGIN">
              알림받기
            </RouterLink>
          </span>
          <span class="product-card__body">
            <span class="product-card__brand">{{ product.brandName }}</span>
            <span class="product-card__seller">판매자 {{ product.sellerName }}</span>
            <strong class="product-card__title">{{ product.title }}</strong>
            <span class="product-card__price-text">가격 {{ formatPrice(product.price) }}</span>
            <span class="product-card__meta">{{ product.categoryName }}</span>
            <span class="product-card__bid">경매 시작가 {{ formatPrice(product.startingBid) }}</span>
          </span>
        </article>
      </div>
    </section>

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
  --home-content-max-width: 1200px;

  display: grid;
  justify-items: center;
  gap: var(--space-12);
  width: 100%;
  padding-bottom: var(--space-16);
}

.home-search-panel,
.home-hero,
.home-section,
.content-band {
  width: 100%;
  max-width: var(--home-content-max-width);
  margin-inline: auto;
}

.home-search-panel {
  display: flex;
  justify-content: center;
  padding-top: var(--space-5);
}

.home-search {
  display: flex;
  width: min(100%, 720px);
  min-height: 50px;
  padding: var(--space-1);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  box-shadow: 0 8px 22px rgba(23, 24, 21, 0.06);
}

.home-search__input {
  min-width: 0;
  border: 0;
  flex: 1;
  padding: 0 var(--space-4);
  background: transparent;
  color: var(--color-text-primary);
  outline: none;
}

.home-search__button,
.home-hero__primary,
.home-hero__secondary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 42px;
  padding: 0 var(--space-5);
  border-radius: var(--radius-control);
  font-weight: 700;
  white-space: nowrap;
}

.home-search__button,
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

.home-hero__eyebrow,
.home-section__eyebrow {
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

.home-section {
  display: grid;
  gap: var(--space-5);
}

.home-section__header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--space-4);
}

.home-section__title {
  margin-top: var(--space-1);
  color: var(--color-text-primary);
  font-size: 24px;
  font-weight: 800;
  line-height: 34px;
}

.home-section__link {
  color: var(--color-primary);
  font-size: 14px;
  font-weight: 800;
}

.live-grid,
.schedule-grid,
.product-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-5);
}

.live-card,
.schedule-card,
.product-card,
.content-card {
  position: relative;
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
  transition:
    border-color 160ms ease,
    box-shadow 160ms ease,
    transform 160ms ease;
}

.live-card:hover,
.schedule-card:hover,
.product-card:hover,
.content-card:hover {
  border-color: var(--color-border-strong);
  box-shadow: 0 10px 24px rgba(23, 24, 21, 0.08);
  transform: translateY(-2px);
}

.live-card,
.schedule-card {
  display: grid;
}

.live-card__media,
.schedule-card__media,
.product-card__media {
  position: relative;
  display: block;
  overflow: hidden;
  background: var(--color-surface-secondary);
}

.live-card__media,
.schedule-card__media {
  aspect-ratio: 16 / 9;
}

.product-card__media {
  aspect-ratio: 4 / 5;
}

.live-card__image,
.schedule-card__image,
.product-card__image,
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

.live-card__badge {
  position: absolute;
  z-index: 1;
}

.live-card__badge {
  top: var(--space-3);
  left: var(--space-3);
}

.live-card__body,
.schedule-card__body {
  display: grid;
  gap: var(--space-1);
  padding: var(--space-3);
  background: var(--color-surface);
}

.live-card__badge {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 var(--space-2);
  border-radius: var(--radius-badge);
  background: var(--color-live);
  color: var(--color-text-inverse);
  font-size: 12px;
  font-weight: 800;
  line-height: 18px;
}

.schedule-card__time,
.product-card__tag,
.product-card__time {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 var(--space-2);
  border-radius: var(--radius-badge);
  font-size: 12px;
  font-weight: 800;
  line-height: 18px;
}

.schedule-card__time,
.product-card__time {
  background: rgba(14, 17, 16, 0.66);
  color: var(--color-text-inverse);
}

.live-card__category {
  color: var(--color-live-text-secondary);
  font-size: 12px;
  font-weight: 700;
}

.live-card__title,
.schedule-card__title,
.product-card__title {
  color: var(--color-text-primary);
  font-size: 17px;
  font-weight: 800;
  line-height: 24px;
}

.live-card__host,
.live-card__meta,
.schedule-card__meta,
.product-card__meta,
.product-card__seller {
  color: var(--color-text-muted);
  font-size: 13px;
  font-weight: 600;
  line-height: 20px;
}

.live-card__action,
.schedule-card__action,
.product-card__action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: fit-content;
  min-height: 36px;
  padding: 0 var(--space-4);
  border-radius: var(--radius-control);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-size: 14px;
  font-weight: 800;
  line-height: 21px;
}

.live-card__action {
  background: var(--color-live);
}

.schedule-card__time {
  top: var(--space-3);
  left: var(--space-3);
}

.product-card {
  display: grid;
}

.product-card__media::after {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(14, 17, 16, 0.04), rgba(14, 17, 16, 0.5));
  content: '';
}

.product-card__tag,
.product-card__time,
.product-card__price {
  position: absolute;
  z-index: 1;
}

.product-card__tag {
  top: var(--space-2);
  left: var(--space-2);
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

.product-card__tag--auction {
  background: var(--color-auction);
}

.product-card__time {
  top: var(--space-2);
  right: var(--space-2);
}

.product-card__price {
  right: var(--space-2);
  bottom: var(--space-2);
  left: var(--space-2);
  color: var(--color-text-inverse);
  font-size: 15px;
  font-weight: 800;
  line-height: 22px;
}

.product-card__body {
  display: grid;
  gap: var(--space-1);
  padding: var(--space-3);
}

.product-card__brand {
  color: var(--color-primary);
  font-size: 13px;
  font-weight: 800;
  line-height: 20px;
}

.product-card__price-text,
.product-card__bid {
  color: var(--color-text-primary);
  font-size: 14px;
  font-weight: 800;
  line-height: 21px;
}

.product-card__bid {
  color: var(--color-auction);
}

.schedule-card__action--media,
.product-card__action--media {
  position: absolute;
  z-index: 1;
  right: var(--space-2);
  bottom: var(--space-2);
  background: var(--color-primary);
  box-shadow: 0 6px 16px rgba(14, 17, 16, 0.22);
}

.content-band {
  display: grid;
}

.content-card {
  min-height: 220px;
}

.content-card__body {
  position: absolute;
  z-index: 1;
  right: var(--space-8);
  bottom: var(--space-8);
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

  .home-section__header {
    align-items: flex-start;
  }

  .home-section__title {
    font-size: 22px;
    line-height: 31px;
  }

  .live-grid,
  .schedule-grid,
  .product-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 520px) {
  .home-search {
    display: grid;
    gap: var(--space-2);
    padding: var(--space-2);
  }

  .home-search__input {
    min-height: 42px;
  }

  .home-search__button {
    width: 100%;
  }

  .home-hero__content {
    padding: var(--space-5);
  }

  .live-grid,
  .schedule-grid,
  .product-grid {
    grid-template-columns: 1fr 1fr;
    gap: var(--space-3);
  }

  .live-card__title,
  .schedule-card__title,
  .product-card__title {
    font-size: 15px;
    line-height: 22px;
  }

  .product-card__time {
    display: none;
  }

  .content-card__body {
    right: var(--space-5);
    bottom: var(--space-5);
    left: var(--space-5);
  }
}
</style>
