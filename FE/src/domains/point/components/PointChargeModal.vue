<script setup lang="ts">
import { loadTossPayments } from '@tosspayments/tosspayments-sdk'
import type { TossPaymentsWidgets } from '@tosspayments/tosspayments-sdk'
import { onBeforeUnmount, onMounted, ref } from 'vue'

import { useAuthStore } from '@/domains/auth/stores/authStore'
import { readyPointCharge } from '@/domains/point/api/pointApi'
import { ROUTE_PATHS } from '@/shared/constants/routes'

const PAYMENT_METHOD_SELECTOR = '#toss-payment-method'
const AGREEMENT_SELECTOR = '#toss-agreement'

const props = defineProps<{
  amount: number
}>()

const emit = defineEmits<{
  close: []
}>()

const authStore = useAuthStore()

const orderId = ref('')
const errorMessage = ref('')
const isPreparing = ref(true)
const isRequesting = ref(false)

let widgets: TossPaymentsWidgets | null = null

const canSubmit = () => !isPreparing.value && !isRequesting.value && widgets !== null

const initWidgets = async () => {
  await authStore.validateStoredSession()

  const userId = authStore.user?.id
  if (!userId) {
    errorMessage.value = '로그인이 필요합니다. 다시 로그인한 뒤 시도해 주세요.'
    isPreparing.value = false
    return
  }

  isPreparing.value = true

  try {
    const ready = await readyPointCharge(userId, props.amount)

    if (!ready.clientKey) {
      throw new Error('missing client key')
    }

    orderId.value = ready.orderId

    const tossPayments = await loadTossPayments(ready.clientKey)
    const nextWidgets = tossPayments.widgets({ customerKey: `member-${userId}` })

    await nextWidgets.setAmount({ currency: 'KRW', value: ready.amount })
    await nextWidgets.renderPaymentMethods({ selector: PAYMENT_METHOD_SELECTOR })
    await nextWidgets.renderAgreement({ selector: AGREEMENT_SELECTOR })

    widgets = nextWidgets
  } catch (error) {
    console.error('[PointChargeModal] 결제 위젯 준비 실패', error)
    const detail =
      error && typeof error === 'object' && 'message' in error && typeof error.message === 'string'
        ? error.message
        : ''
    errorMessage.value = detail
      ? `결제 수단을 불러오지 못했습니다. (${detail})`
      : '결제 수단을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.'
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
  if (!widgets || !orderId.value) {
    errorMessage.value = '결제 수단을 불러오는 중입니다. 잠시 후 다시 시도해 주세요.'
    return
  }

  isRequesting.value = true
  errorMessage.value = ''

  try {
    await widgets.requestPayment({
      orderId: orderId.value,
      orderName: `포인트 충전 ${props.amount.toLocaleString('ko-KR')}P`,
      successUrl: `${window.location.origin}${ROUTE_PATHS.POINT_CHARGE_SUCCESS}`,
      failUrl: `${window.location.origin}${ROUTE_PATHS.POINT_CHARGE_FAIL}`,
    })
    // 성공하면 이 탭이 successUrl로 리다이렉트되어 이 아래 코드는 보통 실행되지 않는다.
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

const handleClose = () => {
  if (isRequesting.value) return
  emit('close')
}
</script>

<template>
  <div class="point-charge-modal-overlay" role="presentation" @click.self="handleClose">
    <section
      class="point-charge-modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="point-charge-modal-title"
    >
      <header class="point-charge-modal__header">
        <h2 id="point-charge-modal-title">결제하기</h2>
        <button type="button" aria-label="닫기" :disabled="isRequesting" @click="handleClose">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M6 6l12 12M18 6 6 18" />
          </svg>
        </button>
      </header>

      <p class="point-charge-modal__amount">{{ amount.toLocaleString('ko-KR') }}P를 충전합니다.</p>

      <div class="point-charge-modal__section">
        <h3>결제 수단</h3>
        <p v-if="isPreparing" class="point-charge-modal__widget-loading" role="status">
          결제 수단을 불러오는 중입니다…
        </p>
        <div :id="PAYMENT_METHOD_SELECTOR.slice(1)" class="point-charge-modal__toss-widget"></div>
        <div :id="AGREEMENT_SELECTOR.slice(1)" class="point-charge-modal__toss-widget"></div>
      </div>

      <p v-if="errorMessage" class="point-charge-modal__error" role="alert">{{ errorMessage }}</p>

      <button
        class="point-charge-modal__submit"
        type="button"
        :disabled="!canSubmit()"
        @click="submitCharge"
      >
        {{ isRequesting ? '결제 요청 중' : `${amount.toLocaleString('ko-KR')}P 결제하기` }}
      </button>
    </section>
  </div>
</template>

<style scoped lang="scss">
.point-charge-modal-overlay {
  display: grid;
  position: fixed;
  /* PurchaseConfirmDialog.vue와 동일하게 헤더(--z-layer-header=10)보다 높은 전역 모달 레이어 값 사용 */
  z-index: 500;
  padding: var(--space-4);
  background: rgba(4, 6, 5, 0.72);
  inset: 0;
  place-items: center;
  backdrop-filter: blur(3px);
}

.point-charge-modal {
  display: grid;
  width: min(480px, 100%);
  max-height: 90vh;
  overflow-y: auto;
  gap: var(--space-5);
  padding: var(--space-6);
  border: 1px solid var(--color-border-strong);
  border-radius: calc(var(--radius-card) * 3);
  background: var(--color-surface);
  box-shadow:
    0 24px 64px rgba(0, 0, 0, 0.5),
    0 2px 0 rgba(255, 255, 255, 0.03) inset;
}

.point-charge-modal__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--color-border);
}

.point-charge-modal__header h2 {
  color: var(--color-text-primary);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-extrabold);
}

.point-charge-modal__header button {
  display: grid;
  width: var(--button-height-compact);
  height: var(--button-height-compact);
  border: none;
  background: none;
  color: var(--color-text-secondary);
  cursor: pointer;
  place-items: center;
}

.point-charge-modal__header button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.point-charge-modal__header button svg {
  width: var(--icon-size-sm);
  height: var(--icon-size-sm);
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-width: 1.8;
}

.point-charge-modal__amount {
  color: var(--color-text-secondary);
  font-size: var(--font-size-body);
  line-height: var(--line-height-control);
}

.point-charge-modal__section {
  display: grid;
  gap: var(--space-4);
}

.point-charge-modal__section h3 {
  color: var(--color-text-primary);
  font-size: var(--font-size-body);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-relaxed);
}

.point-charge-modal__widget-loading {
  color: var(--color-text-secondary);
  font-size: var(--font-size-caption);
}

.point-charge-modal__toss-widget {
  min-height: 1px;
  overflow: hidden;
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface-secondary);
}

.point-charge-modal__error {
  color: var(--color-error);
  font-weight: var(--font-weight-semibold);
}

.point-charge-modal__submit {
  min-height: var(--button-height-standard);
  border: 0;
  border-radius: var(--radius-control);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-bold);
}

.point-charge-modal__submit:disabled {
  opacity: 0.55;
}
</style>
