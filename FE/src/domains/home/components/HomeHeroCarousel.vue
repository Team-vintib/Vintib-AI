<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import type { HomeLiveCardItem, HomeViewData } from '@/domains/home/types/homeView.types'
import { ROUTE_PATHS } from '@/shared/constants/routes'
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
  scheduleText?: string
  collageImages?: string[]
}

const AUTO_PLAY_DELAY = 5000
const DRAG_THRESHOLD = 48
const MANUAL_PAUSE_DELAY = 6000

const fallbackImages = {
  live:
    'https://images.unsplash.com/photo-1516762689617-e1cffcef479d?auto=format&fit=crop&w=1200&q=80',
  discover:
    'https://images.unsplash.com/photo-1483985988355-763728e1935b?auto=format&fit=crop&w=1000&q=80',
  jacket:
    'https://images.unsplash.com/photo-1551028719-00167b16eac5?auto=format&fit=crop&w=900&q=80',
  knit:
    'https://images.unsplash.com/photo-1489987707025-afc232f7ea0f?auto=format&fit=crop&w=900&q=80',
  studio:
    'https://images.unsplash.com/photo-1496747611176-843222e1e57c?auto=format&fit=crop&w=1200&q=80',
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

const liveEntrySlide = computed<HeroSlide>(() => {
  if (selectedLive.value) {
    const live = selectedLive.value

    return {
      id: 'live-auction',
      label: 'LIVE AUCTION',
      title: '지금 놓치면 다시 만나기 어려워요',
      description: '실시간으로 상품을 확인하고,\n원하는 가격에 입찰해 보세요.',
      ctaLabel: '진행 중인 라이브 보기',
      to: `/lives/${live.id}`,
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
    to: scheduledLive ? `/lives/${scheduledLive.id}` : ROUTE_PATHS.LIVE_LIST,
    tone: 'live',
    visualKind: 'scheduled',
    imageUrl: scheduledLive?.thumbnailUrl || fallbackImages.live,
    imageAlt: scheduledLive?.title ?? '예약 라이브 대표 이미지',
    metaText: scheduledLive?.hostName,
    scheduleText: formatLiveSchedule(scheduledLive?.scheduledAt),
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
    to: ROUTE_PATHS.PRODUCT_LIST,
    tone: 'discover',
    visualKind: 'collage',
    imageUrl: fallbackImages.discover,
    imageAlt: '매거진 화보처럼 배치된 빈티지 의류',
    collageImages: [fallbackImages.discover, fallbackImages.jacket, fallbackImages.knit],
  },
  {
    id: 'sell-vintage',
    label: 'SELL YOUR VINTAGE',
    title: '옷장 속 빈티지,\n새로운 주인을 만나게 해주세요',
    description: '사진과 상품 정보만으로\n간편하게 판매를 시작할 수 있어요.',
    ctaLabel: '상품 등록하기',
    to: ROUTE_PATHS.PRODUCT_CREATE,
    tone: 'sell',
    visualKind: 'studio',
    imageUrl: fallbackImages.studio,
    imageAlt: '촬영 준비 중인 빈티지 의류',
  },
])

const shouldPauseAutoPlay = computed(
  () => isHovered.value || isFocused.value || isDragging.value || manualPause.value,
)

const trackStyle = computed(() => ({
  transform: `translateX(calc(${-activeIndex.value * 100}% + ${dragDeltaX.value}px))`,
}))

function formatViewerCount(value?: number) {
  return new Intl.NumberFormat('ko-KR').format(value ?? 0)
}

function formatLiveSchedule(value?: string) {
  if (!value) {
    return '일정 확인 중'
  }

  const date = new Date(value)
  const today = new Date()
  const dateLabel =
    date.toDateString() === today.toDateString()
      ? '오늘'
      : new Intl.DateTimeFormat('ko-KR', {
          month: 'long',
          day: 'numeric',
        }).format(date)
  const timeLabel = new Intl.DateTimeFormat('ko-KR', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  }).format(date)

  return `${dateLabel} ${timeLabel}`
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
  }, 0)
}

function handleSlideClick(slide: HeroSlide) {
  if (didDrag.value) {
    return
  }

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
          @click="handleSlideClick(slide)"
        >
          <div class="home-hero-slide__content">
            <p class="home-hero-slide__label">{{ slide.label }}</p>
            <h1 v-if="index === 0" class="home-hero-slide__title">{{ slide.title }}</h1>
            <h2 v-else class="home-hero-slide__title">{{ slide.title }}</h2>
            <p class="home-hero-slide__description">{{ slide.description }}</p>
            <RouterLink
              class="home-hero-slide__cta"
              :to="slide.to"
              :tabindex="index === activeIndex ? 0 : -1"
              @click.stop
            >
              {{ slide.ctaLabel }}
            </RouterLink>
          </div>

          <div class="home-hero-slide__media" :class="`home-hero-slide__media--${slide.visualKind}`">
            <template v-if="slide.visualKind === 'collage'">
              <img
                v-for="(imageUrl, imageIndex) in slide.collageImages"
                :key="imageUrl"
                class="home-hero-slide__collage-image"
                :class="`home-hero-slide__collage-image--${imageIndex + 1}`"
                :src="imageUrl"
                :alt="imageIndex === 0 ? slide.imageAlt : ''"
                @error="handleImageError"
              />
              <span class="home-hero-slide__media-note">LIVE · AUCTION · DIRECT</span>
            </template>

            <template v-else>
              <img
                class="home-hero-slide__image"
                :src="slide.imageUrl"
                :alt="slide.imageAlt"
                @error="handleImageError"
              />
              <span v-if="slide.visualKind === 'live'" class="home-hero-slide__live-badge">LIVE</span>
              <span v-if="slide.visualKind === 'scheduled'" class="home-hero-slide__schedule-card">
                {{ slide.scheduleText }}
              </span>
              <span v-if="slide.metaText" class="home-hero-slide__meta">{{ slide.metaText }}</span>
            </template>
          </div>
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
  display: grid;
  grid-template-columns: minmax(0, 1.04fr) minmax(0, 0.96fr);
  height: 300px;
  overflow: hidden;
  isolation: isolate;
  background:
    linear-gradient(105deg, rgba(244, 239, 230, 0.98) 0%, rgba(244, 239, 230, 0.86) 52%, transparent 72%),
    var(--hero-warm-paper);
  cursor: pointer;
}

.home-hero-slide--live {
  background:
    linear-gradient(105deg, rgba(18, 18, 18, 0.92) 0%, rgba(18, 18, 18, 0.74) 48%, rgba(18, 18, 18, 0.16) 76%),
    var(--hero-ink-black);
  color: var(--color-text-inverse);
}

.home-hero-slide--discover {
  background:
    linear-gradient(105deg, rgba(244, 239, 230, 0.98) 0%, rgba(244, 239, 230, 0.9) 50%, rgba(74, 107, 87, 0.1) 82%),
    var(--hero-warm-paper);
}

.home-hero-slide--sell {
  background:
    linear-gradient(105deg, rgba(244, 239, 230, 0.98) 0%, rgba(244, 239, 230, 0.86) 52%, rgba(200, 166, 106, 0.14) 86%),
    var(--hero-warm-paper);
}

.home-hero-slide__content {
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

.home-hero-slide__media {
  position: relative;
  min-width: 0;
  height: 100%;
  overflow: hidden;
  background: color-mix(in srgb, var(--hero-film-gray) 30%, var(--hero-warm-paper));
}

.home-hero-slide__media::after {
  position: absolute;
  inset: 0;
  z-index: 1;
  background:
    linear-gradient(90deg, rgba(18, 18, 18, 0.24), transparent 34%),
    linear-gradient(0deg, rgba(18, 18, 18, 0.42), transparent 48%);
  content: '';
  pointer-events: none;
}

.home-hero-slide__image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.home-hero-slide__live-badge,
.home-hero-slide__schedule-card,
.home-hero-slide__meta,
.home-hero-slide__media-note {
  position: absolute;
  z-index: 2;
}

.home-hero-slide__live-badge {
  top: var(--space-6);
  left: var(--space-6);
  display: inline-flex;
  align-items: center;
  gap: 7px;
  min-height: 30px;
  padding: 0 12px;
  border-radius: var(--radius-chip);
  background: var(--hero-accent-red);
  color: var(--color-text-inverse);
  font-size: 12px;
  font-weight: 800;
  line-height: 18px;
}

.home-hero-slide__live-badge::before {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: currentColor;
  content: '';
}

.home-hero-slide__schedule-card {
  top: var(--space-6);
  left: var(--space-6);
  display: inline-flex;
  min-height: 38px;
  align-items: center;
  padding: 0 var(--space-4);
  border: 1px solid rgba(255, 255, 255, 0.42);
  border-radius: 12px;
  background: rgba(244, 239, 230, 0.9);
  color: var(--hero-ink-black);
  font-size: 14px;
  font-weight: 800;
  line-height: 20px;
}

.home-hero-slide__meta {
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

.home-hero-slide__media--collage {
  display: grid;
  height: 300px;
  padding: var(--space-6);
  background:
    linear-gradient(135deg, rgba(74, 107, 87, 0.16), rgba(244, 239, 230, 0.22)),
    var(--hero-warm-paper);
}

.home-hero-slide__media--collage::after {
  background: linear-gradient(0deg, rgba(18, 18, 18, 0.12), transparent 48%);
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

.home-hero-slide__media-note {
  right: var(--space-6);
  bottom: var(--space-6);
  padding: 8px 12px;
  border-radius: var(--radius-chip);
  background: rgba(74, 107, 87, 0.88);
  color: var(--color-text-inverse);
  font-size: 12px;
  font-weight: 800;
  line-height: 18px;
}

.home-hero-slide__media--studio::after {
  background:
    linear-gradient(90deg, rgba(244, 239, 230, 0.3), transparent 38%),
    linear-gradient(0deg, rgba(18, 18, 18, 0.3), transparent 52%);
}

.home-hero-carousel__arrow {
  position: absolute;
  z-index: 3;
  top: 50%;
  display: inline-grid;
  width: 42px;
  height: 42px;
  place-items: center;
  border: 1px solid rgba(255, 255, 255, 0.54);
  border-radius: 50%;
  background: rgba(18, 18, 18, 0.22);
  color: var(--color-text-inverse);
  font-size: 30px;
  line-height: 1;
  opacity: 0.54;
  transform: translateY(-50%);
  transition:
    background 160ms ease,
    opacity 160ms ease;
}

.home-hero-carousel:hover .home-hero-carousel__arrow,
.home-hero-carousel:focus-within .home-hero-carousel__arrow {
  background: rgba(18, 18, 18, 0.52);
  opacity: 1;
}

.home-hero-carousel__arrow--previous {
  left: var(--space-5);
}

.home-hero-carousel__arrow--next {
  right: var(--space-5);
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
    grid-template-columns: 1fr;
    grid-template-rows: 180px 160px;
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

  .home-hero-slide__media,
  .home-hero-slide__image,
  .home-hero-slide__media--collage {
    height: 160px;
  }

  .home-hero-carousel__arrow {
    display: none;
  }

  .home-hero-slide__live-badge,
  .home-hero-slide__schedule-card {
    top: var(--space-4);
    left: var(--space-4);
  }

  .home-hero-slide__meta {
    right: var(--space-4);
    bottom: calc(var(--space-4) + 14px);
    left: var(--space-4);
    max-width: none;
  }

  .home-hero-slide__collage-image--1 {
    right: 14%;
    bottom: 8%;
    width: 40%;
    height: 70%;
  }

  .home-hero-slide__collage-image--2 {
    left: 8%;
    width: 38%;
  }

  .home-hero-slide__collage-image--3 {
    right: 8%;
    width: 28%;
  }
}

@media (max-width: 520px) {
  .home-hero-slide {
    grid-template-rows: 190px 150px;
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
