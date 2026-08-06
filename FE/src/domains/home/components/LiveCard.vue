<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import fallbackImageUrl from '@/assets/images/products/product-denim-jacket.webp'
import type { HomeLiveCardItem } from '@/domains/home/types/homeView.types'
import type { RouteLocationRaw } from 'vue-router'

const props = withDefaults(
  defineProps<{
    live: HomeLiveCardItem
    variant?: 'live' | 'scheduled'
    to?: RouteLocationRaw
    actionTo?: RouteLocationRaw
    actionLabel?: string
  }>(),
  {
    variant: 'live',
    to: undefined,
    actionTo: undefined,
    actionLabel: undefined,
  },
)

const rootComponent = computed(() => (props.to ? RouterLink : 'article'))
const isScheduled = computed(() => props.variant === 'scheduled')
const rootProps = computed(() => (props.to ? { to: props.to } : {}))
const displayImageUrl = computed(() => props.live.thumbnailUrl || fallbackImageUrl)

const handleImageError = (event: Event) => {
  if (event.target instanceof HTMLImageElement) {
    event.target.onerror = null
    event.target.src = fallbackImageUrl
  }
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
</script>

<template>
  <component :is="rootComponent" class="live-card" v-bind="rootProps">
    <span class="live-card__media">
      <img
        class="live-card__image"
        :src="displayImageUrl"
        :alt="live.title"
        @error="handleImageError"
      />
      <template v-if="isScheduled">
        <span class="live-card__badge live-card__badge--scheduled">
          {{ formatSchedule(live.scheduledAt) }}
        </span>
      </template>
      <template v-else>
        <span class="live-card__badge">LIVE</span>
        <span v-if="live.viewerCount !== undefined" class="live-card__viewers">
          {{ live.viewerCount.toLocaleString('ko-KR') }}명
        </span>
      </template>
    </span>
    <span class="live-card__body">
      <strong class="live-card__title">{{ live.title }}</strong>
      <span class="live-card__meta">
        <template v-if="isScheduled">
          판매자 {{ live.hostName }} · 예정 상품 {{ live.scheduledProductCount ?? 0 }}개
        </template>
        <template v-else>판매자 {{ live.hostName }}</template>
      </span>
      <RouterLink v-if="actionTo && actionLabel" class="live-card__action" :to="actionTo">
        {{ actionLabel }}
      </RouterLink>
    </span>
  </component>
</template>

<style scoped lang="scss">
// 카드 자체는 박스(테두리/배경)를 두르지 않는다 — 페이지 배경과 자연스럽게 연결하고,
// 얇은 border는 이미지 프레임에만 준다. hover도 뜨는 대신 이미지/보더 대비만 미세하게 바뀐다.
// 진행 중/예약 라이브 카드는 같은 마크업·스타일을 쓰고, 배지 내용과 하단 액션 버튼 유무만 다르다.
.live-card {
  display: grid;
  gap: var(--space-3);
}

.live-card__media {
  position: relative;
  overflow: hidden;
  display: block;
  aspect-ratio: 4 / 3;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-media);
  background: var(--color-image-frame);
  transition: border-color var(--transition-standard);
}

.live-card:hover .live-card__media {
  border-color: var(--color-border-strong);
}

.live-card__media::after {
  position: absolute;
  inset: 0;
  background: linear-gradient(0deg, var(--overlay-scrim-medium), transparent 42%);
  content: '';
}

.live-card__image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  filter: saturate(0.88) contrast(1.04) brightness(0.95);
  transition: filter var(--transition-standard);
}

.live-card:hover .live-card__image {
  filter: saturate(0.88) contrast(1.04) brightness(1.03);
}

// 상품 카드 등급 뱃지(.product-card__grade)와 동일한 형태/위치 — 박스 안쪽으로 8px 들어온
// 둥근 뱃지, blur 배경. LIVE/예약 시각은 좌측, 시청자 수는 우측에 같은 모양으로 대칭 배치한다.
.live-card__badge,
.live-card__viewers {
  position: absolute;
  z-index: var(--z-layer-1);
  top: var(--space-2);
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px var(--space-2);
  border: 1px solid var(--color-border-strong);
  border-radius: 10px;
  color: var(--color-text-primary);
  font-size: calc(var(--font-size-caption) - 1px);
  font-weight: var(--font-weight-semibold);
  letter-spacing: 0.03em;
  line-height: var(--line-height-xs);
  backdrop-filter: blur(4px);
}

.live-card__badge {
  left: var(--space-2);
  background: var(--color-accent);
}

.live-card__badge--scheduled {
  background: var(--overlay-scrim-strong);
  letter-spacing: -0.01em;
}

.live-card__badge:not(.live-card__badge--scheduled)::before {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  content: '';
  animation: live-pulse var(--duration-pulse) ease-in-out infinite;
}

@keyframes live-pulse {
  0%,
  100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.35;
    transform: scale(0.7);
  }
}

.live-card__viewers {
  right: var(--space-2);
  background: var(--overlay-scrim-strong);
  color: var(--color-text-secondary);
}

.live-card__body {
  display: grid;
  gap: var(--space-1);
}

.live-card__title {
  display: -webkit-box;
  overflow: hidden;
  color: var(--color-text-primary);
  font-size: var(--font-size-body);
  font-weight: var(--font-weight-medium);
  line-height: var(--line-height-comfortable);
  letter-spacing: -0.01em;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.live-card__meta {
  color: var(--color-text-muted);
  font-size: var(--font-size-body);
  font-weight: var(--font-weight-regular);
  line-height: var(--line-height-snug);
}

.live-card__action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  align-self: flex-start;
  width: fit-content;
  height: var(--space-8);
  padding: 0 var(--space-3);
  margin-top: var(--space-1);
  border-radius: var(--radius-control);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
  line-height: var(--line-height-snug);
  transition:
    background-color var(--transition-standard),
    color var(--transition-standard);
}

.live-card__action:hover {
  background: var(--color-primary-hover);
  color: var(--color-primary-strong);
}

@media (max-width: 520px) {
  .live-card__title {
    font-size: var(--font-size-body);
    line-height: var(--line-height-relaxed);
  }
}
</style>
