<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import {
  POINT_CHARGE_MIN_AMOUNT,
  POINT_PAYMENT_METHODS,
  POINT_QUICK_CHARGE_AMOUNTS,
} from '@/domains/point/constants/pointOptions'

const props = defineProps<{
  currentBalance: number
  isSubmitting: boolean
}>()

const emit = defineEmits<{
  charge: [amount: number]
}>()

const amount = ref('')
const paymentMethod = ref<(typeof POINT_PAYMENT_METHODS)[number]>(POINT_PAYMENT_METHODS[0])
const errorMessage = ref('')

const parsedAmount = computed(() => Number(amount.value))
const afterBalance = computed(() =>
  Number.isInteger(parsedAmount.value) && parsedAmount.value > 0
    ? props.currentBalance + parsedAmount.value
    : props.currentBalance,
)
const canSubmit = computed(
  () =>
    !props.isSubmitting &&
    Number.isInteger(parsedAmount.value) &&
    parsedAmount.value >= POINT_CHARGE_MIN_AMOUNT,
)

watch(amount, () => {
  errorMessage.value = ''
})

const selectQuickAmount = (nextAmount: number) => {
  amount.value = String(nextAmount)
}

const submitCharge = () => {
  if (!Number.isInteger(parsedAmount.value) || parsedAmount.value < POINT_CHARGE_MIN_AMOUNT) {
    errorMessage.value = `충전 금액은 최소 ${POINT_CHARGE_MIN_AMOUNT.toLocaleString('ko-KR')}P 이상이어야 합니다.`
    return
  }

  emit('charge', parsedAmount.value)
}
</script>

<template>
  <section class="point-panel" aria-labelledby="point-charge-title">
    <header>
      <h2 id="point-charge-title">충전</h2>
      <p>충전 금액과 결제 수단을 선택해 주세요.</p>
    </header>

    <div class="point-charge__section">
      <h3>충전 금액 선택</h3>
      <div class="point-charge__quick" aria-label="빠른 충전 금액">
        <button
          v-for="quickAmount in POINT_QUICK_CHARGE_AMOUNTS"
          :key="quickAmount"
          type="button"
          :class="{ 'point-charge__quick--active': parsedAmount === quickAmount }"
          :disabled="isSubmitting"
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
          min="1000"
          step="1000"
          inputmode="numeric"
          placeholder="충전할 금액 입력"
          :disabled="isSubmitting"
        />
      </label>
    </div>

    <div class="point-charge__section">
      <h3>결제 수단</h3>
      <div class="point-charge__methods">
        <label v-for="method in POINT_PAYMENT_METHODS" :key="method">
          <input v-model="paymentMethod" type="radio" name="payment-method" :value="method" />
          <span>{{ method }}</span>
        </label>
      </div>
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
      {{ isSubmitting ? '충전 처리 중' : '충전하기' }}
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
.point-charge__methods,
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

.point-charge__methods label {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 40px;
  color: var(--color-text-primary);
  font-size: 14px;
  font-weight: var(--font-weight-semibold);
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
