<script setup lang="ts">
import { computed } from 'vue'

import type { LiveWatchViewData } from '@/domains/live/types/liveWatch.types'

const props = defineProps<{
  live: LiveWatchViewData
  elapsedTime: string
  isFollowing: boolean
}>()

defineEmits<{
  back: []
  toggleFollow: []
}>()

const statusLabel = computed(() => {
  if (props.live.status === 'LIVE') return 'LIVE'
  if (props.live.status === 'SCHEDULED') return '예정'
  if (props.live.status === 'ENDED') return '종료'
  return '취소'
})

const audienceLabel = computed(() => {
  if (props.live.status === 'LIVE') {
    return props.live.currentViewerCount === null
      ? '시청자 집계 준비 중'
      : props.live.currentViewerCount.toLocaleString('ko-KR')
  }

  if (props.live.status === 'ENDED') {
    return `최고 ${props.live.peakViewerCount.toLocaleString('ko-KR')}명`
  }

  return props.live.status === 'SCHEDULED' ? '방송 시작 전' : '방송이 취소되었습니다'
})
</script>

<template>
  <header class="live-watch-header">
    <button class="live-watch-header__back" type="button" aria-label="이전 화면으로" @click="$emit('back')">
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="m15 18-6-6 6-6" />
      </svg>
    </button>

    <span
      class="live-watch-header__status"
      :class="`live-watch-header__status--${live.status.toLowerCase()}`"
    >
      <span v-if="live.status === 'LIVE'" aria-hidden="true"></span>
      {{ statusLabel }}
    </span>

    <div class="live-watch-header__identity">
      <span class="live-watch-header__avatar" aria-hidden="true">
        <img v-if="live.hostProfileImageUrl" :src="live.hostProfileImageUrl" alt="" />
        <template v-else>{{ live.hostNickname.charAt(0) }}</template>
      </span>
      <strong>{{ live.hostNickname }}</strong>
      <span aria-hidden="true">—</span>
      <h1 :title="live.description || undefined">{{ live.title }}</h1>
    </div>

    <div class="live-watch-header__meta">
      <span class="live-watch-header__meta-item">
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
          <circle cx="9" cy="7" r="4" />
          <path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
        </svg>
        {{ audienceLabel }}
      </span>
      <span class="live-watch-header__meta-item">
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="12" cy="12" r="9" />
          <path d="M12 7v5l3 2" />
        </svg>
        {{ elapsedTime }}
      </span>
    </div>

    <button
      v-if="!live.isHost"
      class="live-watch-header__follow"
      :class="{ 'live-watch-header__follow--active': isFollowing }"
      type="button"
      :aria-pressed="isFollowing"
      @click="$emit('toggleFollow')"
    >
      {{ isFollowing ? '팔로잉' : '팔로우' }}
    </button>
  </header>
</template>

<style scoped lang="scss">
.live-watch-header {
  display: flex;
  position: relative;
  z-index: 10;
  align-items: center;
  min-height: 52px;
  padding: 0 var(--space-4);
  border-bottom: 1px solid var(--color-live-border);
  background: var(--color-live-background);
  gap: var(--space-3);
}

.live-watch-header__back {
  display: grid;
  flex: 0 0 auto;
  width: 36px;
  height: 36px;
  border: 0;
  border-radius: var(--radius-control);
  background: transparent;
  color: var(--color-live-text-secondary);
  place-items: center;
}

.live-watch-header__back:hover {
  background: var(--color-live-surface-raised);
  color: var(--color-live-text-primary);
}

.live-watch-header__back svg {
  width: 20px;
  height: 20px;
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 2;
}

.live-watch-header__status {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  min-height: 26px;
  padding: 0 9px;
  border-radius: var(--radius-badge);
  background: var(--color-live-surface-raised);
  color: var(--color-live-text-secondary);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.04em;
}

.live-watch-header__status--live {
  background: var(--color-live);
  color: var(--color-text-inverse);
  gap: 5px;
}

.live-watch-header__status--live span {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: currentColor;
}

.live-watch-header__identity {
  display: flex;
  align-items: baseline;
  min-width: 0;
  gap: 6px;
}

.live-watch-header__avatar {
  display: inline-flex;
  flex: 0 0 auto;
  align-self: center;
  width: 28px;
  height: 28px;
  overflow: hidden;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--color-live-surface-raised);
  color: var(--color-live-text-primary);
  font-size: 12px;
  font-weight: 700;
}

.live-watch-header__avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.live-watch-header__identity strong,
.live-watch-header__identity h1 {
  overflow: hidden;
  font-size: 14px;
  font-weight: 700;
  line-height: 20px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.live-watch-header__identity strong {
  flex: 0 1 auto;
}

.live-watch-header__identity h1 {
  color: var(--color-live-text-secondary);
}

.live-watch-header__identity > span {
  color: var(--color-live-border);
}

.live-watch-header__meta {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  margin-left: auto;
  gap: var(--space-4);
  color: var(--color-live-text-secondary);
}

.live-watch-header__meta-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.live-watch-header__meta-item svg {
  width: 15px;
  height: 15px;
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.7;
}

.live-watch-header__follow {
  flex: 0 0 auto;
  min-width: 70px;
  min-height: 34px;
  padding: 0 var(--space-4);
  border: 1px solid var(--color-live-border);
  border-radius: var(--radius-control);
  background: transparent;
  color: var(--color-live-text-primary);
  font-size: 12px;
  font-weight: 700;
}

.live-watch-header__follow:hover,
.live-watch-header__follow--active {
  border-color: var(--color-primary-soft);
  background: var(--color-primary);
}

.live-watch-header__back:focus-visible,
.live-watch-header__follow:focus-visible {
  outline: 3px solid var(--color-ai);
  outline-offset: 2px;
}

@media (max-width: 900px) {
  .live-watch-header__meta-item:first-child {
    display: none;
  }
}

@media (max-width: 680px) {
  .live-watch-header {
    flex-wrap: wrap;
    padding-top: var(--space-2);
    padding-bottom: var(--space-2);
  }

  .live-watch-header__identity {
    flex: 1 1 calc(100% - 144px);
  }

  .live-watch-header__meta {
    order: 4;
    width: 100%;
    margin-left: 48px;
  }
}
</style>
