<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '@/domains/auth/stores/authStore'
import { getMyOrderDetail } from '@/domains/my/api/myApi'
import { MY_ORDER_STATUS_LABELS } from '@/domains/my/constants/myMockData'
import type { MyOrderItem } from '@/domains/my/types/my.types'
import { normalizeApiError } from '@/shared/api/http'
import { ROUTE_NAMES, ROUTE_PATHS } from '@/shared/constants/routes'
import DefaultLayout from '@/shared/layouts/DefaultLayout.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const order = ref<MyOrderItem | null>(null)
const loadState = ref<'idle' | 'loading' | 'success' | 'error' | 'guest'>('idle')
const errorMessage = ref('')

const isLoading = computed(() => loadState.value === 'loading')
const isGuest = computed(() => loadState.value === 'guest')
const hasLoadError = computed(() => loadState.value === 'error')
const orderId = computed(() => Number(route.params.orderId))

const orderTypeLabel = computed(() => {
  if (!order.value) {
    return ''
  }

  return order.value.type === 'AUCTION' ? '경매 낙찰' : '즉시 구매'
})

const orderAddress = computed(() => {
  if (!order.value) {
    return ''
  }

  return `(${order.value.postalCode}) ${order.value.address} ${order.value.detailAddress}`.trim()
})

const formatOrderDate = (value: string) =>
  new Intl.DateTimeFormat('ko-KR', {
    year: 'numeric',
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))

const loadOrder = async () => {
  if (!authStore.isAuthenticated || !authStore.user) {
    loadState.value = 'guest'
    return
  }

  if (!Number.isFinite(orderId.value)) {
    loadState.value = 'error'
    errorMessage.value = '올바르지 않은 구매 내역입니다.'
    return
  }

  loadState.value = 'loading'
  errorMessage.value = ''

  try {
    order.value = await getMyOrderDetail(authStore.user.id, orderId.value)
    loadState.value = 'success'
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message
    loadState.value = 'error'
  }
}

const goToLogin = () => {
  void router.push({
    name: ROUTE_NAMES.AUTH_LOGIN,
    query: { redirect: route.fullPath || ROUTE_PATHS.MY },
  })
}

const goToOrders = () => {
  void router.push({ name: ROUTE_NAMES.MY, query: { section: 'orders' } })
}

onMounted(() => {
  void loadOrder()
})
</script>

<template>
  <DefaultLayout content-max-width="1120px">
    <section class="my-order-detail-page" aria-labelledby="my-order-detail-title">
      <div v-if="isLoading" class="my-order-detail-state" role="status">
        구매 상세 정보를 불러오는 중입니다.
      </div>

      <div v-else-if="isGuest" class="my-order-detail-state">
        <strong>로그인이 필요합니다.</strong>
        <button type="button" @click="goToLogin">로그인으로 이동</button>
      </div>

      <div v-else-if="hasLoadError" class="my-order-detail-state" role="alert">
        <strong>구매 상세 정보를 불러오지 못했습니다.</strong>
        <p>{{ errorMessage }}</p>
        <button type="button" @click="loadOrder">다시 시도</button>
      </div>

      <template v-else-if="order">
        <header class="my-order-detail-page__header">
          <button type="button" @click="goToOrders">목록으로</button>
          <h1 id="my-order-detail-title" class="sr-only">구매 상세</h1>
        </header>

        <article class="my-order-detail-card">
          <img :src="order.productThumbnailUrl" :alt="order.productName" />
          <div class="my-order-detail-card__body">
            <span>{{ orderTypeLabel }}</span>
            <h2>{{ order.productName }}</h2>
            <p>{{ order.sellerNickname }}</p>
            <strong>{{ order.paidAmount.toLocaleString('ko-KR') }}P</strong>
          </div>
        </article>

        <section class="my-order-detail-section" aria-labelledby="payment-title">
          <div class="my-order-detail-section__title">
            <h2 id="payment-title">결제 정보</h2>
          </div>
          <dl class="my-order-detail-grid">
            <div>
              <dt>구매 일시</dt>
              <dd>{{ formatOrderDate(order.createdAt) }}</dd>
            </div>
            <div>
              <dt>결제 금액</dt>
              <dd>{{ order.paidAmount.toLocaleString('ko-KR') }}P</dd>
            </div>
            <div>
              <dt>구매 방식</dt>
              <dd>{{ orderTypeLabel }}</dd>
            </div>
            <div>
              <dt>주문 상태</dt>
              <dd>{{ MY_ORDER_STATUS_LABELS[order.status] }}</dd>
            </div>
          </dl>
        </section>

        <section class="my-order-detail-section" aria-labelledby="shipping-title">
          <div class="my-order-detail-section__title">
            <h2 id="shipping-title">배송 정보</h2>
          </div>
          <dl class="my-order-detail-grid">
            <div>
              <dt>받는 사람</dt>
              <dd>{{ order.recipientName }}</dd>
            </div>
            <div>
              <dt>연락처</dt>
              <dd>{{ order.recipientPhoneNumber }}</dd>
            </div>
            <div class="my-order-detail-grid__wide">
              <dt>배송지</dt>
              <dd>{{ orderAddress }}</dd>
            </div>
          </dl>
        </section>
      </template>
    </section>
  </DefaultLayout>
</template>

<style scoped lang="scss">
.my-order-detail-page {
  display: grid;
  gap: var(--space-5);
  padding: var(--space-8) var(--space-6) var(--space-12);
}

.my-order-detail-page__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
}

.my-order-detail-card__body span {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 24px;
  padding: 2px 10px;
  border-radius: var(--radius-badge);
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-size: 12px;
  font-weight: var(--font-weight-bold);
  line-height: 18px;
}

.my-order-detail-page__header button,
.my-order-detail-state button {
  min-height: 40px;
  padding: 0 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-size: 14px;
  font-weight: var(--font-weight-bold);
  line-height: 22px;
  cursor: pointer;
}

.my-order-detail-card,
.my-order-detail-section,
.my-order-detail-state {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
  box-shadow: 0 1px 3px rgb(23 26 31 / 8%);
}

.my-order-detail-card {
  display: grid;
  overflow: hidden;
  grid-template-columns: 240px minmax(0, 1fr);
}

.my-order-detail-card img {
  width: 240px;
  height: 100%;
  min-height: 240px;
  object-fit: cover;
}

.my-order-detail-card__body {
  display: grid;
  align-content: center;
  gap: var(--space-3);
  min-width: 0;
  padding: var(--space-6);
}

.my-order-detail-card__body span {
  justify-self: start;
}

.my-order-detail-card__body h2 {
  color: var(--color-text-primary);
  font-size: 24px;
  font-weight: var(--font-weight-extrabold);
  line-height: 34px;
}

.my-order-detail-card__body p {
  color: var(--color-text-secondary);
  font-size: 14px;
  line-height: 22px;
}

.my-order-detail-card__body strong {
  color: var(--color-text-primary);
  font-size: 22px;
  font-weight: var(--font-weight-extrabold);
  line-height: 32px;
}

.my-order-detail-section {
  display: grid;
  gap: var(--space-4);
  padding: var(--space-5);
}

.my-order-detail-section__title h2 {
  color: var(--color-text-primary);
  font-size: 18px;
  font-weight: var(--font-weight-extrabold);
  line-height: 26px;
}

.my-order-detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-3);
}

.my-order-detail-grid div {
  display: grid;
  gap: var(--space-1);
  min-width: 0;
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface-secondary);
}

.my-order-detail-grid__wide {
  grid-column: 1 / -1;
}

.my-order-detail-grid dt {
  color: var(--color-text-secondary);
  font-size: 12px;
  line-height: 18px;
}

.my-order-detail-grid dd {
  color: var(--color-text-primary);
  font-size: 15px;
  font-weight: var(--font-weight-bold);
  line-height: 22px;
  overflow-wrap: anywhere;
}

.my-order-detail-state {
  display: grid;
  justify-items: center;
  gap: var(--space-3);
  padding: var(--space-10);
  color: var(--color-text-secondary);
  font-size: 14px;
  line-height: 22px;
  text-align: center;
}

.my-order-detail-state strong {
  color: var(--color-text-primary);
  font-size: 16px;
  line-height: 24px;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  border: 0;
  margin: -1px;
  white-space: nowrap;
}

.my-order-detail-page__header button:hover,
.my-order-detail-state button:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.my-order-detail-page__header button:focus-visible,
.my-order-detail-state button:focus-visible {
  outline: 3px solid rgb(47 111 237 / 22%);
  outline-offset: 2px;
}

@media (max-width: 768px) {
  .my-order-detail-page {
    padding: var(--space-6) 16px var(--space-10);
  }

  .my-order-detail-page__header {
    flex-direction: column;
  }

  .my-order-detail-card {
    grid-template-columns: 1fr;
  }

  .my-order-detail-card img {
    width: 100%;
    min-height: 0;
    aspect-ratio: 4 / 3;
  }

  .my-order-detail-grid {
    grid-template-columns: 1fr;
  }
}
</style>
