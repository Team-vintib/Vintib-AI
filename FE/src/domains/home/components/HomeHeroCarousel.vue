<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import type { HomeProductCardItem, HomeViewData } from '@/domains/home/types/homeView.types'
import { ROUTE_NAMES } from '@/shared/constants/routes'
import type { RouteLocationRaw } from 'vue-router'

const props = defineProps<{
  homeData: HomeViewData
}>()

type HeroSlideTone = 'live' | 'discover' | 'sell'
type HeroVisualKind = 'live' | 'scheduled' | 'collage' | 'studio'

interface HeroSlide {
  id: string
  label: string
  title: string
  description: string
  ctaLabel: string
  to: RouteLocationRaw
  tone: HeroSlideTone
  visualKind: HeroVisualKind
  imageUrl: string
  imageAlt: string
  metaText?: string
  collageImages?: string[]
}

const AUTO_PLAY_DELAY = 5000
const DRAG_THRESHOLD = 48
const MANUAL_PAUSE_DELAY = 6000

const fallbackImages = {
  live:
    'https://images.unsplash.com/photo-1516762689617-e1cffcef479d?auto=format&fit=crop&w=1200&q=80',
  discover:
    'https://images.unsplash.com/photo-1529139574466-a303027c1d8b?auto=format&fit=crop&w=1200&q=80',
  jacket:
    'https://images.unsplash.com/photo-1551028719-00167b16eac5?auto=format&fit=crop&w=900&q=80',
  knit:
    'https://images.unsplash.com/photo-1489987707025-afc232f7ea0f?auto=format&fit=crop&w=900&q=80',
  studio:
    'https://images.unsplash.com/photo-1490481651871-ab68de25d43d?auto=format&fit=crop&w=1200&q=80',
}

const router = useRouter()
const activeIndex = ref(0)
const isHovered = ref(false)
const isFocused = ref(false)
const isDragging = ref(false)
const manualPause = ref(false)
const dragStartX = ref(0)
const dragDeltaX = ref(0)
const didDrag = ref(false)
let autoPlayTimer: ReturnType<typeof window.setInterval> | null = null
let manualPauseTimer: ReturnType<typeof window.setTimeout> | null = null

const selectedLive = computed(() => props.homeData.liveNow[0])
const selectedScheduledLive = computed(() =>
  [...props.homeData.scheduledLives].sort((first, second) => {
    const firstTime = first.scheduledAt ? new Date(first.scheduledAt).getTime() : Number.MAX_SAFE_INTEGER
    const secondTime = second.scheduledAt
      ? new Date(second.scheduledAt).getTime()
      : Number.MAX_SAFE_INTEGER

    return firstTime - secondTime
  })[0],
)
const productImageCandidates = computed(() =>
  getUniqueImageUrls([
    ...props.homeData.recommendedProducts,
    ...props.homeData.directSaleProducts,
    ...props.homeData.upcomingAuctionProducts,
    ...props.homeData.categoryProductSections.flatMap((section) => section.products),
  ]),
)
const discoverCollageImages = computed(() =>
  fillImageSlots(productImageCandidates.value, [
    fallbackImages.discover,
    fallbackImages.jacket,
    fallbackImages.knit,
  ]),
)

const liveEntrySlide = computed<HeroSlide>(() => {
  if (selectedLive.value) {
    const live = selectedLive.value

    return {
      id: 'live-auction',
      label: 'LIVE AUCTION',
      title: '지금 놓치면 다시 만나기 어려워요',
      description: '실시간으로 상품을 확인하고,\n원하는 가격에 입찰해 보세요.',
      ctaLabel: '진행 중인 라이브 보기',
      to: getLiveWatchRoute(live.id),
      tone: 'live',
      visualKind: 'live',
      imageUrl: live.thumbnailUrl || fallbackImages.live,
      imageAlt: live.title,
      metaText: `${live.hostName} · ${formatViewerCount(live.viewerCount)} 시청 중`,
    }
  }

  const scheduledLive = selectedScheduledLive.value

  return {
    id: 'upcoming-live',
    label: 'UPCOMING LIVE',
    title: '다음 빈티지 드롭을 기다려 보세요',
    description: '곧 시작되는 라이브에서\n새로운 빈티지 상품을 만나보세요.',
    ctaLabel: '예약 라이브 확인하기',
    to: scheduledLive ? getLiveWatchRoute(scheduledLive.id) : { name: ROUTE_NAMES.LIVE_LIST },
    tone: 'live',
    visualKind: 'scheduled',
    imageUrl: scheduledLive?.thumbnailUrl || fallbackImages.live,
    imageAlt: scheduledLive?.title ?? '예약 라이브 대표 이미지',
    metaText: scheduledLive?.hostName,
  }
})

const slides = computed<HeroSlide[]>(() => [
  liveEntrySlide.value,
  {
    id: 'discover-vintage',
    label: 'DISCOVER VINTAGE',
    title: '하나뿐인 빈티지를,\n가장 생생하게',
    description: '라이브로 상태를 확인하고\n경매와 바로 구매로 만나보세요.',
    ctaLabel: '빈티지 둘러보기',
    to: { name: ROUTE_NAMES.PRODUCT_LIST },
    tone: 'discover',
    visualKind: 'collage',
    imageUrl: fallbackImages.discover,
    imageAlt: '매거진 화보처럼 배치된 빈티지 의류',
    collageImages: discoverCollageImages.value,
  },
  {
    id: 'sell-vintage',
    label: 'SELL YOUR VINTAGE',
    title: '옷장 속 빈티지,\n새로운 주인을 만나게 해주세요',
    description: '사진과 상품 정보만으로\n간편하게 판매를 시작할 수 있어요.',
    ctaLabel: '상품 등록하기',
    to: { name: ROUTE_NAMES.PRODUCT_CREATE },
    tone: 'sell',
    visualKind: 'studio',
    imageUrl: fallbackImages.studio,
    imageAlt: '촬영 준비 중인 빈티지 의류',
  },
])

const shouldPauseAutoPlay = computed(
  () => isHovered.value || isFocused.value || isDragging.value || manualPause.value,
)
const activeSlide = computed(() => slides.value[activeIndex.value])

const trackStyle = computed(() => ({
  transform: `translateX(calc(${-activeIndex.value * 100}% + ${dragDeltaX.value}px))`,
}))

function formatViewerCount(value?: number) {
  return new Intl.NumberFormat('ko-KR').format(value ?? 0)
}

function getLiveWatchRoute(liveId: number): RouteLocationRaw {
  return {
    name: ROUTE_NAMES.LIVE_WATCH,
    params: { liveId },
  }
}

function getUniqueImageUrls(products: HomeProductCardItem[]) {
  return [...new Set(products.map((product) => product.primaryImageUrl).filter(Boolean))]
}

function fillImageSlots(imageUrls: string[], fallbackUrls: string[]) {
  return [...new Set([...imageUrls, ...fallbackUrls])].slice(0, 3)
}

function moveTo(index: number) {
  const slideCount = slides.value.length

  activeIndex.value = (index + slideCount) % slideCount
}

function moveNext() {
  moveTo(activeIndex.value + 1)
}

function movePrevious() {
  moveTo(activeIndex.value - 1)
}

function pauseAfterManualInteraction() {
  manualPause.value = true

  if (manualPauseTimer) {
    window.clearTimeout(manualPauseTimer)
  }

  manualPauseTimer = window.setTimeout(() => {
    manualPause.value = false
  }, MANUAL_PAUSE_DELAY)
}

function handlePreviousClick() {
  pauseAfterManualInteraction()
  movePrevious()
}

function handleNextClick() {
  pauseAfterManualInteraction()
  moveNext()
}

function handleIndicatorClick(index: number) {
  pauseAfterManualInteraction()
  moveTo(index)
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'ArrowLeft') {
    event.preventDefault()
    pauseAfterManualInteraction()
    movePrevious()
  }

  if (event.key === 'ArrowRight') {
    event.preventDefault()
    pauseAfterManualInteraction()
    moveNext()
  }

  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    navigateToActiveSlide()
  }
}

function handlePointerDown(event: PointerEvent) {
  if (event.pointerType === 'mouse' && event.button !== 0) {
    return
  }

  isDragging.value = true
  didDrag.value = false
  dragStartX.value = event.clientX
  dragDeltaX.value = 0

  if (event.currentTarget instanceof HTMLElement) {
    event.currentTarget.setPointerCapture(event.pointerId)
  }
}

function handlePointerMove(event: PointerEvent) {
  if (!isDragging.value) {
    return
  }

  dragDeltaX.value = event.clientX - dragStartX.value
  didDrag.value = Math.abs(dragDeltaX.value) > 8
}

function handlePointerEnd() {
  if (!isDragging.value) {
    return
  }

  const deltaX = dragDeltaX.value

  isDragging.value = false
  dragDeltaX.value = 0

  if (Math.abs(deltaX) >= DRAG_THRESHOLD) {
    pauseAfterManualInteraction()

    if (deltaX < 0) {
      moveNext()
    } else {
      movePrevious()
    }
  }

  window.setTimeout(() => {
    didDrag.value = false
  }, 150)
}

function navigateToActiveSlide() {
  const slide = activeSlide.value

  if (!slide || didDrag.value) {
    return
  }

  navigateToSlide(slide)
}

function navigateToSlide(slide: HeroSlide) {
  pauseAfterManualInteraction()
  void router.push(slide.to)
}

function handleImageError(event: Event) {
  if (event.target instanceof HTMLImageElement) {
    event.target.onerror = null
    event.target.src = fallbackImages.live
  }
}

function startAutoPlay() {
  stopAutoPlay()

  autoPlayTimer = window.setInterval(() => {
    if (!shouldPauseAutoPlay.value) {
      moveNext()
    }
  }, AUTO_PLAY_DELAY)
}

function stopAutoPlay() {
  if (autoPlayTimer) {
    window.clearInterval(autoPlayTimer)
    autoPlayTimer = null
  }
}

onMounted(() => {
  startAutoPlay()
})

onBeforeUnmount(() => {
  stopAutoPlay()

  if (manualPauseTimer) {
    window.clearTimeout(manualPauseTimer)
  }
})
</script>

<template>
  <section
    class="home-hero-carousel"
    aria-roledescription="carousel"
    aria-label="VinTib 주요 기능"
    tabindex="0"
    @mouseenter="isHovered = true"
    @mouseleave="isHovered = false"
    @focusin="isFocused = true"
    @focusout="isFocused = false"
    @keydown="handleKeydown"
  >
    <div
      class="home-hero-carousel__viewport"
      @pointerdown="handlePointerDown"
      @pointermove="handlePointerMove"
      @pointerup="handlePointerEnd"
      @pointercancel="handlePointerEnd"
      @pointerleave="handlePointerEnd"
      @click="navigateToActiveSlide"
    >
      <div
        class="home-hero-carousel__track"
        :class="{ 'home-hero-carousel__track--dragging': isDragging }"
        :style="trackStyle"
      >
        <article
          v-for="(slide, index) in slides"
          :key="slide.id"
          class="home-hero-slide"
          :class="[`home-hero-slide--${slide.tone}`, { 'home-hero-slide--active': index === activeIndex }]"
          :aria-hidden="index !== activeIndex"
        >
          <img
            class="home-hero-slide__background"
            :src="slide.imageUrl"
            :alt="slide.imageAlt"
            @error="handleImageError"
          />
          <div class="home-hero-slide__content">
            <p class="home-hero-slide__label">{{ slide.label }}</p>
            <h1 v-if="index === 0" class="home-hero-slide__title">{{ slide.title }}</h1>
            <h2 v-else class="home-hero-slide__title">{{ slide.title }}</h2>
            <p class="home-hero-slide__description">{{ slide.description }}</p>
            <button
              class="home-hero-slide__cta"
              type="button"
              :tabindex="index === activeIndex ? 0 : -1"
              @click.stop="navigateToSlide(slide)"
            >
              {{ slide.ctaLabel }}
            </button>
          </div>

          <div
            v-if="slide.visualKind === 'collage' && slide.collageImages"
            class="home-hero-slide__collage"
          >
            <img
              v-for="(imageUrl, imageIndex) in slide.collageImages"
              :key="imageUrl"
              class="home-hero-slide__collage-image"
              :class="`home-hero-slide__collage-image--${imageIndex + 1}`"
              :src="imageUrl"
              alt=""
              @error="handleImageError"
            />
          </div>
          <span v-if="slide.metaText" class="home-hero-slide__meta">{{ slide.metaText }}</span>
        </article>
      </div>
    </div>

    <button
      class="home-hero-carousel__arrow home-hero-carousel__arrow--previous"
      type="button"
      aria-label="이전 배너 보기"
      @click.stop="handlePreviousClick"
    >
      <span aria-hidden="true">‹</span>
    </button>
    <button
      class="home-hero-carousel__arrow home-hero-carousel__arrow--next"
      type="button"
      aria-label="다음 배너 보기"
      @click.stop="handleNextClick"
    >
      <span aria-hidden="true">›</span>
    </button>

    <div class="home-hero-carousel__indicators" aria-label="배너 위치">
      <button
        v-for="(slide, index) in slides"
        :key="slide.id"
        class="home-hero-carousel__indicator"
        :class="{ 'home-hero-carousel__indicator--active': index === activeIndex }"
        type="button"
        :aria-label="`${index + 1}번째 배너 보기`"
        :aria-current="index === activeIndex ? 'true' : undefined"
        @click="handleIndicatorClick(index)"
      />
    </div>
  </section>
</template>

<style scoped lang="scss">
.home-hero-carousel {
  --hero-warm-paper: #f4efe6;
  --hero-ink-black: #121212;
  --hero-vintage-green: #4a6b57;
  --hero-accent-red: #e34234;
  --hero-film-gray: #c9c6c1;
  --hero-gold-foil: #c8a66a;

  position: relative;
  overflow: hidden;
  border-radius: 24px;
  background: var(--hero-warm-paper);
  color: var(--hero-ink-black);
  outline: none;
}

.home-hero-carousel:focus-visible {
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--hero-vintage-green) 26%, transparent);
}

.home-hero-carousel__viewport {
  overflow: hidden;
  touch-action: pan-y;
  cursor: grab;
}

.home-hero-carousel__viewport:active {
  cursor: grabbing;
}

.home-hero-carousel__track {
  display: flex;
  transition: transform 420ms ease;
  will-change: transform;
}

.home-hero-carousel__track--dragging {
  transition: none;
}

.home-hero-slide {
  position: relative;
  flex: 0 0 100%;
  display: block;
  height: 300px;
  overflow: hidden;
  isolation: isolate;
  background: var(--hero-ink-black);
  cursor: pointer;
}

.home-hero-slide::before {
  position: absolute;
  inset: 0;
  z-index: 1;
  background:
    linear-gradient(90deg, rgba(18, 18, 18, 0.88) 0%, rgba(18, 18, 18, 0.7) 38%, rgba(18, 18, 18, 0.18) 68%, rgba(18, 18, 18, 0.04) 100%),
    linear-gradient(0deg, rgba(18, 18, 18, 0.26), transparent 56%);
  content: '';
}

.home-hero-slide__background {
  position: absolute;
  inset: 0;
  z-index: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center;
  transform: scale(1.02);
}

.home-hero-slide--live {
  color: var(--color-text-inverse);
}

.home-hero-slide--discover::before {
  background:
    linear-gradient(90deg, rgba(244, 239, 230, 0.96) 0%, rgba(244, 239, 230, 0.84) 39%, rgba(244, 239, 230, 0.24) 72%, rgba(244, 239, 230, 0.06) 100%),
    linear-gradient(0deg, rgba(74, 107, 87, 0.16), transparent 58%);
}

.home-hero-slide--sell::before {
  background:
    linear-gradient(90deg, rgba(244, 239, 230, 0.95) 0%, rgba(244, 239, 230, 0.82) 40%, rgba(244, 239, 230, 0.2) 72%, rgba(244, 239, 230, 0.04) 100%),
    linear-gradient(0deg, rgba(200, 166, 106, 0.18), transparent 58%);
}

.home-hero-slide__content {
  position: relative;
  z-index: 2;
  display: grid;
  align-content: center;
  justify-items: start;
  gap: var(--space-3);
  min-width: 0;
  padding: var(--space-8) var(--space-10);
}

.home-hero-slide__label {
  color: var(--hero-vintage-green);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0;
  line-height: 18px;
}

.home-hero-slide--live .home-hero-slide__label {
  color: var(--hero-accent-red);
}

.home-hero-slide__title {
  max-width: 520px;
  white-space: pre-line;
  color: inherit;
  font-size: 30px;
  font-weight: 800;
  line-height: 39px;
  letter-spacing: 0;
}

.home-hero-slide__description {
  max-width: 360px;
  white-space: pre-line;
  color: color-mix(in srgb, currentColor 72%, transparent);
  font-size: 16px;
  line-height: 26px;
}

.home-hero-slide__cta {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 48px;
  padding: 0 var(--space-5);
  margin-top: var(--space-2);
  border: 0;
  border-radius: 14px;
  background: var(--hero-vintage-green);
  color: var(--color-text-inverse);
  font-size: 15px;
  font-weight: 800;
  line-height: 20px;
  white-space: nowrap;
}

.home-hero-slide--live .home-hero-slide__cta {
  background: var(--hero-accent-red);
}

.home-hero-slide--sell .home-hero-slide__cta {
  background: var(--hero-ink-black);
}

.home-hero-slide__meta {
  position: absolute;
  z-index: 2;
  right: var(--space-6);
  bottom: var(--space-6);
  max-width: calc(100% - var(--space-12));
  padding: 10px var(--space-4);
  border-radius: 12px;
  background: rgba(18, 18, 18, 0.64);
  color: var(--color-text-inverse);
  font-size: 14px;
  font-weight: 700;
  line-height: 20px;
}

.home-hero-slide__collage {
  position: absolute;
  inset: 0 0 0 46%;
  z-index: 1;
  pointer-events: none;
}

.home-hero-slide__collage-image {
  position: absolute;
  z-index: 1;
  object-fit: cover;
  box-shadow: 0 18px 36px rgba(18, 18, 18, 0.16);
}

.home-hero-slide__collage-image--1 {
  right: 16%;
  bottom: 11%;
  width: 38%;
  height: 68%;
}

.home-hero-slide__collage-image--2 {
  top: 9%;
  left: 10%;
  width: 35%;
  height: 54%;
}

.home-hero-slide__collage-image--3 {
  right: 8%;
  top: 13%;
  width: 26%;
  height: 38%;
}

.home-hero-carousel__arrow {
  position: absolute;
  z-index: 3;
  top: 50%;
  display: inline-flex;
  width: 32px;
  height: 48px;
  align-items: center;
  justify-content: center;
  border: 0;
  background: transparent;
  color: var(--color-text-inverse);
  font-size: 44px;
  font-weight: 300;
  line-height: 1;
  opacity: 0.62;
  transform: translateY(-50%);
  transition:
    color 160ms ease,
    opacity 160ms ease;
}

.home-hero-carousel:hover .home-hero-carousel__arrow,
.home-hero-carousel:focus-within .home-hero-carousel__arrow {
  color: var(--color-text-inverse);
  opacity: 1;
}

.home-hero-carousel__arrow--previous {
  left: var(--space-4);
}

.home-hero-carousel__arrow--next {
  right: var(--space-4);
}

.home-hero-carousel__indicators {
  position: absolute;
  z-index: 3;
  right: 0;
  bottom: var(--space-5);
  left: 0;
  display: flex;
  justify-content: center;
  gap: var(--space-2);
  pointer-events: none;
}

.home-hero-carousel__indicator {
  width: 8px;
  height: 8px;
  border: 0;
  border-radius: var(--radius-chip);
  background: rgba(255, 255, 255, 0.64);
  pointer-events: auto;
  transition:
    width 180ms ease,
    background 180ms ease;
}

.home-hero-carousel__indicator--active {
  width: 32px;
  background: var(--hero-gold-foil);
}

@media (max-width: 768px) {
  .home-hero-carousel {
    border-radius: 22px;
  }

  .home-hero-slide {
    height: 340px;
  }

  .home-hero-slide__content {
    align-content: start;
    padding: var(--space-5) var(--space-5) var(--space-4);
  }

  .home-hero-slide__title {
    max-width: 420px;
    font-size: 24px;
    line-height: 32px;
  }

  .home-hero-slide__description {
    font-size: 14px;
    line-height: 22px;
  }

  .home-hero-slide__cta {
    min-height: 50px;
  }

  .home-hero-slide::before {
    background:
      linear-gradient(180deg, rgba(18, 18, 18, 0.82) 0%, rgba(18, 18, 18, 0.56) 54%, rgba(18, 18, 18, 0.16) 100%),
      linear-gradient(90deg, rgba(18, 18, 18, 0.44), transparent 70%);
  }

  .home-hero-slide--discover::before,
  .home-hero-slide--sell::before {
    background:
      linear-gradient(180deg, rgba(244, 239, 230, 0.95) 0%, rgba(244, 239, 230, 0.78) 58%, rgba(244, 239, 230, 0.18) 100%),
      linear-gradient(90deg, rgba(244, 239, 230, 0.62), transparent 72%);
  }

  .home-hero-carousel__arrow {
    display: none;
  }

  .home-hero-slide__meta {
    right: var(--space-4);
    bottom: calc(var(--space-4) + 14px);
    left: var(--space-4);
    max-width: none;
  }

  .home-hero-slide__collage-image--1 {
    right: 8%;
    bottom: 7%;
    width: 42%;
    height: 42%;
  }

  .home-hero-slide__collage-image--2 {
    top: auto;
    bottom: 10%;
    left: 10%;
    width: 34%;
    height: 34%;
  }

  .home-hero-slide__collage-image--3 {
    top: auto;
    right: 22%;
    bottom: 30%;
    width: 24%;
    height: 28%;
  }
}

@media (max-width: 520px) {
  .home-hero-slide {
    height: 340px;
  }

  .home-hero-slide__content {
    gap: var(--space-2);
    padding: var(--space-5);
  }

  .home-hero-slide__title {
    font-size: 23px;
    line-height: 31px;
  }

  .home-hero-slide__description {
    max-width: 310px;
  }

  .home-hero-carousel__indicators {
    bottom: var(--space-4);
  }
}

@media (prefers-reduced-motion: reduce) {
  .home-hero-carousel__track,
  .home-hero-carousel__indicator,
  .home-hero-carousel__arrow {
    transition-duration: 1ms;
  }
}
</style>
