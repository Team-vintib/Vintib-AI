<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '@/domains/auth/stores/authStore'
import { getMySaleDetail } from '@/domains/my/api/myApi'
import {
  MY_ORDER_STATUS_LABELS,
  MY_SETTLEMENT_STATUS_LABELS,
} from '@/domains/my/constants/myMockData'
import type { MySaleItem } from '@/domains/my/types/my.types'
import { normalizeApiError } from '@/shared/api/http'
import { ROUTE_NAMES, ROUTE_PATHS } from '@/shared/constants/routes'
import DefaultLayout from '@/shared/layouts/DefaultLayout.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const sale = ref<MySaleItem | null>(null)
const loadState = ref<'idle' | 'loading' | 'success' | 'error' | 'guest'>('idle')
const errorMessage = ref('')

const isLoading = computed(() => loadState.value === 'loading')
const isGuest = computed(() => loadState.value === 'guest')
const hasLoadError = computed(() => loadState.value === 'error')
const saleId = computed(() => Number(route.params.saleId))

const saleAddress = computed(() => {
  if (!sale.value) {
    return ''
  }

  return `(${sale.value.postalCode}) ${sale.value.address} ${sale.value.detailAddress}`.trim()
})

const formatSaleDate = (value: string) =>
  new Intl.DateTimeFormat('ko-KR', {
    year: 'numeric',
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))

const loadSale = async () => {
  if (!authStore.isAuthenticated || !authStore.user) {
    loadState.value = 'guest'
    return
  }

  if (!Number.isFinite(saleId.value)) {
    loadState.value = 'error'
    errorMessage.value = '올바르지 않은 판매 내역입니다.'
    return
  }

  loadState.value = 'loading'
  errorMessage.value = ''

  try {
    sale.value = await getMySaleDetail(authStore.user.id, saleId.value)
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

const goToSales = () => {
  void router.push({ name: ROUTE_NAMES.MY, query: { section: 'sales' } })
}

onMounted(() => {
  void loadSale()
})
</script>

<template>
  <DefaultLayout content-max-width="1120px">
    <section class="my-sale-detail-page" aria-labelledby="my-sale-detail-title">
      <div v-if="isLoading" class="my-sale-detail-state" role="status">
        판매 상세 정보를 불러오는 중입니다.
      </div>

      <div v-else-if="isGuest" class="my-sale-detail-state">
        <strong>로그인이 필요합니다.</strong>
        <button type="button" @click="goToLogin">로그인으로 이동</button>
      </div>

      <div v-else-if="hasLoadError" class="my-sale-detail-state" role="alert">
        <strong>판매 상세 정보를 불러오지 못했습니다.</strong>
        <p>{{ errorMessage }}</p>
        <button type="button" @click="loadSale">다시 시도</button>
      </div>

      <template v-else-if="sale">
        <header class="my-sale-detail-page__header">
          <button type="button" @click="goToSales">목록으로</button>
          <h1 id="my-sale-detail-title" class="sr-only">판매 상세</h1>
        </header>

        <article class="my-sale-detail-card">
          <img :src="sale.productThumbnailUrl" :alt="sale.productName" />
          <div class="my-sale-detail-card__body">
            <span>{{ MY_ORDER_STATUS_LABELS[sale.status] }}</span>
            <h2>{{ sale.productName }}</h2>
            <p>{{ sale.buyerNickname }}</p>
            <strong>{{ sale.paidAmount.toLocaleString('ko-KR') }}P</strong>
          </div>
        </article>

        <section class="my-sale-detail-section" aria-labelledby="sale-payment-title">
          <div class="my-sale-detail-section__title">
            <h2 id="sale-payment-title">판매 정보</h2>
          </div>
          <dl class="my-sale-detail-grid">
            <div>
              <dt>판매 일시</dt>
              <dd>{{ formatSaleDate(sale.createdAt) }}</dd>
            </div>
            <div>
              <dt>판매 금액</dt>
              <dd>{{ sale.paidAmount.toLocaleString('ko-KR') }}P</dd>
            </div>
            <div>
              <dt>구매자</dt>
              <dd>{{ sale.buyerNickname }}</dd>
            </div>
            <div>
              <dt>주문 상태</dt>
              <dd>{{ MY_ORDER_STATUS_LABELS[sale.status] }}</dd>
            </div>
            <div>
              <dt>정산 상태</dt>
              <dd>{{ MY_SETTLEMENT_STATUS_LABELS[sale.settlementStatus] }}</dd>
            </div>
          </dl>
        </section>

        <section class="my-sale-detail-section" aria-labelledby="sale-shipping-title">
          <div class="my-sale-detail-section__title">
            <h2 id="sale-shipping-title">배송 정보</h2>
          </div>
          <dl class="my-sale-detail-grid">
            <div>
              <dt>받는 사람</dt>
              <dd>{{ sale.recipientName }}</dd>
            </div>
            <div>
              <dt>연락처</dt>
              <dd>{{ sale.recipientPhoneNumber }}</dd>
            </div>
            <div class="my-sale-detail-grid__wide">
              <dt>배송지</dt>
              <dd>{{ saleAddress }}</dd>
            </div>
          </dl>
        </section>
      </template>
    </section>
  </DefaultLayout>
</template>

<style scoped lang="scss">
.my-sale-detail-page {
  display: grid;
  gap: var(--space-5);
  padding: var(--space-8) var(--space-6) var(--space-12);
}

.my-sale-detail-page__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
}

.my-sale-detail-card__body span {
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

.my-sale-detail-page__header button,
.my-sale-detail-state button {
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

.my-sale-detail-card,
.my-sale-detail-section,
.my-sale-detail-state {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
  box-shadow: 0 1px 3px rgb(23 26 31 / 8%);
}

.my-sale-detail-card {
  display: grid;
  overflow: hidden;
  grid-template-columns: 240px minmax(0, 1fr);
}

.my-sale-detail-card img {
  width: 240px;
  height: 100%;
  min-height: 240px;
  object-fit: cover;
}

.my-sale-detail-card__body {
  display: grid;
  align-content: center;
  gap: var(--space-3);
  min-width: 0;
  padding: var(--space-6);
}

.my-sale-detail-card__body span {
  justify-self: start;
}

.my-sale-detail-card__body h2 {
  color: var(--color-text-primary);
  font-size: 24px;
  font-weight: var(--font-weight-extrabold);
  line-height: 34px;
}

.my-sale-detail-card__body p {
  color: var(--color-text-secondary);
  font-size: 14px;
  line-height: 22px;
}

.my-sale-detail-card__body strong {
  color: var(--color-text-primary);
  font-size: 22px;
  font-weight: var(--font-weight-extrabold);
  line-height: 32px;
}

.my-sale-detail-section {
  display: grid;
  gap: var(--space-4);
  padding: var(--space-5);
}

.my-sale-detail-section__title h2 {
  color: var(--color-text-primary);
  font-size: 18px;
  font-weight: var(--font-weight-extrabold);
  line-height: 26px;
}

.my-sale-detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-3);
}

.my-sale-detail-grid div {
  display: grid;
  gap: var(--space-1);
  min-width: 0;
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface-secondary);
}

.my-sale-detail-grid__wide {
  grid-column: 1 / -1;
}

.my-sale-detail-grid dt {
  color: var(--color-text-secondary);
  font-size: 12px;
  line-height: 18px;
}

.my-sale-detail-grid dd {
  color: var(--color-text-primary);
  font-size: 15px;
  font-weight: var(--font-weight-bold);
  line-height: 22px;
  overflow-wrap: anywhere;
}

.my-sale-detail-state {
  display: grid;
  justify-items: center;
  gap: var(--space-3);
  padding: var(--space-10);
  color: var(--color-text-secondary);
  font-size: 14px;
  line-height: 22px;
  text-align: center;
}

.my-sale-detail-state strong {
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

.my-sale-detail-page__header button:hover,
.my-sale-detail-state button:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.my-sale-detail-page__header button:focus-visible,
.my-sale-detail-state button:focus-visible {
  outline: 3px solid rgb(47 111 237 / 22%);
  outline-offset: 2px;
}

@media (max-width: 768px) {
  .my-sale-detail-page {
    padding: var(--space-6) 16px var(--space-10);
  }

  .my-sale-detail-page__header {
    flex-direction: column;
  }

  .my-sale-detail-card {
    grid-template-columns: 1fr;
  }

  .my-sale-detail-card img {
    width: 100%;
    min-height: 0;
    aspect-ratio: 4 / 3;
  }

  .my-sale-detail-grid {
    grid-template-columns: 1fr;
  }
}
</style>
