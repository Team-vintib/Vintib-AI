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
const rootClass = computed(() => (isScheduled.value ? 'schedule-card' : 'live-card'))
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
  <component :is="rootComponent" :class="rootClass" v-bind="rootProps">
    <span :class="isScheduled ? 'schedule-card__media' : 'live-card__media'">
      <img
        :class="isScheduled ? 'schedule-card__image' : 'live-card__image'"
        :src="displayImageUrl"
        :alt="live.title"
        @error="handleImageError"
      />
      <span v-if="isScheduled" class="schedule-card__time">
        {{ formatSchedule(live.scheduledAt) }}
      </span>
      <template v-else>
        <span class="live-card__badge">LIVE</span>
        <span v-if="live.viewerCount !== undefined" class="live-card__viewers">
          {{ live.viewerCount.toLocaleString('ko-KR') }}명
        </span>
      </template>
    </span>
    <span v-if="isScheduled" class="schedule-card__body">
      <span class="schedule-card__row">
        <strong class="schedule-card__title">{{ live.title }}</strong>
        <span class="schedule-card__time-text">{{ formatSchedule(live.scheduledAt) }}</span>
      </span>
      <span class="schedule-card__meta">
        판매자 {{ live.hostName }} · 예정 상품 {{ live.scheduledProductCount ?? 0 }}개
      </span>
      <RouterLink v-if="actionTo && actionLabel" class="schedule-card__action" :to="actionTo">
        {{ actionLabel }}
      </RouterLink>
    </span>
    <span v-else class="live-card__body">
      <strong class="live-card__title">{{ live.title }}</strong>
      <span class="live-card__meta">판매자 {{ live.hostName }}</span>
    </span>
  </component>
</template>

<style scoped lang="scss">
// 카드 자체는 박스(테두리/배경)를 두르지 않는다 — 페이지 배경과 자연스럽게 연결하고,
// 얇은 border는 이미지 프레임에만 준다. hover도 뜨는 대신 이미지/보더 대비만 미세하게 바뀐다.
.live-card {
  display: grid;
  gap: var(--space-3);
}

.schedule-card {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.live-card__media,
.schedule-card__media {
  position: relative;
  overflow: hidden;
  display: block;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-media);
  background: var(--color-image-frame);
  transition: border-color 220ms ease;
}

.live-card__media {
  aspect-ratio: 4 / 3;
}

.schedule-card__media {
  flex: 0 0 96px;
  aspect-ratio: 1 / 1;
}

.live-card:hover .live-card__media,
.schedule-card:hover .schedule-card__media {
  border-color: var(--color-border-strong);
}

.live-card__media::after {
  position: absolute;
  inset: 0;
  background: linear-gradient(0deg, rgba(10, 10, 10, 0.55), transparent 42%);
  content: '';
}

.live-card__image,
.schedule-card__image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  filter: saturate(0.88) contrast(1.04) brightness(0.95);
  transition: filter 220ms ease;
}

.live-card:hover .live-card__image,
.schedule-card:hover .schedule-card__image {
  filter: saturate(0.88) contrast(1.04) brightness(1.03);
}

.live-card__badge,
.live-card__viewers,
.schedule-card__time {
  position: absolute;
  z-index: 1;
  top: 0;
  display: inline-flex;
  align-items: center;
  min-height: 22px;
  padding: 0 8px;
  color: var(--color-text-primary);
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 500;
  letter-spacing: 0.12em;
  line-height: 16px;
}

.live-card__badge {
  left: 0;
  gap: 6px;
  background: var(--color-accent);
  border-radius: 0 0 var(--radius-badge) 0;
  letter-spacing: 0.18em;
}

.live-card__badge::before {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  content: '';
  animation: live-pulse 1.7s ease-in-out infinite;
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
  right: 0;
  background: rgba(10, 10, 10, 0.82);
  border-radius: 0 0 0 var(--radius-badge);
  color: var(--color-text-secondary);
  letter-spacing: -0.01em;
  text-transform: none;
}

.schedule-card__time {
  left: 0;
  background: rgba(10, 10, 10, 0.82);
  border-radius: 0 0 var(--radius-badge) 0;
}

.live-card__body {
  display: grid;
  gap: var(--space-1);
}

.schedule-card__body {
  display: grid;
  flex: 1 1 auto;
  gap: var(--space-1);
  min-width: 0;
}

.live-card__title {
  display: -webkit-box;
  overflow: hidden;
  color: var(--color-text-primary);
  font-size: 15px;
  font-weight: 500;
  line-height: 21px;
  letter-spacing: -0.01em;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.schedule-card__row {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
}

.schedule-card__title {
  overflow: hidden;
  min-width: 0;
  color: var(--color-text-primary);
  font-size: 14px;
  font-weight: 500;
  letter-spacing: -0.01em;
  line-height: 20px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.schedule-card__time-text {
  flex: 0 0 auto;
  color: var(--color-text-secondary);
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: -0.01em;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}

.live-card__meta,
.schedule-card__meta {
  color: var(--color-text-muted);
  font-size: 12px;
  font-weight: 300;
  line-height: 18px;
}

.schedule-card__action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  align-self: flex-start;
  width: fit-content;
  height: 32px;
  padding: 0 var(--space-3);
  margin-top: var(--space-1);
  border-radius: var(--radius-control);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-size: 12px;
  font-weight: 500;
  line-height: 18px;
  transition:
    background-color 220ms ease,
    color 220ms ease;
}

.schedule-card__action:hover {
  background: var(--color-primary-hover);
  color: var(--color-primary-strong);
}

@media (max-width: 520px) {
  .live-card__title {
    font-size: 15px;
    line-height: 22px;
  }

  .schedule-card__media {
    flex-basis: 76px;
  }
}
</style>
