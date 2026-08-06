<script setup lang="ts">
import type { PointBalance } from '@/domains/point/types/point.types'

const props = defineProps<{
  balance: PointBalance
}>()

const formatPoint = (amount: number) => `${amount.toLocaleString('ko-KR')}P`
// "보유"는 화면에 실제로 펼쳐 보이는 3개 카드(출금 가능/정산 예정/출금 처리 중)의 합과 일치해야
// 한다. 입찰 보류·거래 대금 보관은 여기 포함하지 않는다 — 입찰 보류는 라이브 경매 화면에,
// 거래 대금 보관은 주문/구매내역에 이미 노출되므로 지갑 요약에서는 중복 표시하지 않는다.
const totalPoint = () =>
  props.balance.available + props.balance.pendingSettlement + props.balance.withdrawalProcessing
</script>

<template>
  <section class="point-summary" aria-label="포인트 요약">
    <div class="point-summary__hero">
      <span>사용 가능 포인트</span>
      <strong>{{ formatPoint(balance.available) }}</strong>
    </div>

    <dl class="point-summary__cards">
      <div>
        <dt>보유</dt>
        <dd>{{ formatPoint(totalPoint()) }}</dd>
      </div>
      <div>
        <dt>출금 가능</dt>
        <dd>{{ formatPoint(balance.withdrawable) }}</dd>
      </div>
      <div>
        <dt>정산 예정</dt>
        <dd>{{ formatPoint(balance.pendingSettlement) }}</dd>
      </div>
      <div>
        <dt>출금 처리 중</dt>
        <dd>{{ formatPoint(balance.withdrawalProcessing) }}</dd>
      </div>
    </dl>
  </section>
</template>

<style scoped lang="scss">
.point-summary {
  display: grid;
  gap: var(--space-4);
}

.point-summary__hero {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-8);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

.point-summary__hero span {
  font-size: var(--font-size-body);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-body);
  opacity: 0.82;
}

.point-summary__hero strong {
  font-size: 44px;
  font-weight: var(--font-weight-extrabold);
  line-height: 54px;
}

.point-summary__cards {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space-3);
  margin: 0;
}

.point-summary__cards div {
  display: grid;
  gap: var(--space-2);
  min-height: 108px;
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
}

.point-summary__cards dt {
  color: var(--color-text-secondary);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-control);
}

.point-summary__cards dd {
  margin: 0;
  color: var(--color-text-primary);
  font-size: var(--font-size-lg-plus);
  font-weight: var(--font-weight-extrabold);
  line-height: var(--line-height-lg-plus);
}

@media (max-width: 860px) {
  .point-summary__hero strong {
    font-size: 36px;
    line-height: var(--line-height-4xl);
  }

  .point-summary__cards {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 520px) {
  .point-summary__cards {
    grid-template-columns: 1fr;
  }
}
</style>
