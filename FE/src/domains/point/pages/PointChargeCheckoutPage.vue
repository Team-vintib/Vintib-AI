<script setup lang="ts">
import { loadTossPayments } from '@tosspayments/tosspayments-sdk'
import type { TossPaymentsWidgets } from '@tosspayments/tosspayments-sdk'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '@/domains/auth/stores/authStore'
import { readyPointCharge } from '@/domains/point/api/pointApi'
import { POINT_CHARGE_MIN_AMOUNT } from '@/domains/point/constants/pointOptions'
import { ROUTE_NAMES, ROUTE_PATHS } from '@/shared/constants/routes'
import DefaultLayout from '@/shared/layouts/DefaultLayout.vue'

const PAYMENT_METHOD_SELECTOR = '#toss-payment-method'
const AGREEMENT_SELECTOR = '#toss-agreement'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const amount = computed(() => Number(route.query.amount))
const isAmountValid = computed(
  () => Number.isInteger(amount.value) && amount.value >= POINT_CHARGE_MIN_AMOUNT,
)

const orderId = ref('')
const errorMessage = ref('')
const isPreparing = ref(true)
const isRequesting = ref(false)

let widgets: TossPaymentsWidgets | null = null

const canSubmit = computed(() => !isPreparing.value && !isRequesting.value && widgets !== null)

// 이 화면은 이미 확정된 금액으로 진입하므로(포인트 페이지에서 새 탭으로 열림), 예전처럼
// 위젯 준비용 임시 금액과 제출용 실제 금액으로 나눠 ready를 두 번 부를 필요가 없다 — 한 번으로 끝낸다.
const initWidgets = async () => {
  if (!isAmountValid.value) {
    isPreparing.value = false
    return
  }

  await authStore.validateStoredSession()

  const userId = authStore.user?.id
  if (!userId) {
    await router.push({ name: ROUTE_NAMES.AUTH_LOGIN, query: { redirect: route.fullPath } })
    return
  }

  isPreparing.value = true

  try {
    const ready = await readyPointCharge(userId, amount.value)

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

    console.error('[PointChargeCheckoutPage] 결제 위젯 준비 실패', error)
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
      orderName: `포인트 충전 ${amount.value.toLocaleString('ko-KR')}P`,
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
</script>

<template>
  <DefaultLayout content-max-width="640px">
    <section class="point-checkout" aria-labelledby="point-checkout-title">
      <div v-if="!isAmountValid" class="point-checkout__state" role="alert">
        <strong>결제 금액이 올바르지 않습니다.</strong>
        <p>포인트 충전 화면으로 돌아가 다시 시도해 주세요.</p>
        <a class="point-checkout__link" :href="`${ROUTE_PATHS.POINT}?section=charge`">
          충전 화면으로 이동
        </a>
      </div>

      <template v-else>
        <header>
          <h2 id="point-checkout-title">결제하기</h2>
          <p>{{ amount.toLocaleString('ko-KR') }}P를 충전합니다.</p>
        </header>

        <div class="point-checkout__section">
          <h3>결제 수단</h3>
          <p v-if="isPreparing" class="point-checkout__widget-loading" role="status">
            결제 수단을 불러오는 중입니다…
          </p>
          <div :id="PAYMENT_METHOD_SELECTOR.slice(1)" class="point-checkout__toss-widget"></div>
          <div :id="AGREEMENT_SELECTOR.slice(1)" class="point-checkout__toss-widget"></div>
        </div>

        <p v-if="errorMessage" class="point-checkout__error" role="alert">{{ errorMessage }}</p>

        <button class="point-checkout__submit" type="button" :disabled="!canSubmit" @click="submitCharge">
          {{ isRequesting ? '결제 요청 중' : `${amount.toLocaleString('ko-KR')}P 결제하기` }}
        </button>
      </template>
    </section>
  </DefaultLayout>
</template>

<style scoped lang="scss">
.point-checkout {
  display: grid;
  gap: var(--space-5);
}

.point-checkout header {
  display: grid;
  gap: var(--space-2);
}

.point-checkout h2 {
  color: var(--color-text-primary);
  font-size: var(--font-size-lg-plus);
  font-weight: var(--font-weight-extrabold);
  line-height: var(--line-height-lg-plus);
}

.point-checkout header p {
  color: var(--color-text-secondary);
  font-size: var(--font-size-body);
  line-height: var(--line-height-control);
}

.point-checkout__section {
  display: grid;
  gap: var(--space-4);
}

.point-checkout__section h3 {
  color: var(--color-text-primary);
  font-size: var(--font-size-body);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-relaxed);
}

.point-checkout__widget-loading {
  color: var(--color-text-secondary);
  font-size: var(--font-size-caption);
}

.point-checkout__toss-widget {
  min-height: 1px;
  overflow: hidden;
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface-secondary);
}

.point-checkout__error {
  color: var(--color-error);
  font-weight: var(--font-weight-semibold);
}

.point-checkout__submit {
  min-height: var(--button-height-standard);
  border: 0;
  border-radius: var(--radius-control);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-bold);
}

.point-checkout__submit:disabled {
  opacity: 0.55;
}

.point-checkout__state {
  display: grid;
  justify-items: center;
  gap: var(--space-3);
  padding: var(--space-8);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  text-align: center;
}

.point-checkout__state strong {
  color: var(--color-text-primary);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-extrabold);
  line-height: var(--line-height-lg);
}

.point-checkout__link {
  min-height: var(--button-height-small);
  display: inline-flex;
  align-items: center;
  padding: 0 var(--space-4);
  border-radius: var(--radius-control);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-bold);
  text-decoration: none;
}
</style>
