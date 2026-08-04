<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

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
const fallbackImageUrl =
  'https://images.unsplash.com/photo-1496747611176-843222e1e57c?auto=format&fit=crop&w=900&q=80'

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
        :src="live.thumbnailUrl"
        :alt="live.title"
        @error="handleImageError"
      />
      <span v-if="isScheduled" class="schedule-card__time">
        {{ formatSchedule(live.scheduledAt) }}
      </span>
      <span v-else class="live-card__badge">LIVE</span>
    </span>
    <span :class="isScheduled ? 'schedule-card__body' : 'live-card__body'">
      <strong :class="isScheduled ? 'schedule-card__title' : 'live-card__title'">
        {{ live.title }}
      </strong>
      <span :class="isScheduled ? 'schedule-card__meta' : 'live-card__meta'">
        판매자 {{ live.hostName }}
      </span>
      <span
        :class="
          isScheduled
            ? 'schedule-card__meta schedule-card__meta--time'
            : 'live-card__meta live-card__meta--time'
        "
      >
        {{ isScheduled ? '예정 일자' : '시작 시간' }}
        {{ formatSchedule(isScheduled ? live.scheduledAt : live.startedAt) }}
      </span>
      <span v-if="isScheduled" class="schedule-card__meta">
        예정 상품 {{ live.scheduledProductCount ?? 0 }}개
      </span>
      <RouterLink v-if="actionTo && actionLabel" class="schedule-card__action" :to="actionTo">
        {{ actionLabel }}
      </RouterLink>
    </span>
  </component>
</template>

<style scoped lang="scss">
.live-card,
.schedule-card {
  position: relative;
  display: grid;
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
  transition:
    border-color 220ms ease,
    background-color 220ms ease,
    transform 620ms cubic-bezier(0.22, 1, 0.36, 1);
}

.live-card:hover,
.schedule-card:hover {
  border-color: var(--color-border-strong);
  transform: translateY(-3px);
}

.live-card:hover .live-card__image,
.schedule-card:hover .schedule-card__image {
  transform: scale(1.045);
}

.live-card__media,
.schedule-card__media {
  position: relative;
  display: block;
  overflow: hidden;
  aspect-ratio: 4 / 3;
  background: var(--color-image-frame);
}

.live-card__media::after,
.schedule-card__media::after {
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
  transition: transform 620ms cubic-bezier(0.22, 1, 0.36, 1);
}

.live-card__badge,
.schedule-card__time {
  position: absolute;
  z-index: 1;
  top: 0;
  left: 0;
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 10px;
  border-radius: 0 0 var(--radius-badge) 0;
  color: var(--color-text-primary);
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 500;
  letter-spacing: 0.12em;
  line-height: 18px;
}

.live-card__badge {
  gap: 6px;
  background: var(--color-accent);
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

.schedule-card__time {
  background: rgba(10, 10, 10, 0.82);
}

.live-card__body,
.schedule-card__body {
  display: grid;
  gap: var(--space-1);
  padding: var(--space-4);
  background: var(--color-surface);
}

.live-card__title,
.schedule-card__title {
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

.live-card__meta,
.schedule-card__meta {
  color: var(--color-text-muted);
  font-size: 12px;
  font-weight: 300;
  line-height: 18px;
}

.live-card__meta--time,
.schedule-card__meta--time {
  color: var(--color-text-secondary);
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: -0.01em;
  font-variant-numeric: tabular-nums;
}

.schedule-card__action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: fit-content;
  height: 36px;
  padding: 0 var(--space-4);
  justify-self: end;
  margin-top: var(--space-2);
  border-radius: var(--radius-control);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-size: 13px;
  font-weight: 500;
  line-height: 20px;
  transition:
    background-color 220ms ease,
    color 220ms ease;
}

.schedule-card__action:hover {
  background: var(--color-primary-hover);
  color: var(--color-primary-strong);
}

@media (max-width: 520px) {
  .live-card__title,
  .schedule-card__title {
    font-size: 15px;
    line-height: 22px;
  }
}
</style>
