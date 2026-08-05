<script setup lang="ts">
import { computed } from 'vue'

import type { LiveWatchViewData } from '@/domains/live/types/liveWatch.types'

const props = defineProps<{
  live: LiveWatchViewData
  elapsedTime: string
}>()

defineEmits<{
  back: []
  endBroadcast: []
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
      : `${props.live.currentViewerCount.toLocaleString('ko-KR')}명 시청 중`
  }

  if (props.live.status === 'ENDED') {
    return `최고 ${props.live.peakViewerCount.toLocaleString('ko-KR')}명`
  }

  return props.live.status === 'SCHEDULED' ? '방송 시작 전' : '방송이 취소되었습니다'
})

const isLive = computed(() => props.live.status === 'LIVE')
</script>

<template>
  <header class="live-broadcast-header">
    <button
      class="live-broadcast-header__back"
      type="button"
      aria-label="방송 화면 나가기"
      @click="$emit('back')"
    >
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="m15 18-6-6 6-6" />
      </svg>
    </button>

    <span
      class="live-broadcast-header__status"
      :class="`live-broadcast-header__status--${live.status.toLowerCase()}`"
    >
      <span v-if="isLive" aria-hidden="true"></span>
      {{ statusLabel }}
    </span>

    <span class="live-broadcast-header__role">판매자</span>

    <div class="live-broadcast-header__identity">
      <h1>{{ live.title }}</h1>
    </div>

    <div class="live-broadcast-header__meta">
      <span class="live-broadcast-header__meta-item">
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
          <circle cx="9" cy="7" r="4" />
          <path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
        </svg>
        {{ audienceLabel }}
      </span>
      <span class="live-broadcast-header__meta-item">
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="12" cy="12" r="9" />
          <path d="M12 7v5l3 2" />
        </svg>
        {{ elapsedTime }}
      </span>
    </div>

    <!-- 방송 종료 동작은 437(상품 전환·종료 버튼)에서 연결. 지금은 자리와 이벤트만. -->
    <button
      class="live-broadcast-header__end"
      type="button"
      :disabled="!isLive"
      @click="$emit('endBroadcast')"
    >
      <span aria-hidden="true"></span>
      방송 종료
    </button>
  </header>
</template>

<style scoped lang="scss">
.live-broadcast-header {
  display: flex;
  position: relative;
  z-index: var(--z-layer-header);
  align-items: center;
  min-height: var(--button-height-major);
  padding: 0 var(--space-4);
  border-bottom: 1px solid var(--color-live-border);
  background: var(--color-live-background);
  gap: var(--space-3);
}

.live-broadcast-header__back {
  display: grid;
  flex: 0 0 auto;
  width: 36px;
  height: var(--button-height-small);
  border: 0;
  border-radius: var(--radius-control);
  background: transparent;
  color: var(--color-live-text-secondary);
  place-items: center;
}

.live-broadcast-header__back:hover {
  background: var(--color-live-surface-raised);
  color: var(--color-live-text-primary);
}

.live-broadcast-header__back svg {
  width: var(--icon-size-md);
  height: var(--icon-size-md);
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 2;
}

.live-broadcast-header__status {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  min-height: var(--badge-height-sm);
  padding: 0 9px;
  border-radius: var(--radius-badge);
  background: var(--color-live-surface-raised);
  color: var(--color-live-text-secondary);
  font-size: var(--font-size-2xs);
  font-weight: var(--font-weight-extrabold);
  letter-spacing: 0.04em;
}

.live-broadcast-header__status--live {
  background: var(--color-live);
  color: var(--color-text-inverse);
  gap: 5px;
}

.live-broadcast-header__status--live span {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: currentColor;
}

.live-broadcast-header__role {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  min-height: var(--badge-height-xs);
  padding: 0 8px;
  border: 1px solid var(--color-live-border);
  border-radius: var(--radius-badge);
  color: var(--color-live-text-secondary);
  font-size: var(--font-size-badge);
  font-weight: var(--font-weight-bold);
  letter-spacing: 0.04em;
}

.live-broadcast-header__identity {
  display: flex;
  align-items: baseline;
  min-width: 0;
  gap: 6px;
}

.live-broadcast-header__identity h1 {
  overflow: hidden;
  color: var(--color-live-text-primary);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-control);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.live-broadcast-header__meta {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  margin-left: auto;
  gap: var(--space-4);
  color: var(--color-live-text-secondary);
}

.live-broadcast-header__meta-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: var(--font-size-xs);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.live-broadcast-header__meta-item svg {
  width: var(--icon-size-xs);
  height: var(--icon-size-xs);
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.7;
}

.live-broadcast-header__end {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  min-height: var(--button-height-2xs);
  padding: 0 var(--space-4);
  border: 1px solid color-mix(in srgb, var(--color-error) 55%, transparent);
  border-radius: var(--radius-control);
  background: color-mix(in srgb, var(--color-error) 16%, transparent);
  gap: 6px;
  color: var(--color-error);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-bold);
}

.live-broadcast-header__end span {
  width: 8px;
  height: 8px;
  border-radius: 2px;
  background: currentColor;
}

.live-broadcast-header__end:hover:not(:disabled) {
  background: color-mix(in srgb, var(--color-error) 26%, transparent);
}

.live-broadcast-header__end:disabled {
  border-color: var(--color-live-border);
  background: transparent;
  color: var(--color-live-text-secondary);
  opacity: 0.6;
}

.live-broadcast-header__back:focus-visible,
.live-broadcast-header__end:focus-visible {
  outline: var(--focus-ring-width) solid var(--color-ai);
  outline-offset: 2px;
}

@media (max-width: 900px) {
  .live-broadcast-header__meta-item:last-child {
    display: none;
  }
}

@media (max-width: 680px) {
  .live-broadcast-header {
    flex-wrap: wrap;
    padding-top: var(--space-2);
    padding-bottom: var(--space-2);
  }

  .live-broadcast-header__identity {
    flex: 1 1 100%;
    order: 5;
  }

  .live-broadcast-header__meta {
    margin-left: 0;
  }
}
</style>
