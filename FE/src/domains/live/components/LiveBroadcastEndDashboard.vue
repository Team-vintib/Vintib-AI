<script setup lang="ts">
import { computed } from 'vue'

import type { BroadcastEndSummary } from '@/domains/auction/types/liveAuction.types'

const props = defineProps<{
  title: string
  elapsedTime: string
  peakViewerCount: number | null
  summary: BroadcastEndSummary | null
  manageableUnsoldCount: number
  isLoading: boolean
  errorMessage: string
}>()

const emit = defineEmits<{
  retry: []
  'to-list': []
  'manage-unsold': []
}>()

const productCount = computed(() => props.summary?.results.length ?? 0)
const unsoldResults = computed(
  () => props.summary?.results.filter((result) => result.status === 'UNSOLD') ?? [],
)

const formatPrice = (value: number) => `${value.toLocaleString('ko-KR')}P`
const resultLabel = (status: 'SOLD' | 'UNSOLD', soldVia: 'AUCTION' | 'DIRECT_SALE' | null) => {
  if (status === 'UNSOLD') return '미판매'
  return soldVia === 'AUCTION' ? '낙찰' : '판매'
}
</script>

<template>
  <section class="broadcast-end" aria-labelledby="broadcast-end-title">
    <header class="broadcast-end__head">
      <span class="broadcast-end__badge">방송 종료</span>
      <h1 id="broadcast-end-title" class="broadcast-end__title">{{ title }}</h1>
      <p class="broadcast-end__subtitle">방송 결과를 정리했어요.</p>
    </header>

    <div v-if="isLoading" class="broadcast-end__state" role="status">
      방송 결과를 불러오는 중입니다.
    </div>

    <div v-else-if="errorMessage" class="broadcast-end__state broadcast-end__state--error">
      <p>{{ errorMessage }}</p>
      <button type="button" @click="emit('retry')">다시 시도</button>
    </div>

    <template v-else-if="summary">
      <dl class="broadcast-end__stats">
        <div class="broadcast-end__stat">
          <dt>방송 시간</dt>
          <dd>{{ elapsedTime }}</dd>
        </div>
        <div class="broadcast-end__stat">
          <dt>최고 시청자</dt>
          <dd>
            {{ peakViewerCount !== null ? `${peakViewerCount.toLocaleString('ko-KR')}명` : '-' }}
          </dd>
        </div>
        <div class="broadcast-end__stat">
          <dt>판매 완료</dt>
          <dd>{{ summary.soldCount }} / {{ productCount }}개</dd>
        </div>
        <div class="broadcast-end__stat broadcast-end__stat--accent">
          <dt>총 판매액</dt>
          <dd>{{ formatPrice(summary.totalSales) }}</dd>
        </div>
      </dl>

      <div class="broadcast-end__section">
        <h2 class="broadcast-end__section-title">상품별 결과</h2>
        <p v-if="summary.results.length === 0" class="broadcast-end__empty">
          판매 결과가 없습니다.
        </p>
        <ul v-else class="broadcast-end__list">
          <li
            v-for="result in summary.results"
            :key="result.productId"
            class="broadcast-end__item"
          >
            <div class="broadcast-end__item-main">
              <span
                class="broadcast-end__outcome"
                :class="`broadcast-end__outcome--${result.status.toLowerCase()}`"
              >
                {{ resultLabel(result.status, result.soldVia) }}
              </span>
              <span class="broadcast-end__item-title">{{ result.title }}</span>
            </div>
            <div class="broadcast-end__item-meta">
              <span v-if="result.status === 'SOLD'" class="broadcast-end__method">
                {{ result.soldVia === 'AUCTION' ? '경매' : '상시 판매' }}
              </span>
              <strong v-if="result.finalPrice !== null" class="broadcast-end__price">
                {{ formatPrice(result.finalPrice) }}
              </strong>
              <span v-else class="broadcast-end__item-none">—</span>
            </div>
          </li>
        </ul>
      </div>

      <div
        v-if="summary.unsoldCount > 0"
        class="broadcast-end__section broadcast-end__unsold"
      >
        <h2 class="broadcast-end__section-title">미판매 상품 {{ summary.unsoldCount }}개</h2>
        <p class="broadcast-end__unsold-desc">
          방송에서 판매되지 않은 상품이에요.
          <template v-if="manageableUnsoldCount > 0">
            경매가 유찰된 {{ manageableUnsoldCount }}개 상품은 판매 방식을 정할 수 있어요.
          </template>
        </p>
        <ul class="broadcast-end__unsold-list">
          <li v-for="result in unsoldResults" :key="result.productId">{{ result.title }}</li>
        </ul>
        <button
          v-if="manageableUnsoldCount > 0"
          type="button"
          class="broadcast-end__unsold-action"
          @click="emit('manage-unsold')"
        >
          유찰 상품 관리
        </button>
      </div>
    </template>

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

.broadcast-end__head,
.broadcast-end__section {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.broadcast-end__badge {
  align-self: flex-start;
  padding: 4px 10px;
  border-radius: var(--radius-chip);
  background: var(--color-live-surface-raised);
  color: var(--color-live-text-secondary);
  font-size: var(--font-size-2xs);
  font-weight: var(--font-weight-bold);
}

.broadcast-end__title {
  color: var(--color-live-text-primary);
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-extrabold);
}

.broadcast-end__subtitle,
.broadcast-end__empty,
.broadcast-end__state {
  color: var(--color-live-text-secondary);
  font-size: var(--font-size-caption);
}

.broadcast-end__state {
  padding: var(--space-5);
  border: 1px solid var(--color-live-border);
  border-radius: var(--radius-control);
  background: var(--color-live-surface);
  text-align: center;
}

.broadcast-end__state--error {
  display: flex;
  align-items: center;
  flex-direction: column;
  gap: var(--space-3);
  color: var(--color-error);
}

.broadcast-end__state button {
  min-height: var(--button-height-tight);
  padding: 0 var(--space-4);
  border: 1px solid var(--color-live-border);
  border-radius: var(--radius-control);
  background: var(--color-live-surface-raised);
  color: var(--color-live-text-primary);
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
  font-size: var(--font-size-2xs);
}

.broadcast-end__stat dd {
  color: var(--color-live-text-primary);
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-extrabold);
}

.broadcast-end__stat--accent dd {
  color: var(--color-live);
}

.broadcast-end__section-title {
  color: var(--color-live-text-primary);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-bold);
}

.broadcast-end__list {
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

.broadcast-end__item-main,
.broadcast-end__item-meta {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: var(--space-2);
}

.broadcast-end__item-meta {
  flex-shrink: 0;
}

.broadcast-end__outcome {
  flex-shrink: 0;
  padding: 2px 8px;
  border-radius: var(--radius-badge);
  font-size: var(--font-size-badge);
  font-weight: var(--font-weight-bold);
}

.broadcast-end__outcome--sold {
  background: var(--color-live);
  color: var(--color-text-inverse);
}

.broadcast-end__outcome--unsold {
  background: color-mix(in srgb, var(--color-error) 22%, transparent);
  color: var(--color-error);
}

.broadcast-end__item-title {
  overflow: hidden;
  color: var(--color-live-text-primary);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-semibold);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.broadcast-end__method,
.broadcast-end__item-none {
  color: var(--color-live-text-secondary);
  font-size: var(--font-size-xs);
}

.broadcast-end__price {
  color: var(--color-live-text-primary);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-extrabold);
}

.broadcast-end__unsold {
  padding: var(--space-4);
  border: 1px solid color-mix(in srgb, var(--color-error) 40%, var(--color-live-border));
  border-radius: var(--radius-card);
  background: color-mix(in srgb, var(--color-error) 8%, transparent);
}

.broadcast-end__unsold-desc {
  color: var(--color-live-text-secondary);
  font-size: var(--font-size-xs);
  line-height: var(--line-height-snug);
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
  font-size: var(--font-size-xs);
}

.broadcast-end__unsold-action,
.broadcast-end__to-list {
  min-height: var(--button-height-compact);
  border-radius: var(--radius-control);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-bold);
}

.broadcast-end__unsold-action {
  margin-top: var(--space-2);
  padding: 0 var(--space-5);
  border: 0;
  background: var(--color-live);
  color: var(--color-text-inverse);
}

.broadcast-end__actions {
  display: flex;
  margin-top: var(--space-2);
}

.broadcast-end__to-list {
  flex: 1;
  border: 1px solid var(--color-live-border);
  background: var(--color-live-surface);
  color: var(--color-live-text-primary);
}

@media (max-width: 720px) {
  .broadcast-end__stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
