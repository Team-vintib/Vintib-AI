<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import { homeMockData } from '@/domains/home/constants/homeMockData'
import type { HomeLiveStatus } from '@/domains/home/types/homeView.types'
import { ROUTE_PATHS } from '@/shared/constants/routes'

const memberContentCards = computed(() =>
  homeMockData.contentCards.filter((card) => card.audience === 'member' || card.audience === 'all'),
)

const formatPrice = (value?: number) => {
  if (value === undefined) {
    return '가격 확인'
  }

  return `${value.toLocaleString('ko-KR')}원`
}

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
    <section class="home-search-panel" aria-label="홈 검색">
      <form class="home-search" role="search" @submit.prevent>
        <span class="home-search__icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path
              d="m20 20-4.2-4.2m2.2-5.3a7.5 7.5 0 1 1-15 0 7.5 7.5 0 0 1 15 0Z"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
          </svg>
        </span>
        <input
          class="home-search__input"
          type="search"
          placeholder="예: 리바이스 데님 자켓, Archive Room"
        />
        <RouterLink class="home-search__button" :to="ROUTE_PATHS.SEARCH">검색하기</RouterLink>
      </form>
      <div class="home-search-tags" aria-label="인기 검색어">
        <span class="home-search-tags__label">인기 검색어</span>
        <RouterLink class="home-search-tags__item" :to="ROUTE_PATHS.SEARCH">리바이스</RouterLink>
        <RouterLink class="home-search-tags__item" :to="ROUTE_PATHS.SEARCH">가죽 자켓</RouterLink>
        <RouterLink class="home-search-tags__item" :to="ROUTE_PATHS.SEARCH">라이브 경매</RouterLink>
        <RouterLink class="home-search-tags__item" :to="ROUTE_PATHS.SEARCH"
          >Archive Room</RouterLink
        >
      </div>
    </section>

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

    <section class="home-section" aria-labelledby="followed-seller-title">
      <div class="home-section__header">
        <div>
          <p class="home-section__eyebrow">Following</p>
          <h2 id="followed-seller-title" class="home-section__title">내가 팔로우한 판매자</h2>
        </div>
        <RouterLink class="home-section__link" :to="ROUTE_PATHS.FOLLOWING_HOME"
          >전체보기</RouterLink
        >
      </div>

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
        <RouterLink
          v-for="live in homeMockData.liveNow"
          :key="live.id"
          class="live-card"
          :to="getLivePath(live.id)"
        >
          <span class="live-card__media">
            <img class="live-card__image" :src="live.thumbnailUrl" :alt="live.title" />
            <span class="live-card__badge">LIVE</span>
          </span>
          <span class="live-card__body">
            <strong class="live-card__title">{{ live.title }}</strong>
            <span class="live-card__meta">판매자 {{ live.hostName }}</span>
            <span class="live-card__meta live-card__meta--time"
              >시작 시간 {{ formatSchedule(live.startedAt) }}</span
            >
          </span>
        </RouterLink>
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
        <article v-for="live in homeMockData.scheduledLives" :key="live.id" class="schedule-card">
          <span class="schedule-card__media">
            <img class="schedule-card__image" :src="live.thumbnailUrl" :alt="live.title" />
            <span class="schedule-card__time">{{ formatSchedule(live.scheduledAt) }}</span>
          </span>
          <span class="schedule-card__body">
            <strong class="schedule-card__title">{{ live.title }}</strong>
            <span class="schedule-card__meta">판매자 {{ live.hostName }}</span>
            <span class="schedule-card__meta schedule-card__meta--time"
              >예정 일자 {{ formatSchedule(live.scheduledAt) }}</span
            >
            <span class="schedule-card__meta"
              >예정 상품 {{ live.scheduledProductCount ?? 0 }}개</span
            >
            <RouterLink class="schedule-card__action" :to="getLivePath(live.id)">
              방송 알림 받기
            </RouterLink>
          </span>
        </article>
      </div>
    </section>

    <section class="home-section" aria-labelledby="recommended-product-title">
      <div class="home-section__header">
        <div>
          <p class="home-section__eyebrow">Taste pick</p>
          <h2 id="recommended-product-title" class="home-section__title">내 취향의 빈티지 상품</h2>
        </div>
        <RouterLink class="home-section__link" :to="ROUTE_PATHS.PRODUCT_LIST">전체보기</RouterLink>
      </div>

      <div class="product-grid">
        <RouterLink
          v-for="product in homeMockData.recommendedProducts"
          :key="product.id"
          class="product-card"
          :to="getProductPath(product.id)"
        >
          <span class="product-card__media">
            <img class="product-card__image" :src="product.primaryImageUrl" :alt="product.title" />
            <span
              class="product-card__tag"
              :class="{ 'product-card__tag--direct': product.saleType === 'DIRECT_SALE' }"
            >
              {{ product.saleType === 'AUCTION' ? '경매 예정' : '바로 구매' }}
            </span>
          </span>
          <span class="product-card__body">
            <span class="product-card__brand">{{ product.brandName }}</span>
            <span class="product-card__seller">판매자 {{ product.sellerName }}</span>
            <strong class="product-card__title">{{ product.title }}</strong>
            <span class="product-card__price">{{ formatPrice(product.price) }}</span>
            <span v-if="product.startingBid" class="product-card__bid">
              경매 시작가 {{ formatPrice(product.startingBid) }}
            </span>
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

      <div class="product-grid">
        <RouterLink
          v-for="product in homeMockData.upcomingAuctionProducts"
          :key="product.id"
          class="product-card"
          :to="getProductPath(product.id)"
        >
          <span class="product-card__media">
            <img class="product-card__image" :src="product.primaryImageUrl" :alt="product.title" />
            <span class="product-card__tag product-card__tag--auction">경매 예정</span>
          </span>
          <span class="product-card__body">
            <span class="product-card__brand">{{ product.brandName }}</span>
            <span class="product-card__seller">판매자 {{ product.sellerName }}</span>
            <strong class="product-card__title">{{ product.title }}</strong>
            <span class="product-card__price">가격 {{ formatPrice(product.price) }}</span>
            <span class="product-card__meta">{{ product.categoryName }}</span>
            <span class="product-card__bid"
              >경매 시작가 {{ formatPrice(product.startingBid) }}</span
            >
          </span>
        </RouterLink>
      </div>
    </section>

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
  --home-content-max-width: 1200px;

  display: grid;
  justify-items: stretch;
  gap: var(--space-12);
  width: min(100%, var(--home-content-max-width));
  margin-inline: auto;
  padding-bottom: var(--space-16);
}

.home-search-panel,
.member-hero,
.home-section,
.content-band {
  width: 100%;
}

.home-search-panel {
  display: grid;
  place-items: center;
  gap: var(--space-3);
  padding-top: var(--space-5);
}

.home-search {
  display: flex;
  align-items: center;
  width: min(100%, 860px);
  height: 58px;
  padding: 5px 5px 5px var(--space-5);
  border: 1px solid var(--color-search-border);
  border-radius: 16px;
  background: var(--color-surface);
  box-shadow: none;
  transition:
    border-color 160ms ease,
    box-shadow 160ms ease;
}

.home-search:focus-within {
  border-color: var(--color-search-button);
  box-shadow: 0 0 0 4px rgba(47, 75, 58, 0.08);
}

.home-search__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  flex: 0 0 auto;
  color: var(--color-search-icon);
}

.home-search__icon svg {
  width: 18px;
  height: 18px;
}

.home-search__input {
  height: 48px;
  min-width: 0;
  border: 0;
  flex: 1;
  padding: 0 var(--space-4);
  background: transparent;
  color: var(--color-text-primary);
  font-size: 15px;
  line-height: 48px;
  outline: none;
}

.home-search__input::placeholder {
  color: var(--color-text-muted);
}

.home-search__button,
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

.home-search__button {
  background: var(--color-search-button);
  color: var(--color-text-inverse);
}

.member-hero__primary {
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

.home-search__button:hover {
  background: var(--color-search-button-hover);
}

.home-search-tags {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  flex-wrap: wrap;
  width: min(100%, 860px);
}

.home-search-tags__label {
  color: var(--color-text-muted);
  font-size: 13px;
  line-height: 20px;
}

.home-search-tags__item {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-chip);
  background: rgba(255, 255, 255, 0.62);
  color: var(--color-text-secondary);
  font-size: 13px;
  line-height: 20px;
}

.home-search-tags__item:hover {
  border-color: var(--color-border-strong);
  color: var(--color-text-primary);
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

.member-hero__eyebrow,
.home-section__eyebrow {
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
  white-space: nowrap;
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
.live-card,
.schedule-card,
.product-card,
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
.live-card:hover,
.schedule-card:hover,
.product-card:hover,
.content-card:hover {
  border-color: #ded8ce;
  box-shadow: 0 10px 26px rgb(18 18 18 / 7%);
  transform: translateY(-2px);
}

.seller-card,
.live-card,
.schedule-card {
  display: grid;
}

.seller-card__cover,
.live-card__media,
.schedule-card__media,
.product-card__media {
  position: relative;
  display: block;
  overflow: hidden;
  background: var(--color-surface-secondary);
}

.seller-card__cover,
.live-card__media,
.schedule-card__media {
  aspect-ratio: 16 / 9;
}

.product-card__media {
  aspect-ratio: 16 / 9;
}

.seller-card__cover::after,
.product-card__media::after {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(14, 17, 16, 0.02), rgba(14, 17, 16, 0.42));
  content: '';
}

.seller-card__cover-image,
.live-card__image,
.schedule-card__image,
.product-card__image,
.content-card__image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.seller-card__status,
.live-card__badge,
.product-card__tag {
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

.seller-card__status--live,
.product-card__tag {
  background: var(--color-live);
}

.live-card__badge {
  gap: 6px;
  height: 28px;
  background: #b83f42;
}

.live-card__badge::before {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  content: '';
}

.schedule-card__time {
  position: absolute;
  z-index: 1;
  top: var(--space-3);
  left: var(--space-3);
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 10px;
  border-radius: var(--space-2);
  background: rgba(14, 17, 16, 0.66);
  color: var(--color-text-inverse);
  font-size: 12px;
  font-weight: 700;
  line-height: 18px;
}

.seller-card__body,
.live-card__body,
.schedule-card__body,
.product-card__body {
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
.seller-card__live-title,
.live-card__title,
.schedule-card__title,
.product-card__title {
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
.seller-card__stats,
.live-card__meta,
.schedule-card__meta,
.product-card__seller,
.product-card__meta {
  color: var(--color-text-muted);
  font-size: 13px;
  font-weight: 400;
  line-height: 20px;
}

.seller-card__time,
.live-card__meta--time,
.schedule-card__meta--time {
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

.schedule-card__action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: fit-content;
  height: 40px;
  padding: 0 var(--space-4);
  justify-self: end;
  margin-top: var(--space-2);
  border-radius: 12px;
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-size: 14px;
  font-weight: 600;
  line-height: 20px;
}

.product-card {
  display: grid;
}

.product-card__brand {
  color: var(--color-primary);
  font-size: 13px;
  font-weight: 600;
  line-height: 20px;
}

.product-card__price,
.product-card__bid {
  color: var(--color-text-primary);
  font-size: 14px;
  font-weight: 800;
  line-height: 21px;
}

.product-card__bid {
  color: var(--color-auction);
}

.product-card__tag--auction {
  background: var(--color-auction);
}

.product-card__tag--direct {
  background: var(--color-direct-sale);
}

.product-card__action {
  justify-self: end;
  margin-top: var(--space-2);
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

  .home-section__header {
    align-items: flex-start;
  }

  .home-section__title {
    font-size: 22px;
    line-height: 31px;
  }

  .seller-grid,
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
    height: auto;
  }

  .home-search__icon {
    display: none;
  }

  .home-search__input {
    height: 42px;
    line-height: 42px;
  }

  .home-search__button {
    width: 100%;
    height: 42px;
  }

  .home-search-tags {
    justify-content: flex-start;
  }

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

  .seller-card__live-title,
  .live-card__title,
  .schedule-card__title,
  .product-card__title {
    font-size: 15px;
    line-height: 22px;
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
