<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import { ROUTE_NAMES } from '@/shared/constants/routes'

import type { LiveListItem } from '@/domains/live/types/liveList.types'

const props = defineProps<{
  live: LiveListItem
}>()

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
  'live-list-card__badge--live': props.live.status === 'LIVE',
  'live-list-card__badge--scheduled': props.live.status === 'SCHEDULED',
  'live-list-card__badge--ended': props.live.status === 'ENDED',
}))

const broadcastLabel = computed(() => {
  const formattedDate = new Intl.DateTimeFormat('ko-KR', {
    month: 'long',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  }).format(new Date(props.live.broadcastAt))

  if (props.live.status === 'LIVE') {
    return `${formattedDate} 시작`
  }

  if (props.live.status === 'SCHEDULED') {
    return `${formattedDate} 예정`
  }

  return `${formattedDate} 종료`
})
</script>

<template>
  <RouterLink
    class="live-list-card"
    :to="{ name: ROUTE_NAMES.LIVE_WATCH, params: { liveId: live.id } }"
    :aria-label="`${live.title}, ${statusLabel} 방송 보기`"
  >
    <span class="live-list-card__media">
      <img class="live-list-card__image" :src="live.thumbnailUrl" :alt="`${live.title} 썸네일`" />
      <span class="live-list-card__badge" :class="statusClass">
        {{ statusLabel }}
      </span>
    </span>

    <span class="live-list-card__body">
      <strong class="live-list-card__title">{{ live.title }}</strong>
      <span class="live-list-card__seller">판매자 {{ live.sellerName }}</span>
      <span class="live-list-card__meta">{{ broadcastLabel }}</span>
      <span class="live-list-card__viewer">
        <span aria-hidden="true">●</span>
        시청자 {{ live.viewerCount.toLocaleString('ko-KR') }}명
      </span>
    </span>
  </RouterLink>
</template>

<style scoped lang="scss">
.live-list-card {
  display: grid;
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: 20px;
  background: var(--color-surface);
  box-shadow: 0 8px 24px rgb(18 18 18 / 5%);
  transition:
    border-color 160ms ease,
    box-shadow 160ms ease,
    transform 160ms ease;
}

.live-list-card:hover {
  border-color: var(--color-border-strong);
  box-shadow: 0 10px 26px rgb(18 18 18 / 8%);
  transform: translateY(-2px);
}

.live-list-card:focus-visible {
  outline: 3px solid var(--color-primary);
  outline-offset: 4px;
}

.live-list-card__media {
  position: relative;
  display: block;
  overflow: hidden;
  aspect-ratio: 16 / 9;
  background: var(--color-surface-secondary);
}

.live-list-card__image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 220ms ease;
}

.live-list-card:hover .live-list-card__image {
  transform: scale(1.02);
}

.live-list-card__badge {
  position: absolute;
  top: var(--space-3);
  left: var(--space-3);
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 4px 10px;
  border-radius: var(--radius-badge);
  color: var(--color-text-inverse);
  font-size: 12px;
  font-weight: 800;
  line-height: 18px;
}

.live-list-card__badge--live {
  gap: 6px;
  background: var(--color-live);
}

.live-list-card__badge--live::before {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  content: '';
}

.live-list-card__badge--scheduled {
  background: var(--color-primary);
}

.live-list-card__badge--ended {
  background: var(--color-text-secondary);
}

.live-list-card__body {
  display: grid;
  gap: var(--space-2);
  padding: var(--space-5);
}

.live-list-card__title {
  display: -webkit-box;
  overflow: hidden;
  color: var(--color-text-primary);
  font-size: 18px;
  font-weight: 700;
  line-height: 26px;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.live-list-card__seller,
.live-list-card__meta,
.live-list-card__viewer {
  color: var(--color-text-secondary);
  font-size: 13px;
  line-height: 20px;
}

.live-list-card__seller {
  font-weight: 600;
}

.live-list-card__viewer {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: var(--color-text-primary);
  font-weight: 600;
}

.live-list-card__viewer span {
  color: var(--color-live);
  font-size: 8px;
}

@media (max-width: 640px) {
  .live-list-card__body {
    padding: var(--space-4);
  }

  .live-list-card__title {
    font-size: 16px;
    line-height: 24px;
  }
}
</style>
