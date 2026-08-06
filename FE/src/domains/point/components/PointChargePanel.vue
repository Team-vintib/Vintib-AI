<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

import { POINT_CHARGE_MIN_AMOUNT, POINT_QUICK_CHARGE_AMOUNTS } from '@/domains/point/constants/pointOptions'
import { ROUTE_NAMES } from '@/shared/constants/routes'

const router = useRouter()

const emit = defineEmits<{
  error: [message: string]
}>()

const amount = ref('')

const parsedAmount = computed(() => Number(amount.value))
const canSubmit = computed(
  () => Number.isInteger(parsedAmount.value) && parsedAmount.value >= POINT_CHARGE_MIN_AMOUNT,
)

const selectQuickAmount = (nextAmount: number) => {
  amount.value = String(nextAmount)
}

// 결제수단 선택은 새 탭에서 진행한다(토스 위젯이 앱 다크 테마와 안 어울려 분리했다). 팝업 차단을
// 피하려면 window.open을 클릭 핸들러 안에서 await 없이 곧바로 호출해야 한다.
const openCheckout = () => {
  if (!canSubmit.value) {
    emit('error', `충전 금액은 최소 ${POINT_CHARGE_MIN_AMOUNT.toLocaleString('ko-KR')}P 이상이어야 합니다.`)
    return
  }

  const checkoutRoute = router.resolve({
    name: ROUTE_NAMES.POINT_CHARGE_CHECKOUT,
    query: { amount: String(parsedAmount.value) },
  })
  window.open(checkoutRoute.href, '_blank')
}
</script>

<template>
  <section class="point-panel" aria-labelledby="point-charge-title">
    <header>
      <h2 id="point-charge-title">충전</h2>
      <p>충전 금액을 선택하면 새 탭에서 결제를 진행합니다.</p>
    </header>

    <div class="point-charge__section">
      <h3>충전 금액 선택</h3>
      <div class="point-charge__quick" aria-label="빠른 충전 금액">
        <button
          v-for="quickAmount in POINT_QUICK_CHARGE_AMOUNTS"
          :key="quickAmount"
          type="button"
          :class="{ 'point-charge__quick--active': parsedAmount === quickAmount }"
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
        />
      </label>
    </div>

    <button class="point-panel__submit" type="button" :disabled="!canSubmit" @click="openCheckout">
      충전하기
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
  font-size: var(--font-size-lg-plus);
  font-weight: var(--font-weight-extrabold);
  line-height: var(--line-height-lg-plus);
}

.point-panel h3 {
  color: var(--color-text-primary);
  font-size: var(--font-size-body);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-relaxed);
}

.point-panel p,
.point-charge__field span {
  color: var(--color-text-secondary);
  font-size: var(--font-size-caption);
  line-height: var(--line-height-control);
}

.point-charge__quick {
  display: grid;
  gap: var(--space-2);
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.point-charge__quick button,
.point-panel__submit {
  min-height: var(--button-height-small);
  border-radius: var(--radius-control);
  font-size: var(--font-size-button-small);
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
  font-size: var(--font-size-body);
}

.point-panel__submit {
  border: 0;
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

.point-panel__submit:disabled {
  opacity: 0.55;
}

@media (max-width: 640px) {
  .point-charge__quick {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
