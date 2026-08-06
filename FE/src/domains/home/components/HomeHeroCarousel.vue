<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { registerLiveReminder } from '@/domains/live/api/liveWatchApi'
import type { HomePopularHostLive, HomeViewData } from '@/domains/home/types/homeView.types'
import { ROUTE_NAMES } from '@/shared/constants/routes'
import type { RouteLocationRaw } from 'vue-router'

const props = defineProps<{
  homeData: HomeViewData
  popularHostLive?: HomePopularHostLive | null
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
  collageImages?: string[]
  onCtaClick?: () => void
}

const AUTO_PLAY_DELAY = 5000
const DRAG_THRESHOLD = 48
const MANUAL_PAUSE_DELAY = 6000

const fallbackImages = {
  live:
    'https://images.unsplash.com/photo-1516762689617-e1cffcef479d?auto=format&fit=crop&w=1200&q=80',
  upcoming:
    'https://images.unsplash.com/photo-1483985988355-763728e1935b?auto=format&fit=crop&w=1200&q=80',
  popularHost:
    'https://images.unsplash.com/photo-1524253482453-3fed8d2fe12b?auto=format&fit=crop&w=1200&q=80',
  discoverBackground:
    'https://images.unsplash.com/photo-1490114538077-0a7f8cb49891?auto=format&fit=crop&w=1200&q=80',
  discover:
    'https://images.unsplash.com/photo-1529139574466-a303027c1d8b?auto=format&fit=crop&w=1200&q=80',
  jacket:
    'https://images.unsplash.com/photo-1551028719-00167b16eac5?auto=format&fit=crop&w=900&q=80',
  knit:
    'https://images.unsplash.com/photo-1489987707025-afc232f7ea0f?auto=format&fit=crop&w=900&q=80',
  rack:
    'https://images.unsplash.com/photo-1445205170230-053b83016050?auto=format&fit=crop&w=900&q=80',
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

type ReminderState = 'idle' | 'pending' | 'done' | 'error'
const popularHostReminderState = ref<ReminderState>('idle')

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
// 상품 데이터 유무와 무관하게 항상 같은 4장을 보여준다(홈 배너 고정 이미지 요청).
const discoverCollageImages = [
  fallbackImages.discover,
  fallbackImages.jacket,
  fallbackImages.knit,
  fallbackImages.rack,
]

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
    imageUrl: scheduledLive?.thumbnailUrl || fallbackImages.upcoming,
    imageAlt: scheduledLive?.title ?? '예약 라이브 대표 이미지',
  }
})

const popularHostReminderLabel = computed(() => {
  if (popularHostReminderState.value === 'pending') return '설정 중...'
  if (popularHostReminderState.value === 'done') return '알림 설정 완료'
  if (popularHostReminderState.value === 'error') return '다시 시도'
  return '알림 설정'
})

const popularHostLiveSlide = computed<HeroSlide | null>(() => {
  const popularHostLive = props.popularHostLive

  if (!popularHostLive) {
    return null
  }

  const live = popularHostLive.live

  return {
    id: 'popular-host-live',
    label: 'MOST FOLLOWED',
    title: '인기 셀러의\n다음 라이브를 놓치지 마세요',
    description: formatScheduledAt(live.scheduledAt),
    ctaLabel: popularHostReminderLabel.value,
    to: getLiveWatchRoute(live.id),
    tone: 'live',
    visualKind: 'scheduled',
    imageUrl: live.thumbnailUrl || fallbackImages.popularHost,
    imageAlt: live.title,
    onCtaClick: () => handlePopularHostReminderClick(live.id),
  }
})

const slides = computed<HeroSlide[]>(() => [
  ...(popularHostLiveSlide.value ? [popularHostLiveSlide.value] : []),
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
    imageUrl: fallbackImages.discoverBackground,
    imageAlt: '매거진 화보처럼 배치된 빈티지 의류',
    collageImages: discoverCollageImages,
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

function formatScheduledAt(value?: string) {
  if (!value) {
    return '라이브 일정 확인 중'
  }

  const formatted = new Intl.DateTimeFormat('ko-KR', {
    month: 'long',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  }).format(new Date(value))

  return `${formatted} 라이브 예정`
}

function getLiveWatchRoute(liveId: number): RouteLocationRaw {
  return {
    name: ROUTE_NAMES.LIVE_WATCH,
    params: { liveId },
  }
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

function handleCtaClick(slide: HeroSlide) {
  if (slide.onCtaClick) {
    pauseAfterManualInteraction()
    slide.onCtaClick()
    return
  }

  navigateToSlide(slide)
}

async function handlePopularHostReminderClick(liveId: number) {
  if (popularHostReminderState.value === 'pending' || popularHostReminderState.value === 'done') {
    return
  }

  popularHostReminderState.value = 'pending'

  try {
    await registerLiveReminder(liveId)
    popularHostReminderState.value = 'done'
  } catch {
    popularHostReminderState.value = 'error'
  }
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
          </div>

          <button
            class="home-hero-slide__cta"
            type="button"
            :tabindex="index === activeIndex ? 0 : -1"
            @click.stop="handleCtaClick(slide)"
          >
            {{ slide.ctaLabel }}
          </button>

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
        </article>
      </div>
    </div>

    <button
      class="home-hero-carousel__arrow home-hero-carousel__arrow--previous"
      type="button"
      aria-label="이전 배너 보기"
      @click.stop="handlePreviousClick"
    >
      <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M15 5l-7 7 7 7" /></svg>
    </button>
    <button
      class="home-hero-carousel__arrow home-hero-carousel__arrow--next"
      type="button"
      aria-label="다음 배너 보기"
      @click.stop="handleNextClick"
    >
      <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M9 5l7 7-7 7" /></svg>
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
  --hero-accent-red: var(--color-accent);
  --hero-film-gray: var(--color-text-muted);

  position: relative;
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-image-frame);
  color: var(--color-text-primary);
  outline: none;
}

.home-hero-carousel:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
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
  height: 440px;
  overflow: hidden;
  isolation: isolate;
  background: var(--color-page);
  cursor: pointer;
}

.home-hero-slide::before {
  position: absolute;
  inset: 0;
  z-index: var(--z-layer-1);
  background: var(--gradient-hero-scrim);
  content: '';
}

.home-hero-slide__background {
  position: absolute;
  inset: 0;
  z-index: 0; /* --z-layer-1(그라디언트)보다 아래 명시 */
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center;
  filter: saturate(0.82) contrast(1.04) brightness(0.9);
  transform: scale(1.02);
}

.home-hero-slide--live {
  color: var(--color-text-primary);
}

.home-hero-slide--discover::before,
.home-hero-slide--sell::before {
  background: var(--gradient-hero-scrim);
}

.home-hero-slide__content {
  position: relative;
  z-index: var(--z-layer-2);
  display: grid;
  align-content: start;
  justify-items: start;
  gap: var(--space-3);
  min-width: 0;
  max-height: 62%;
  padding: var(--space-12) var(--space-10) 0;
  overflow: hidden;
}

.home-hero-slide__label {
  color: var(--color-text-muted);
  font-family: var(--font-mono);
  font-size: var(--font-size-2xs);
  font-weight: var(--font-weight-regular);
  letter-spacing: 0.2em;
  line-height: var(--line-height-snug);
  text-transform: uppercase;
}

.home-hero-slide--live .home-hero-slide__label {
  color: var(--hero-accent-red);
}

.home-hero-slide__title {
  max-width: 560px;
  white-space: pre-line;
  color: inherit;
  font-family: var(--font-display);
  font-size: var(--font-size-hero-display);
  font-weight: var(--font-weight-semibold);
  line-height: 1.08;
  letter-spacing: -0.03em;
}

.home-hero-slide__description {
  max-width: 380px;
  white-space: pre-line;
  color: var(--color-text-secondary);
  font-size: var(--font-size-body);
  font-weight: var(--font-weight-light);
  line-height: var(--line-height-body);
}

.home-hero-slide__cta {
  position: absolute;
  z-index: var(--z-layer-2);
  top: 72%;
  left: var(--space-10);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: var(--button-height-compact);
  padding: 0 var(--space-5);
  border: 0;
  border-radius: var(--radius-control);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-medium);
  line-height: var(--line-height-control);
  white-space: nowrap;
  transform: translateY(-50%);
  transition:
    background-color var(--transition-standard),
    color var(--transition-standard);
}

.home-hero-slide__cta:hover {
  background: var(--color-primary-hover);
  color: var(--color-primary-strong);
}

.home-hero-slide--live .home-hero-slide__cta {
  background: var(--hero-accent-red);
  color: var(--color-primary-strong);
}

.home-hero-slide--live .home-hero-slide__cta:hover {
  background: var(--color-accent-hover);
}

.home-hero-slide__collage {
  position: absolute;
  inset: 0 0 0 46%;
  z-index: var(--z-layer-1);
  pointer-events: none;
}

.home-hero-slide__collage-image {
  position: absolute;
  z-index: var(--z-layer-1);
  object-fit: cover;
  border-radius: var(--radius-media);
  filter: saturate(0.88) contrast(1.04) brightness(0.95);
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

.home-hero-slide__collage-image--4 {
  bottom: 6%;
  left: 10%;
  width: 30%;
  height: 30%;
}

.home-hero-carousel__arrow {
  position: absolute;
  z-index: var(--z-layer-3);
  top: 50%;
  display: inline-flex;
  width: var(--space-8);
  height: var(--button-height-standard);
  align-items: center;
  justify-content: center;
  border: 0;
  background: transparent;
  color: var(--color-text-inverse);
  opacity: 0.62;
  transform: translateY(-50%);
  transition:
    color var(--transition-fast),
    opacity var(--transition-fast);
}

.home-hero-carousel__arrow svg {
  width: 28px;
  height: 28px;
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
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
  z-index: var(--z-layer-3);
  right: 0;
  bottom: var(--space-5);
  left: 0;
  display: flex;
  justify-content: center;
  gap: var(--space-2);
  pointer-events: none;
}

.home-hero-carousel__indicator {
  width: 10px;
  height: 3px;
  border: 0;
  border-radius: 0;
  background: rgba(242, 240, 237, 0.35);
  pointer-events: auto;
  transition:
    width var(--transition-moderate),
    background var(--transition-moderate);
}

.home-hero-carousel__indicator--active {
  width: 26px;
  background: var(--color-primary);
}

@media (max-width: 768px) {
  .home-hero-carousel {
    border-radius: var(--radius-card);
  }

  .home-hero-slide {
    height: 400px;
  }

  .home-hero-slide__content {
    align-content: start;
    padding: var(--space-8) var(--space-5) var(--space-4);
  }

  .home-hero-slide__title {
    max-width: 420px;
    font-size: var(--font-size-2xl);
    line-height: var(--line-height-2xl);
  }

  .home-hero-slide__description {
    font-size: var(--font-size-button-small);
    line-height: var(--line-height-relaxed);
  }

  .home-hero-slide__cta {
    left: var(--space-5);
    min-height: 50px;
  }

  .home-hero-slide::before,
  .home-hero-slide--discover::before,
  .home-hero-slide--sell::before {
    background:
      linear-gradient(180deg, rgba(10, 10, 10, 0.85) 0%, rgba(10, 10, 10, 0.58) 54%, rgba(10, 10, 10, 0.16) 100%),
      linear-gradient(90deg, rgba(10, 10, 10, 0.44), transparent 70%);
  }

  .home-hero-carousel__arrow {
    display: none;
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

  // 좁은 화면에서는 3장만으로도 꽉 차서, 4번째는 겹침을 피하려 숨긴다.
  .home-hero-slide__collage-image--4 {
    display: none;
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
