<script setup lang="ts">
import { computed } from 'vue'

import type {
  LiveWatchProduct,
  LiveWatchStatus,
} from '@/domains/live/types/liveWatch.types'

const props = defineProps<{
  product: LiveWatchProduct | null
  status: LiveWatchStatus
}>()

const statusMessage = computed(() => {
  if (props.status === 'SCHEDULED') return '방송이 시작되면 경매 상태를 확인할 수 있습니다.'
  if (props.status === 'ENDED') return '종료된 경매입니다.'
  if (!props.product) return '현재 연결된 상품이 없습니다.'
  return '경매 정보 연결 준비 중'
})
</script>

<template>
  <aside class="live-watch-side-panel" aria-label="실시간 경매 패널 영역">
    <h2>실시간 경매</h2>

    <div class="live-watch-side-panel__placeholder" role="status">
      <span aria-hidden="true"></span>
      <div>
        <strong>{{ statusMessage }}</strong>
        <p>{{ product?.title || '선택된 상품 없음' }}</p>
      </div>
    </div>
  </aside>
</template>

<style scoped lang="scss">
.live-watch-side-panel {
  display: grid;
  min-width: 0;
  min-height: 0;
  padding: 15px 15px 15px 14px;
  border-top: 1px solid var(--color-live-border);
  border-left: 1px solid var(--color-live-border);
  background: var(--color-live-background);
  grid-template-rows: 15px minmax(0, 1fr);
  row-gap: 10px;
}

.live-watch-side-panel h2 {
  color: var(--color-live-text-secondary);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.04em;
  line-height: 15px;
  text-transform: uppercase;
}

.live-watch-side-panel__placeholder {
  display: flex;
  align-items: center;
  min-width: 0;
  padding: var(--space-3);
  border: 1px dashed var(--color-live-border);
  border-radius: var(--radius-control);
  background: var(--color-live-surface);
  gap: var(--space-3);
  color: var(--color-live-text-secondary);
}

.live-watch-side-panel__placeholder > span {
  flex: 0 0 auto;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--color-auction);
}

.live-watch-side-panel__placeholder > div {
  min-width: 0;
}

.live-watch-side-panel__placeholder strong {
  display: block;
  color: var(--color-live-text-primary);
  font-size: 11px;
}

.live-watch-side-panel__placeholder p {
  overflow: hidden;
  margin-top: 3px;
  font-size: 10px;
  line-height: 15px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 720px) {
  .live-watch-side-panel {
    min-height: 132px;
    border-left: 0;
  }
}
</style>
