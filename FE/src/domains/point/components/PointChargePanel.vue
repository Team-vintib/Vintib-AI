<script setup lang="ts">
import { loadTossPayments } from '@tosspayments/tosspayments-sdk'
import type { TossPaymentsWidgets } from '@tosspayments/tosspayments-sdk'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { readyPointCharge } from '@/domains/point/api/pointApi'
import { POINT_CHARGE_MIN_AMOUNT, POINT_QUICK_CHARGE_AMOUNTS } from '@/domains/point/constants/pointOptions'
import { ROUTE_PATHS } from '@/shared/constants/routes'

const PAYMENT_METHOD_SELECTOR = '#toss-payment-method'
const AGREEMENT_SELECTOR = '#toss-agreement'

const props = defineProps<{
  userId: number
  currentBalance: number
}>()

const emit = defineEmits<{
  error: [message: string]
}>()

const amount = ref('')
const errorMessage = ref('')
const isPreparing = ref(true)
const isRequesting = ref(false)

let widgets: TossPaymentsWidgets | null = null

const parsedAmount = computed(() => Number(amount.value))
const afterBalance = computed(() =>
  Number.isInteger(parsedAmount.value) && parsedAmount.value > 0
    ? props.currentBalance + parsedAmount.value
    : props.currentBalance,
)
const canSubmit = computed(
  () =>
    !isPreparing.value &&
    !isRequesting.value &&
    widgets !== null &&
    Number.isInteger(parsedAmount.value) &&
    parsedAmount.value >= POINT_CHARGE_MIN_AMOUNT,
)

watch(amount, (next) => {
  errorMessage.value = ''
  const nextAmount = Number(next)

  if (widgets && Number.isInteger(nextAmount) && nextAmount >= POINT_CHARGE_MIN_AMOUNT) {
    void widgets.setAmount({ currency: 'KRW', value: nextAmount })
  }
})

const selectQuickAmount = (nextAmount: number) => {
  amount.value = String(nextAmount)
}

// 결제수단/약관 위젯을 미리 그려 둬야 "충전하기"를 눌렀을 때 바로 결제를 요청할 수 있다.
// clientKey는 BE ready 응답에서만 받을 수 있어, 위젯 준비 목적으로 최소 금액으로 한 번 ready를 호출한다.
const initWidgets = async () => {
  isPreparing.value = true

  try {
    const ready = await readyPointCharge(props.userId, POINT_CHARGE_MIN_AMOUNT)

    if (!ready.clientKey) {
      throw new Error('missing client key')
    }

    const tossPayments = await loadTossPayments(ready.clientKey)
    const nextWidgets = tossPayments.widgets({ customerKey: `member-${props.userId}` })

    await nextWidgets.setAmount({ currency: 'KRW', value: POINT_CHARGE_MIN_AMOUNT })
    await nextWidgets.renderPaymentMethods({ selector: PAYMENT_METHOD_SELECTOR })
    await nextWidgets.renderAgreement({ selector: AGREEMENT_SELECTOR })

    widgets = nextWidgets
  } catch {
    emit('error', '결제 수단을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.')
  } finally {
    isPreparing.value = false
  }
}

onMounted(() => {
  void initWidgets()
})

onBeforeUnmount(() => {
  widgets = null
})

const submitCharge = async () => {
  if (!Number.isInteger(parsedAmount.value) || parsedAmount.value < POINT_CHARGE_MIN_AMOUNT) {
    errorMessage.value = `충전 금액은 최소 ${POINT_CHARGE_MIN_AMOUNT.toLocaleString('ko-KR')}P 이상이어야 합니다.`
    return
  }

  if (!widgets) {
    errorMessage.value = '결제 수단을 불러오는 중입니다. 잠시 후 다시 시도해 주세요.'
    return
  }

  isRequesting.value = true
  errorMessage.value = ''

  try {
    // 위젯 준비 때 발급받은 orderId는 최소 금액용이라 그대로 쓰지 않는다 — 최종 금액으로 다시
    // ready를 호출해 confirm 단계에서 금액이 어긋나지 않는(PAYMENT_AMOUNT_MISMATCH) orderId를 받는다.
    const ready = await readyPointCharge(props.userId, parsedAmount.value)
    await widgets.setAmount({ currency: 'KRW', value: ready.amount })
    await widgets.requestPayment({
      orderId: ready.orderId,
      orderName: `포인트 충전 ${ready.amount.toLocaleString('ko-KR')}P`,
      successUrl: `${window.location.origin}${ROUTE_PATHS.POINT_CHARGE_SUCCESS}`,
      failUrl: `${window.location.origin}${ROUTE_PATHS.POINT_CHARGE_FAIL}`,
    })
    // 성공하면 브라우저가 successUrl로 리다이렉트되어 이 아래 코드는 보통 실행되지 않는다.
  } catch (error) {
    const message =
      error && typeof error === 'object' && 'message' in error && typeof error.message === 'string'
        ? error.message
        : '결제 요청 중 오류가 발생했습니다. 다시 시도해 주세요.'
    errorMessage.value = message
  } finally {
    isRequesting.value = false
  }
}
</script>

<template>
  <section class="point-panel" aria-labelledby="point-charge-title">
    <header>
      <h2 id="point-charge-title">충전</h2>
      <p>충전 금액을 선택하고 결제 수단을 골라 주세요.</p>
    </header>

    <div class="point-charge__section">
      <h3>충전 금액 선택</h3>
      <div class="point-charge__quick" aria-label="빠른 충전 금액">
        <button
          v-for="quickAmount in POINT_QUICK_CHARGE_AMOUNTS"
          :key="quickAmount"
          type="button"
          :class="{ 'point-charge__quick--active': parsedAmount === quickAmount }"
          :disabled="isRequesting"
          @click="selectQuickAmount(quickAmount)"
        >
          {{ quickAmount.toLocaleString('ko-KR') }}P
        </button>
      </div>

      <label class="point-charge__field">
        <span>직접 입력</span>
        <input
          v-model="amount"
          type="number"
          :min="POINT_CHARGE_MIN_AMOUNT"
          step="1000"
          inputmode="numeric"
          placeholder="충전할 금액 입력"
          :disabled="isRequesting"
        />
      </label>
    </div>

    <div class="point-charge__section">
      <h3>결제 수단</h3>
      <p v-if="isPreparing" class="point-charge__widget-loading" role="status">
        결제 수단을 불러오는 중입니다…
      </p>
      <div :id="PAYMENT_METHOD_SELECTOR.slice(1)" class="point-charge__toss-widget"></div>
      <div :id="AGREEMENT_SELECTOR.slice(1)" class="point-charge__toss-widget"></div>
    </div>

    <dl class="point-charge__summary">
      <div>
        <dt>충전 금액</dt>
        <dd>{{ Math.max(parsedAmount || 0, 0).toLocaleString('ko-KR') }}P</dd>
      </div>
      <div>
        <dt>충전 후 잔액</dt>
        <dd>{{ afterBalance.toLocaleString('ko-KR') }}P</dd>
      </div>
    </dl>

    <p v-if="errorMessage" class="point-panel__error" role="alert">{{ errorMessage }}</p>

    <button
      class="point-panel__submit"
      type="button"
      :disabled="!canSubmit"
      @click="submitCharge"
    >
      {{ isRequesting ? '결제 요청 중' : '충전하기' }}
    </button>
  </section>
</template>

<style scoped lang="scss">
.point-panel,
.point-charge__section {
  display: grid;
  gap: var(--space-4);
}

.point-panel {
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
}

.point-panel header,
.point-charge__field {
  display: grid;
  gap: var(--space-2);
}

.point-panel h2 {
  color: var(--color-text-primary);
  font-size: 20px;
  font-weight: var(--font-weight-extrabold);
  line-height: 28px;
}

.point-panel h3 {
  color: var(--color-text-primary);
  font-size: 15px;
  font-weight: var(--font-weight-bold);
  line-height: 22px;
}

.point-panel p,
.point-charge__field span {
  color: var(--color-text-secondary);
  font-size: 13px;
  line-height: 20px;
}

.point-charge__quick,
.point-charge__summary {
  display: grid;
  gap: var(--space-2);
}

.point-charge__quick {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.point-charge__quick button,
.point-panel__submit {
  min-height: var(--button-height-small);
  border-radius: var(--radius-control);
  font-size: 14px;
  font-weight: var(--font-weight-bold);
}

.point-charge__quick button {
  border: 1px solid var(--color-border);
  background: var(--color-surface-secondary);
  color: var(--color-text-primary);
}

.point-charge__quick--active {
  border-color: var(--color-primary) !important;
  background: var(--color-primary-soft) !important;
  color: var(--color-primary) !important;
}

.point-charge__field input {
  min-height: var(--button-height-standard);
  padding: 0 var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-size: 15px;
}

.point-charge__widget-loading {
  color: var(--color-text-secondary);
}

.point-charge__toss-widget {
  min-height: 1px;
}

.point-charge__summary {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  margin: 0;
}

.point-charge__summary div {
  padding: var(--space-4);
  border-radius: var(--radius-control);
  background: var(--color-surface-secondary);
}

.point-charge__summary dt {
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: var(--font-weight-bold);
  line-height: 20px;
}

.point-charge__summary dd {
  margin: var(--space-1) 0 0;
  color: var(--color-text-primary);
  font-size: 18px;
  font-weight: var(--font-weight-extrabold);
  line-height: 26px;
}

.point-panel__error {
  color: var(--color-error) !important;
  font-weight: var(--font-weight-semibold);
}

.point-panel__submit {
  border: 0;
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

.point-panel__submit:disabled,
.point-charge__quick button:disabled {
  opacity: 0.55;
}

@media (max-width: 640px) {
  .point-charge__quick,
  .point-charge__summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
