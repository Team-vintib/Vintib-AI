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
  border-radius: 20px;
  background: var(--color-surface);
  box-shadow: 0 8px 24px color-mix(in srgb, var(--color-text-primary) 5%, transparent);
  transition:
    border-color 160ms ease,
    box-shadow 160ms ease,
    transform 160ms ease;
}

.live-card:hover,
.schedule-card:hover {
  border-color: var(--color-border-strong);
  box-shadow: 0 10px 26px color-mix(in srgb, var(--color-text-primary) 7%, transparent);
  transform: translateY(-2px);
}

.live-card__media,
.schedule-card__media {
  position: relative;
  display: block;
  overflow: hidden;
  aspect-ratio: 16 / 9;
  background: var(--color-surface-secondary);
}

.live-card__image,
.schedule-card__image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.live-card__badge,
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
  color: var(--color-text-inverse);
  font-size: 12px;
  font-weight: 700;
  line-height: 18px;
}

.live-card__badge {
  gap: 6px;
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
  background: rgba(14, 17, 16, 0.66);
}

.live-card__body,
.schedule-card__body {
  display: grid;
  gap: var(--space-2);
  padding: var(--space-5);
  background: var(--color-surface);
}

.live-card__title,
.schedule-card__title {
  display: -webkit-box;
  overflow: hidden;
  color: var(--color-text-primary);
  font-size: 18px;
  font-weight: 700;
  line-height: 26px;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.live-card__meta,
.schedule-card__meta {
  color: var(--color-text-muted);
  font-size: 13px;
  font-weight: 400;
  line-height: 20px;
}

.live-card__meta--time,
.schedule-card__meta--time {
  color: var(--color-text-secondary);
  font-weight: 500;
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

@media (max-width: 520px) {
  .live-card__title,
  .schedule-card__title {
    font-size: 15px;
    line-height: 22px;
  }
}
</style>
