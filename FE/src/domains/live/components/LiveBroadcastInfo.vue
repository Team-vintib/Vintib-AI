<script setup lang="ts">
import { computed } from 'vue'

import type { LiveWatchViewData } from '@/domains/live/types/liveWatch.types'

const props = defineProps<{
  live: LiveWatchViewData
  elapsedTime: string
}>()

const statusLabel = computed(() => {
  if (props.live.status === 'LIVE') return '방송 중'
  if (props.live.status === 'SCHEDULED') return '방송 예정'
  if (props.live.status === 'ENDED') return '방송 종료'
  return '방송 취소'
})

const currentViewerLabel = computed(() =>
  props.live.currentViewerCount === null
    ? '집계 준비 중'
    : `${props.live.currentViewerCount.toLocaleString('ko-KR')}명`,
)

const peakViewerLabel = computed(
  () => `${props.live.peakViewerCount.toLocaleString('ko-KR')}명`,
)

const productCountLabel = computed(() => `${props.live.products.length}개`)
</script>

<template>
  <section class="live-broadcast-info" aria-label="방송 정보">
    <div class="live-broadcast-info__header">
      <h2>방송 정보</h2>
      <span
        class="live-broadcast-info__status"
        :class="`live-broadcast-info__status--${live.status.toLowerCase()}`"
      >
        {{ statusLabel }}
      </span>
    </div>

    <p v-if="live.description" class="live-broadcast-info__description">
      {{ live.description }}
    </p>

    <dl class="live-broadcast-info__meta">
      <div>
        <dt>진행 시간</dt>
        <dd>{{ elapsedTime }}</dd>
      </div>
      <div>
        <dt>현재 시청자</dt>
        <dd>{{ currentViewerLabel }}</dd>
      </div>
      <div>
        <dt>최고 시청자</dt>
        <dd>{{ peakViewerLabel }}</dd>
      </div>
      <div>
        <dt>연결 상품</dt>
        <dd>{{ productCountLabel }}</dd>
      </div>
    </dl>

    <div v-if="live.categories.length" class="live-broadcast-info__categories">
      <span v-for="category in live.categories" :key="category.id">
        {{ category.name }}
      </span>
    </div>
  </section>
</template>

<style scoped lang="scss">
.live-broadcast-info {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-4);
  border: 1px solid var(--color-live-border);
  border-radius: var(--radius-control);
  background: var(--color-live-surface);
}

.live-broadcast-info__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.live-broadcast-info__header h2 {
  color: var(--color-live-text-primary);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-bold);
}

.live-broadcast-info__status {
  display: inline-flex;
  align-items: center;
  min-height: var(--badge-height-xs);
  padding: 0 8px;
  border-radius: var(--radius-badge);
  background: var(--color-live-surface-raised);
  color: var(--color-live-text-secondary);
  font-size: var(--font-size-badge);
  font-weight: var(--font-weight-bold);
}

.live-broadcast-info__status--live {
  background: var(--color-live);
  color: var(--color-text-inverse);
}

.live-broadcast-info__description {
  color: var(--color-live-text-secondary);
  font-size: var(--font-size-xs);
  line-height: var(--line-height-snug);
}

.live-broadcast-info__meta {
  display: grid;
  gap: var(--space-2);
}

.live-broadcast-info__meta div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}

.live-broadcast-info__meta dt {
  color: var(--color-live-text-secondary);
  font-size: var(--font-size-2xs);
}

.live-broadcast-info__meta dd {
  color: var(--color-live-text-primary);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-bold);
  font-variant-numeric: tabular-nums;
}

.live-broadcast-info__categories {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.live-broadcast-info__categories span {
  display: inline-flex;
  align-items: center;
  min-height: var(--badge-height-xs);
  padding: 0 8px;
  border: 1px solid var(--color-live-border);
  border-radius: var(--radius-badge);
  color: var(--color-live-text-secondary);
  font-size: var(--font-size-badge);
  font-weight: var(--font-weight-semibold);
}
</style>
