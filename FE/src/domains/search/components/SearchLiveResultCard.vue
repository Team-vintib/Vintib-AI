<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import fallbackLiveThumbnail from '@/assets/images/products/product-denim-jacket.webp'
import { ROUTE_NAMES } from '@/shared/constants/routes'

import type { SearchLiveResult } from '@/domains/search/types/search.types'

const props = defineProps<{
  live: SearchLiveResult
}>()

const displayThumbnailUrl = computed(() => props.live.thumbnailUrl || fallbackLiveThumbnail)
const handleThumbnailError = (event: Event) => {
  const target = event.target

  if (target instanceof HTMLImageElement) {
    target.onerror = null
    target.src = fallbackLiveThumbnail
  }
}

const statusLabel = computed(() => {
  if (props.live.status === 'LIVE') {
    return 'LIVE'
  }

  if (props.live.status === 'SCHEDULED') {
    return '예정'
  }

  return '종료'
})

const statusClass = computed(() => ({
  'search-live-card__badge--live': props.live.status === 'LIVE',
  'search-live-card__badge--scheduled': props.live.status === 'SCHEDULED',
  'search-live-card__badge--ended': props.live.status === 'ENDED',
}))

const displayTime = computed(() => {
  const dateValue = props.live.startedAt ?? props.live.scheduledAt

  if (!dateValue) {
    return '일정 확인 필요'
  }

  return new Intl.DateTimeFormat('ko-KR', {
    month: 'long',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  }).format(new Date(dateValue))
})
</script>

<template>
  <article class="search-live-card">
    <RouterLink
      class="search-live-card__media"
      :to="{ name: ROUTE_NAMES.LIVE_WATCH, params: { liveId: live.id } }"
    >
      <img
        class="search-live-card__image"
        :src="displayThumbnailUrl"
        :alt="live.title"
        @error="handleThumbnailError"
      />
      <span class="search-live-card__badge" :class="statusClass">{{ statusLabel }}</span>
    </RouterLink>

    <div class="search-live-card__body">
      <RouterLink
        class="search-live-card__title"
        :to="{ name: ROUTE_NAMES.LIVE_WATCH, params: { liveId: live.id } }"
      >
        {{ live.title }}
      </RouterLink>
      <p class="search-live-card__meta">판매자 {{ live.hostName }}</p>
      <p class="search-live-card__meta">{{ displayTime }} · 상품 {{ live.productCount }}개</p>
    </div>
  </article>
</template>

<style scoped lang="scss">
.search-live-card {
  display: grid;
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
  transition:
    border-color 160ms ease,
    transform 160ms ease;
}

.search-live-card:hover {
  border-color: var(--color-border-strong);
  transform: translateY(-2px);
}

.search-live-card__media {
  position: relative;
  overflow: hidden;
  aspect-ratio: 16 / 9;
  background: var(--color-surface-secondary);
}

.search-live-card__media:focus-visible,
.search-live-card__title:focus-visible {
  outline: 1px solid var(--color-primary);
  outline-offset: 2px;
}

.search-live-card__image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.search-live-card__badge {
  position: absolute;
  top: var(--space-3);
  left: var(--space-3);
  min-height: 28px;
  padding: 4px 10px;
  border-radius: var(--radius-badge);
  color: var(--color-text-inverse);
  font-size: 12px;
  font-weight: 800;
  line-height: 18px;
}

.search-live-card__badge--live {
  background: var(--color-live);
}

.search-live-card__badge--scheduled {
  background: var(--color-primary);
}

.search-live-card__badge--ended {
  background: var(--color-text-muted);
}

.search-live-card__body {
  display: grid;
  gap: var(--space-2);
  padding: var(--space-4);
}

.search-live-card__title {
  display: -webkit-box;
  overflow: hidden;
  color: var(--color-text-primary);
  font-size: 17px;
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-body);
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.search-live-card__meta {
  color: var(--color-text-secondary);
  font-size: var(--font-size-caption);
  line-height: 20px;
}
</style>
