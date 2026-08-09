<script setup lang="ts">
import { computed } from 'vue'

import type { OrderStatus } from '@/domains/order/types/order.types'
import type { OrderShipmentInfo } from '@/domains/shipping/types/shipping.types'

const props = defineProps<{
  orderStatus: OrderStatus
  shipment: OrderShipmentInfo | null
}>()

/** 진행 바에 태우는 4단계 — trackingStatus 12개를 그대로 쓰기엔 너무 세분화돼 있어 단순화한다. */
const STEPS = [
  { key: 'ordered', label: '주문 완료' },
  { key: 'shipped', label: '송장 등록' },
  { key: 'inTransit', label: '배송중' },
  { key: 'delivered', label: '배송 완료' },
] as const

const IN_TRANSIT_STATUSES = ['PICKUP_READY', 'PICKED_UP', 'IN_TRANSIT', 'OUT_FOR_DELIVERY']
/** 진행률로 표현하면 오해를 주는 예외 상태 — 바 대신 배지로 보여준다. */
const EXCEPTION_STATUSES = ['FAILED', 'RETURNED', 'CANCELLED', 'HOLD', 'UNKNOWN']

/**
 * BE의 웹훅 구독 실패 폴백(deliveryapi.co.kr 자격증명 없는 환경 등)은 order.status만 DELIVERED로
 * 즉시 확정하고 shipment.trackingStatus는 영영 null로 남긴다 — order.status도 상한으로 같이 봐야
 * 이 경우에도 "배송 완료"까지 채워진다.
 */
const isDelivered = computed(
  () =>
    !!props.shipment?.deliveredAt ||
    ['DELIVERED', 'CONFIRMED', 'SETTLED'].includes(props.orderStatus),
)
const isShipped = computed(() => !!props.shipment?.shippedAt)
const isInTransit = computed(
  () =>
    isDelivered.value ||
    (!!props.shipment?.trackingStatus && IN_TRANSIT_STATUSES.includes(props.shipment.trackingStatus)),
)

/** 1~4. 주문은 이 컴포넌트가 렌더되는 시점엔 항상 존재하므로 1단계는 늘 완료다. */
const currentStep = computed(() => {
  if (isDelivered.value) return 4
  if (isInTransit.value) return 3
  if (isShipped.value) return 2
  return 1
})

const isException = computed(
  () => !!props.shipment?.trackingStatus && EXCEPTION_STATUSES.includes(props.shipment.trackingStatus),
)
</script>

<template>
  <div class="shipment-progress" role="group" aria-label="배송 진행 상태">
    <ol class="shipment-progress__bar">
      <li
        v-for="(step, index) in STEPS"
        :key="step.key"
        class="shipment-progress__step"
        :class="{ 'shipment-progress__step--done': index + 1 <= currentStep }"
      >
        <span class="shipment-progress__dot" aria-hidden="true" />
        <span class="shipment-progress__label">{{ step.label }}</span>
      </li>
    </ol>

    <p v-if="isException" class="shipment-progress__exception" role="status">
      {{ shipment?.trackingStatusLabel }}
    </p>
  </div>
</template>

<style scoped lang="scss">
.shipment-progress {
  display: grid;
  gap: var(--space-2);
}

.shipment-progress__bar {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  list-style: none;
}

.shipment-progress__step {
  display: grid;
  position: relative;
  justify-items: center;
  gap: var(--space-2);
}

.shipment-progress__step::before {
  content: '';
  position: absolute;
  top: 5px;
  left: -50%;
  width: 100%;
  height: 2px;
  background: var(--color-border);
}

.shipment-progress__step:first-child::before {
  content: none;
}

.shipment-progress__step--done::before {
  background: var(--color-primary);
}

.shipment-progress__dot {
  z-index: 1;
  width: 12px;
  height: 12px;
  border: 2px solid var(--color-border);
  border-radius: 50%;
  background: var(--color-surface);
}

.shipment-progress__step--done .shipment-progress__dot {
  border-color: var(--color-primary);
  background: var(--color-primary);
}

.shipment-progress__label {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  line-height: var(--line-height-snug);
  text-align: center;
}

.shipment-progress__step--done .shipment-progress__label {
  color: var(--color-text-primary);
  font-weight: var(--font-weight-bold);
}

.shipment-progress__exception {
  display: inline-flex;
  align-items: center;
  justify-self: start;
  min-height: var(--badge-height-compact);
  padding: 2px 10px;
  border-radius: var(--radius-badge);
  background: var(--color-error-soft);
  color: var(--color-error);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-snug);
}
</style>
