<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { ROUTE_NAMES } from '@/shared/constants/routes'
import DefaultLayout from '@/shared/layouts/DefaultLayout.vue'

// 토스 결제위젯 Redirect 방식 실패 콜백. 쿼리로 {code, message, orderId}가 붙어 온다.
const route = useRoute()
const router = useRouter()

const firstQueryValue = (value: unknown): string => {
  if (Array.isArray(value)) {
    return typeof value[0] === 'string' ? value[0] : ''
  }
  return typeof value === 'string' ? value : ''
}

const errorCode = computed(() => firstQueryValue(route.query.code))
const errorMessage = computed(
  () => firstQueryValue(route.query.message) || '결제가 취소되었거나 실패했습니다.',
)

const goToCharge = () => {
  void router.push({ name: ROUTE_NAMES.POINT, query: { section: 'charge' } })
}
</script>

<template>
  <DefaultLayout content-max-width="640px">
    <section class="point-charge-result" aria-live="polite">
      <div class="point-charge-result__state" role="alert">
        <strong>충전에 실패했습니다.</strong>
        <p>{{ errorMessage }}</p>
        <p v-if="errorCode" class="point-charge-result__code">오류 코드: {{ errorCode }}</p>
        <button type="button" @click="goToCharge">충전 화면으로 돌아가기</button>
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
  font-size: var(--font-size-body);
  line-height: var(--line-height-body);
  text-align: center;
}

.point-charge-result__state strong {
  color: var(--color-text-primary);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-extrabold);
  line-height: var(--line-height-lg);
}

.point-charge-result__code {
  color: var(--color-text-tertiary, var(--color-text-secondary));
  font-size: var(--font-size-caption);
}

.point-charge-result__state button {
  min-height: var(--button-height-small);
  padding: 0 var(--space-4);
  border: 0;
  border-radius: var(--radius-control);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-bold);
}
</style>
