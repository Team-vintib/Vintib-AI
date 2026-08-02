<script setup lang="ts">
import { computed } from 'vue'

import type { BroadcastEndSummary } from '@/domains/live/constants/liveBroadcastEndMock'

const props = defineProps<{
  title: string
  elapsedTime: string
  peakViewerCount: number | null
  summary: BroadcastEndSummary
}>()

const emit = defineEmits<{
  'to-list': []
  'manage-unsold': []
}>()

const unsoldResults = computed(() =>
  props.summary.results.filter((result) => result.outcome === 'UNSOLD'),
)

const formatPrice = (value: number) => `${value.toLocaleString('ko-KR')}P`

const outcomeLabel: Record<string, string> = {
  WON: '낙찰',
  UNSOLD: '미낙찰',
  NOT_AUCTIONED: '경매 안 함',
}
</script>

<template>
  <section class="broadcast-end" aria-labelledby="broadcast-end-title">
    <header class="broadcast-end__head">
      <span class="broadcast-end__badge">방송 종료</span>
      <h1 id="broadcast-end-title" class="broadcast-end__title">{{ title }}</h1>
      <p class="broadcast-end__subtitle">방송 결과를 정리했어요.</p>
    </header>

    <dl class="broadcast-end__stats">
      <div class="broadcast-end__stat">
        <dt>방송 시간</dt>
        <dd>{{ elapsedTime }}</dd>
      </div>
      <div class="broadcast-end__stat">
        <dt>최고 시청자</dt>
        <dd>{{ peakViewerCount !== null ? `${peakViewerCount.toLocaleString('ko-KR')}명` : '-' }}</dd>
      </div>
      <div class="broadcast-end__stat">
        <dt>낙찰</dt>
        <dd>{{ summary.soldCount }} / {{ summary.productCount }}개</dd>
      </div>
      <div class="broadcast-end__stat broadcast-end__stat--accent">
        <dt>총 판매액</dt>
        <dd>{{ formatPrice(summary.totalSales) }}</dd>
      </div>
    </dl>

    <div class="broadcast-end__section">
      <h2 class="broadcast-end__section-title">상품별 결과</h2>
      <ul class="broadcast-end__list">
        <li v-for="result in summary.results" :key="result.productId" class="broadcast-end__item">
          <div class="broadcast-end__item-main">
            <span
              class="broadcast-end__outcome"
              :class="`broadcast-end__outcome--${result.outcome.toLowerCase()}`"
            >
              {{ outcomeLabel[result.outcome] }}
            </span>
            <span class="broadcast-end__item-title">{{ result.title }}</span>
          </div>
          <div class="broadcast-end__item-meta">
            <template v-if="result.outcome === 'WON'">
              <span class="broadcast-end__winner">{{ result.winnerNickname }}</span>
              <strong class="broadcast-end__price">{{ formatPrice(result.finalPrice ?? 0) }}</strong>
            </template>
            <span v-else class="broadcast-end__item-none">—</span>
          </div>
        </li>
      </ul>
    </div>

    <!-- 미낙찰 처리 진입 (실제 경매 재시도/상시 판매 선택 동작은 440에서). 미낙찰 없으면 숨김. -->
    <div v-if="summary.unsoldCount > 0" class="broadcast-end__section broadcast-end__unsold">
      <h2 class="broadcast-end__section-title">
        남은 상품 {{ summary.unsoldCount }}개
      </h2>
      <p class="broadcast-end__unsold-desc">
        낙찰되지 않은 상품이에요. 상시 판매로 전환하거나 경매 예정으로 되돌릴 수 있어요.
      </p>
      <ul class="broadcast-end__unsold-list">
        <li v-for="result in unsoldResults" :key="result.productId">{{ result.title }}</li>
      </ul>
      <button type="button" class="broadcast-end__unsold-action" @click="emit('manage-unsold')">
        남은 상품 관리
      </button>
    </div>

    <div class="broadcast-end__actions">
      <button type="button" class="broadcast-end__to-list" @click="emit('to-list')">
        라이브 목록으로
      </button>
    </div>
  </section>
</template>

<style scoped lang="scss">
.broadcast-end {
  display: flex;
  width: 100%;
  max-width: 720px;
  flex-direction: column;
  gap: var(--space-4);
  margin: 0 auto;
  padding: var(--space-6) var(--space-4) var(--space-8);
}

.broadcast-end__head {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.broadcast-end__badge {
  align-self: flex-start;
  padding: 4px 10px;
  border-radius: var(--radius-chip);
  background: var(--color-live-surface-raised);
  color: var(--color-live-text-secondary);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
}

.broadcast-end__title {
  color: var(--color-live-text-primary);
  font-size: 22px;
  font-weight: 800;
}

.broadcast-end__subtitle {
  color: var(--color-live-text-secondary);
  font-size: 13px;
}

.broadcast-end__stats {
  display: grid;
  gap: var(--space-3);
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.broadcast-end__stat {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: var(--space-3);
  border: 1px solid var(--color-live-border);
  border-radius: var(--radius-control);
  background: var(--color-live-surface);
}

.broadcast-end__stat dt {
  color: var(--color-live-text-secondary);
  font-size: 11px;
}

.broadcast-end__stat dd {
  color: var(--color-live-text-primary);
  font-size: 16px;
  font-weight: 800;
}

.broadcast-end__stat--accent dd {
  color: var(--color-live);
}

.broadcast-end__section {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.broadcast-end__section-title {
  color: var(--color-live-text-primary);
  font-size: 14px;
  font-weight: 700;
}

.broadcast-end__list {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--color-live-border);
  border-radius: var(--radius-control);
  overflow: hidden;
}

.broadcast-end__item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-3);
  background: var(--color-live-surface);
}

.broadcast-end__item + .broadcast-end__item {
  border-top: 1px solid var(--color-live-border);
}

.broadcast-end__item-main {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: var(--space-2);
}

.broadcast-end__outcome {
  flex-shrink: 0;
  padding: 2px 8px;
  border-radius: var(--radius-badge);
  font-size: 10px;
  font-weight: 700;
}

.broadcast-end__outcome--won {
  background: var(--color-live);
  color: var(--color-text-inverse);
}

.broadcast-end__outcome--unsold {
  background: color-mix(in srgb, var(--color-error) 22%, transparent);
  color: var(--color-error);
}

.broadcast-end__outcome--not_auctioned {
  background: var(--color-live-surface-raised);
  color: var(--color-live-text-secondary);
}

.broadcast-end__item-title {
  overflow: hidden;
  color: var(--color-live-text-primary);
  font-size: 13px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.broadcast-end__item-meta {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  gap: var(--space-2);
}

.broadcast-end__winner {
  color: var(--color-live-text-secondary);
  font-size: 12px;
}

.broadcast-end__price {
  color: var(--color-live-text-primary);
  font-size: 13px;
  font-weight: 800;
}

.broadcast-end__item-none {
  color: var(--color-live-text-secondary);
  font-size: 13px;
}

.broadcast-end__unsold {
  padding: var(--space-4);
  border: 1px solid color-mix(in srgb, var(--color-error) 40%, var(--color-live-border));
  border-radius: var(--radius-card);
  background: color-mix(in srgb, var(--color-error) 8%, transparent);
}

.broadcast-end__unsold-desc {
  color: var(--color-live-text-secondary);
  font-size: 12px;
  line-height: 18px;
}

.broadcast-end__unsold-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: var(--space-2) 0;
}

.broadcast-end__unsold-list li {
  padding: 4px 10px;
  border-radius: var(--radius-chip);
  background: var(--color-live-surface);
  color: var(--color-live-text-primary);
  font-size: 12px;
}

.broadcast-end__unsold-action {
  min-height: 42px;
  margin-top: var(--space-2);
  padding: 0 var(--space-5);
  border: 0;
  border-radius: var(--radius-control);
  background: var(--color-live);
  color: var(--color-text-inverse);
  font-size: 14px;
  font-weight: 700;
}

.broadcast-end__unsold-action:hover {
  opacity: 0.92;
}

.broadcast-end__actions {
  display: flex;
  margin-top: var(--space-2);
  padding-top: var(--space-2);
}

.broadcast-end__to-list {
  min-height: 44px;
  flex: 1;
  border: 1px solid var(--color-live-border);
  border-radius: var(--radius-control);
  background: var(--color-live-surface);
  color: var(--color-live-text-primary);
  font-size: 14px;
  font-weight: 700;
}

.broadcast-end__to-list:hover {
  background: var(--color-live-surface-raised);
}

@media (max-width: 720px) {
  .broadcast-end__stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
