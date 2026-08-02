<script setup lang="ts">
import type { LiveWatchProduct } from '@/domains/live/types/liveWatch.types'
import type { LiveTryOnMockScenario } from '@/domains/tryon/types/liveTryOn.types'

defineProps<{
  product: LiveWatchProduct
  mockScenario?: LiveTryOnMockScenario
}>()

const emit = defineEmits<{
  close: []
}>()
</script>

<template>
  <aside class="live-try-on-panel" aria-labelledby="live-try-on-title">
    <header class="live-try-on-panel__header">
      <div>
        <h2 id="live-try-on-title">AI 시착</h2>
        <p>{{ product.title }}</p>
      </div>
      <button type="button" class="live-try-on-panel__close" aria-label="AI 시착 패널 닫기" @click="emit('close')">
        ×
      </button>
    </header>

    <div class="live-try-on-panel__empty">
      <strong>AI 시착 정보가 없습니다.</strong>
      <p>사용자 시착 프로필과 생성 API가 연결되면 실제 결과가 표시됩니다.</p>
    </div>
  </aside>
</template>

<style scoped lang="scss">
.live-try-on-panel {
  display: grid;
  min-width: 0;
  min-height: 0;
  grid-template-rows: auto 1fr;
  border-left: 1px solid var(--color-live-border);
  background: var(--color-live-surface);
  color: var(--color-live-text-primary);
}

.live-try-on-panel__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-4);
  border-bottom: 1px solid var(--color-live-border);
}

.live-try-on-panel__header h2 {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
}

.live-try-on-panel__header p {
  margin: var(--space-1) 0 0;
  color: var(--color-live-text-secondary);
  font-size: 12px;
}

.live-try-on-panel__close {
  display: inline-grid;
  width: 28px;
  height: 28px;
  place-items: center;
  border: 1px solid var(--color-live-border);
  border-radius: var(--radius-control);
  background: transparent;
  color: var(--color-live-text-primary);
  cursor: pointer;
  font-size: 18px;
}

.live-try-on-panel__empty {
  display: grid;
  align-content: center;
  gap: var(--space-2);
  padding: var(--space-5);
  color: var(--color-live-text-secondary);
  font-size: 13px;
  line-height: 1.5;
}

.live-try-on-panel__empty strong {
  color: var(--color-live-text-primary);
  font-size: 14px;
}

.live-try-on-panel__empty p {
  margin: 0;
}
</style>
