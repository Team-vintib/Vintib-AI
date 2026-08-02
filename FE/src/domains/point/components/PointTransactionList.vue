<script setup lang="ts">
import { POINT_TRANSACTION_TYPE_LABELS } from '@/domains/point/constants/pointOptions'
import type { PointTransaction } from '@/domains/point/types/point.types'

withDefaults(
  defineProps<{
    transactions: PointTransaction[]
    title?: string
    showViewAll?: boolean
  }>(),
  {
    title: '포인트 내역',
    showViewAll: false,
  },
)

const emit = defineEmits<{
  viewAll: []
}>()

const formatPoint = (amount: number) => {
  const sign = amount > 0 ? '+' : ''
  return `${sign}${amount.toLocaleString('ko-KR')}P`
}

const formatDateTime = (dateTime: string) =>
  new Intl.DateTimeFormat('ko-KR', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(dateTime))
</script>

<template>
  <section class="point-transactions" aria-labelledby="point-transactions-title">
    <header>
      <h2 id="point-transactions-title">{{ title }}</h2>
      <button v-if="showViewAll" type="button" @click="emit('viewAll')">전체 내역</button>
    </header>

    <div v-if="transactions.length === 0" class="point-transactions__empty">
      표시할 포인트 내역이 없습니다.
    </div>

    <ul v-else class="point-transactions__list">
      <li v-for="transaction in transactions" :key="transaction.id">
        <div class="point-transactions__main">
          <span>{{ POINT_TRANSACTION_TYPE_LABELS[transaction.type] }}</span>
          <strong>{{ transaction.title }}</strong>
          <small>{{ formatDateTime(transaction.createdAt) }}</small>
          <small v-if="transaction.memo">{{ transaction.memo }}</small>
        </div>

        <div class="point-transactions__amount">
          <strong :class="{ 'point-transactions__amount--minus': transaction.amount < 0 }">
            {{ formatPoint(transaction.amount) }}
          </strong>
          <span>잔액 {{ transaction.balanceAfter.toLocaleString('ko-KR') }}P</span>
        </div>
      </li>
    </ul>
  </section>
</template>

<style scoped lang="scss">
.point-transactions {
  display: grid;
  gap: var(--space-4);
}

.point-transactions header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
}

.point-transactions h2 {
  color: var(--color-text-primary);
  font-size: 20px;
  font-weight: var(--font-weight-extrabold);
  line-height: 28px;
}

.point-transactions header button {
  min-height: var(--button-height-small);
  padding: 0 var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-size: 14px;
  font-weight: var(--font-weight-bold);
}

.point-transactions__list {
  display: grid;
  gap: var(--space-3);
  padding: 0;
  margin: 0;
  list-style: none;
}

.point-transactions__list li,
.point-transactions__empty {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
}

.point-transactions__list li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-4);
}

.point-transactions__main,
.point-transactions__amount {
  display: grid;
  gap: var(--space-1);
}

.point-transactions__main span {
  color: var(--color-primary);
  font-size: 12px;
  font-weight: var(--font-weight-bold);
  line-height: 18px;
}

.point-transactions__main strong {
  color: var(--color-text-primary);
  font-size: 15px;
  font-weight: var(--font-weight-bold);
  line-height: 22px;
}

.point-transactions__main small,
.point-transactions__amount span {
  color: var(--color-text-muted);
  font-size: 13px;
  line-height: 20px;
}

.point-transactions__amount {
  justify-items: end;
  min-width: 132px;
}

.point-transactions__amount strong {
  color: var(--color-primary);
  font-size: 16px;
  font-weight: var(--font-weight-extrabold);
  line-height: 24px;
}

.point-transactions__amount--minus {
  color: var(--color-text-primary) !important;
}

.point-transactions__empty {
  padding: var(--space-6);
  color: var(--color-text-secondary);
  font-size: 14px;
  line-height: 22px;
  text-align: center;
}

@media (max-width: 640px) {
  .point-transactions header,
  .point-transactions__list li {
    align-items: stretch;
    flex-direction: column;
  }

  .point-transactions__amount {
    justify-items: start;
  }
}
</style>
