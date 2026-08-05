<script setup lang="ts">
import type { LiveAuctionMockState } from '@/domains/auction/types/liveAuction.types'
import type {
  LiveWatchProduct,
  LiveWatchStatus,
} from '@/domains/live/types/liveWatch.types'

defineProps<{
  product: LiveWatchProduct | null
  status: LiveWatchStatus
  mockState?: LiveAuctionMockState
}>()
</script>

<template>
  <aside class="live-auction-panel" aria-labelledby="live-auction-title">
    <h2 id="live-auction-title">실시간 경매</h2>

    <div class="live-auction-panel__empty">
      <strong>경매 정보가 없습니다.</strong>
      <p>입찰/낙찰 API가 연결되면 이 영역에 실제 경매 상태가 표시됩니다.</p>
    </div>
  </aside>
</template>

<style scoped lang="scss">
.live-auction-panel {
  display: grid;
  min-width: 0;
  min-height: 0;
  padding: 26px 28px;
  border-top: 1px solid var(--color-live-border);
  border-left: 1px solid var(--color-live-border);
  background: var(--color-surface-raised);
  grid-template-rows: auto 1fr;
  row-gap: var(--space-3);
}

.live-auction-panel h2 {
  color: var(--color-accent);
  font-family: var(--font-mono);
  font-size: var(--font-size-badge);
  font-weight: var(--font-weight-regular);
  letter-spacing: 0.2em;
  line-height: var(--line-height-tight);
  text-transform: uppercase;
}

.live-auction-panel__empty {
  display: grid;
  min-height: 88px;
  align-content: center;
  gap: var(--space-1);
  color: var(--color-live-text-secondary);
  font-size: var(--font-size-xs);
  line-height: 1.5;
}

.live-auction-panel__empty strong {
  color: var(--color-live-text-primary);
  font-size: var(--font-size-caption);
}

.live-auction-panel__empty p {
  margin: 0;
}
</style>
