<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '@/domains/auth/stores/authStore'
import { confirmPointCharge } from '@/domains/point/api/pointApi'
import { dispatchPointBalanceUpdated } from '@/domains/point/utils/pointBalanceEvents'
import { normalizeApiError } from '@/shared/api/http'
import { ROUTE_NAMES, ROUTE_PATHS } from '@/shared/constants/routes'
import DefaultLayout from '@/shared/layouts/DefaultLayout.vue'

// 토스 결제위젯 Redirect 방식 성공 콜백. 쿼리로 {orderId, paymentKey, amount}가 붙어 온다.
// 여기서 BE confirm을 호출해야 실제로 포인트가 적립된다 — 리다이렉트만으로는 결제가 완료되지 않는다.
const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const status = ref<'confirming' | 'success' | 'error'>('confirming')
const errorMessage = ref('')
const chargedAmount = ref(0)

const confirm = async () => {
  await authStore.validateStoredSession()

  const userId = authStore.user?.id
  const orderId = firstQueryValue(route.query.orderId)
  const paymentKey = firstQueryValue(route.query.paymentKey)
  const amount = Number(firstQueryValue(route.query.amount))

  if (!userId) {
    await router.push({ name: ROUTE_NAMES.AUTH_LOGIN, query: { redirect: ROUTE_PATHS.POINT } })
    return
  }

  if (!orderId || !paymentKey || !Number.isInteger(amount) || amount <= 0) {
    status.value = 'error'
    errorMessage.value = '결제 정보가 올바르지 않습니다.'
    return
  }

  try {
    const balance = await confirmPointCharge(userId, { orderId, paymentKey, amount })
    dispatchPointBalanceUpdated({ userId, balance })
    chargedAmount.value = amount
    status.value = 'success'
  } catch (error) {
    status.value = 'error'
    errorMessage.value = normalizeApiError(error).message
  }
}

const goToWallet = () => {
  void router.push({ name: ROUTE_NAMES.POINT })
}

onMounted(() => {
  void confirm()
})

const firstQueryValue = (value: unknown): string => {
  if (Array.isArray(value)) {
    return typeof value[0] === 'string' ? value[0] : ''
  }
  return typeof value === 'string' ? value : ''
}
</script>

<template>
  <DefaultLayout content-max-width="640px">
    <section class="point-charge-result" aria-live="polite">
      <div v-if="status === 'confirming'" class="point-charge-result__state" role="status">
        <strong>결제 승인 처리 중입니다…</strong>
        <p>잠시만 기다려 주세요.</p>
      </div>

      <div v-else-if="status === 'success'" class="point-charge-result__state">
        <strong>{{ chargedAmount.toLocaleString('ko-KR') }}P 충전이 완료되었습니다.</strong>
        <p>포인트 지갑에서 잔액을 확인할 수 있습니다.</p>
        <button type="button" @click="goToWallet">포인트 지갑으로 이동</button>
      </div>

      <div v-else class="point-charge-result__state" role="alert">
        <strong>충전 승인에 실패했습니다.</strong>
        <p>{{ errorMessage }}</p>
        <button type="button" @click="goToWallet">포인트 지갑으로 이동</button>
      </div>
    </section>
  </DefaultLayout>
</template>

<style scoped lang="scss">
.point-charge-result {
  display: grid;
  padding: var(--space-8);
}

.point-charge-result__state {
  display: grid;
  justify-items: center;
  gap: var(--space-3);
  padding: var(--space-8);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  font-size: 15px;
  line-height: 24px;
  text-align: center;
}

.point-charge-result__state strong {
  color: var(--color-text-primary);
  font-size: 18px;
  font-weight: var(--font-weight-extrabold);
  line-height: 26px;
}

.point-charge-result__state button {
  min-height: var(--button-height-small);
  padding: 0 var(--space-4);
  border: 0;
  border-radius: var(--radius-control);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-size: 14px;
  font-weight: var(--font-weight-bold);
}
</style>
