<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '@/domains/auth/stores/authStore'
import {
  MY_ORDER_STATUS_LABELS,
  MY_SETTLEMENT_STATUS_LABELS,
} from '@/domains/my/constants/myMockData'
import type { MySettlementStatus } from '@/domains/my/types/my.types'
import { getOrderDetail } from '@/domains/order/api/orderApi'
import type { OrderSummary } from '@/domains/order/types/order.types'
import { getProductPrimaryImageUrl } from '@/domains/product/api/productApi'
import { getRefunds, reviewRefund } from '@/domains/refund/api/refundApi'
import { REFUND_REASON_LABELS, REFUND_STATUS_LABELS } from '@/domains/refund/constants/refundOptions'
import type { RefundRequestInfo } from '@/domains/refund/types/refund.types'
import { COURIER_OPTIONS } from '@/domains/shipping/constants/courierOptions'
import { getShipment, registerShipment } from '@/domains/shipping/api/shipmentApi'
import type { CourierCode, OrderShipmentInfo } from '@/domains/shipping/types/shipping.types'
import { normalizeApiError } from '@/shared/api/http'
import { ROUTE_NAMES, ROUTE_PATHS } from '@/shared/constants/routes'
import DefaultLayout from '@/shared/layouts/DefaultLayout.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const order = ref<OrderSummary | null>(null)
const shipment = ref<OrderShipmentInfo | null>(null)
const refunds = ref<RefundRequestInfo[]>([])
const productThumbnailUrl = ref('')
const loadState = ref<'idle' | 'loading' | 'success' | 'error' | 'guest'>('idle')
const errorMessage = ref('')

const isLoading = computed(() => loadState.value === 'loading')
const isGuest = computed(() => loadState.value === 'guest')
const hasLoadError = computed(() => loadState.value === 'error')
const saleId = computed(() => Number(route.params.saleId))

const settlementStatus = computed<MySettlementStatus>(() => {
  if (!order.value) return 'ESCROW'
  if (order.value.status === 'SETTLED') return 'SETTLED'
  if (order.value.status === 'CONFIRMED') return 'PENDING'
  if (order.value.status === 'REFUNDED') return 'REFUND_REQUESTED'
  return 'ESCROW'
})

const hasBuyerAddress = computed(() => !!shipment.value && shipment.value.address1 !== '')
const canRegisterShipment = computed(
  () => order.value?.status === 'PAID' && hasBuyerAddress.value && !shipment.value?.trackingNumber,
)
const activeRefund = computed(() => refunds.value.find((refund) => refund.status === 'REQUESTED') ?? null)
const latestRefund = computed(() => refunds.value[0] ?? null)

const isShipmentFormOpen = ref(false)
const shipmentCourierCode = ref<CourierCode>('CJ')
const shipmentTrackingNumber = ref('')
const isShipmentSubmitting = ref(false)
const shipmentErrorMessage = ref('')

const isRefundReviewSubmitting = ref(false)
const refundReviewErrorMessage = ref('')
const rejectionReasonInput = ref('')

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
    const orderDetail = await getOrderDetail(saleId.value)
    order.value = orderDetail

    const [shipmentResult, refundsResult, thumbnailUrl] = await Promise.all([
      getShipment(saleId.value).catch(() => null),
      getRefunds(saleId.value).catch(() => []),
      getProductPrimaryImageUrl(orderDetail.product.id).catch(() => ''),
    ])

    shipment.value = shipmentResult
    refunds.value = refundsResult
    productThumbnailUrl.value = thumbnailUrl
    loadState.value = 'success'
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message
    loadState.value = 'error'
  }
}

const refreshOrderStatus = async () => {
  if (!order.value) return

  order.value = await getOrderDetail(order.value.orderId).catch(() => order.value)
}

const openShipmentForm = () => {
  shipmentCourierCode.value = 'CJ'
  shipmentTrackingNumber.value = ''
  shipmentErrorMessage.value = ''
  isShipmentFormOpen.value = true
}

const submitShipment = async () => {
  if (!order.value || !shipmentTrackingNumber.value.trim()) return

  isShipmentSubmitting.value = true
  shipmentErrorMessage.value = ''

  try {
    shipment.value = await registerShipment(order.value.orderId, {
      courierCode: shipmentCourierCode.value,
      trackingNumber: shipmentTrackingNumber.value.trim(),
    })
    isShipmentFormOpen.value = false
    await refreshOrderStatus()
  } catch (error) {
    shipmentErrorMessage.value = normalizeApiError(error).message
  } finally {
    isShipmentSubmitting.value = false
  }
}

const approveRefund = async () => {
  if (!activeRefund.value) return

  isRefundReviewSubmitting.value = true
  refundReviewErrorMessage.value = ''

  try {
    const reviewed = await reviewRefund(activeRefund.value.refundId, { decision: 'APPROVED' })
    refunds.value = refunds.value.map((refund) => (refund.refundId === reviewed.refundId ? reviewed : refund))
    await refreshOrderStatus()
  } catch (error) {
    refundReviewErrorMessage.value = normalizeApiError(error).message
  } finally {
    isRefundReviewSubmitting.value = false
  }
}

const rejectRefund = async () => {
  if (!activeRefund.value || !rejectionReasonInput.value.trim()) return

  isRefundReviewSubmitting.value = true
  refundReviewErrorMessage.value = ''

  try {
    const reviewed = await reviewRefund(activeRefund.value.refundId, {
      decision: 'REJECTED',
      rejectionReason: rejectionReasonInput.value.trim(),
    })
    refunds.value = refunds.value.map((refund) => (refund.refundId === reviewed.refundId ? reviewed : refund))
    rejectionReasonInput.value = ''
  } catch (error) {
    refundReviewErrorMessage.value = normalizeApiError(error).message
  } finally {
    isRefundReviewSubmitting.value = false
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

      <template v-else-if="order">
        <header class="my-sale-detail-page__header">
          <button type="button" @click="goToSales">목록으로</button>
          <h1 id="my-sale-detail-title" class="sr-only">판매 상세</h1>
        </header>

        <article class="my-sale-detail-card">
          <img :src="productThumbnailUrl" :alt="order.product.title" />
          <div class="my-sale-detail-card__body">
            <span>{{ MY_ORDER_STATUS_LABELS[order.status] }}</span>
            <h2>{{ order.product.title }}</h2>
            <p>{{ order.buyerNickname }}</p>
            <strong>{{ order.orderPrice.toLocaleString('ko-KR') }}P</strong>
          </div>
        </article>

        <section class="my-sale-detail-section" aria-labelledby="product-title">
          <div class="my-sale-detail-section__title">
            <h2 id="product-title">상품 정보</h2>
          </div>
          <dl class="my-sale-detail-grid">
            <div>
              <dt>상품 상태</dt>
              <dd>{{ order.product.conditionGrade ?? '-' }}</dd>
            </div>
            <div>
              <dt>사이즈</dt>
              <dd>{{ order.product.sizeLabel ?? '-' }}</dd>
            </div>
          </dl>
        </section>

        <section class="my-sale-detail-section" aria-labelledby="sale-payment-title">
          <div class="my-sale-detail-section__title">
            <h2 id="sale-payment-title">판매 정보</h2>
          </div>
          <dl class="my-sale-detail-grid">
            <div>
              <dt>판매 일시</dt>
              <dd>{{ formatSaleDate(order.createdAt) }}</dd>
            </div>
            <div>
              <dt>판매 금액</dt>
              <dd>{{ order.orderPrice.toLocaleString('ko-KR') }}P</dd>
            </div>
            <div>
              <dt>구매자</dt>
              <dd>{{ order.buyerNickname }}</dd>
            </div>
            <div>
              <dt>주문 상태</dt>
              <dd>{{ MY_ORDER_STATUS_LABELS[order.status] }}</dd>
            </div>
            <div>
              <dt>정산 상태</dt>
              <dd>{{ MY_SETTLEMENT_STATUS_LABELS[settlementStatus] }}</dd>
            </div>
          </dl>
        </section>

        <section class="my-sale-detail-section" aria-labelledby="sale-shipping-title">
          <div class="my-sale-detail-section__title">
            <h2 id="sale-shipping-title">구매자 배송지</h2>
          </div>
          <dl v-if="hasBuyerAddress && shipment" class="my-sale-detail-grid">
            <div>
              <dt>받는 사람</dt>
              <dd>{{ shipment.recipientName }}</dd>
            </div>
            <div>
              <dt>연락처</dt>
              <dd>{{ shipment.recipientPhone }}</dd>
            </div>
            <div class="my-sale-detail-grid__wide">
              <dt>배송지</dt>
              <dd>({{ shipment.zipcode }}) {{ shipment.address1 }} {{ shipment.address2 }}</dd>
            </div>
          </dl>
          <p v-else class="my-sale-detail-empty">구매자가 아직 배송지를 등록하지 않았습니다.</p>
        </section>

        <section class="my-sale-detail-section" aria-labelledby="sale-delivery-title">
          <div class="my-sale-detail-section__title">
            <h2 id="sale-delivery-title">배송 정보</h2>
            <button v-if="canRegisterShipment" type="button" @click="openShipmentForm">송장 등록</button>
          </div>

          <form v-if="isShipmentFormOpen" class="my-sale-detail-form" @submit.prevent="submitShipment">
            <div class="my-sale-detail-form__field">
              <label for="sale-courier-code">택배사</label>
              <select id="sale-courier-code" v-model="shipmentCourierCode">
                <option v-for="option in COURIER_OPTIONS" :key="option.code" :value="option.code">
                  {{ option.label }}
                </option>
              </select>
            </div>
            <div class="my-sale-detail-form__field">
              <label for="sale-tracking-number">송장 번호</label>
              <input id="sale-tracking-number" v-model="shipmentTrackingNumber" type="text" required />
            </div>
            <p v-if="shipmentErrorMessage" class="my-sale-detail-form__error" role="alert">
              {{ shipmentErrorMessage }}
            </p>
            <div class="my-sale-detail-form__actions">
              <button type="button" @click="isShipmentFormOpen = false">취소</button>
              <button type="submit" :disabled="isShipmentSubmitting || !shipmentTrackingNumber.trim()">
                {{ isShipmentSubmitting ? '등록 중…' : '등록' }}
              </button>
            </div>
          </form>

          <dl v-else-if="shipment?.trackingNumber" class="my-sale-detail-grid">
            <div>
              <dt>택배사</dt>
              <dd>{{ shipment.courierName }}</dd>
            </div>
            <div>
              <dt>송장 번호</dt>
              <dd>{{ shipment.trackingNumber }}</dd>
            </div>
            <div>
              <dt>배송 상태</dt>
              <dd>{{ MY_ORDER_STATUS_LABELS[order.status] }}</dd>
            </div>
            <div>
              <dt>발송/도착 일시</dt>
              <dd>
                {{ shipment.shippedAt ? formatSaleDate(shipment.shippedAt) : '-' }} /
                {{ shipment.deliveredAt ? formatSaleDate(shipment.deliveredAt) : '-' }}
              </dd>
            </div>
          </dl>

          <p v-else-if="!canRegisterShipment" class="my-sale-detail-empty">아직 송장이 등록되지 않았습니다.</p>
        </section>

        <section
          v-if="activeRefund || latestRefund"
          class="my-sale-detail-section"
          aria-labelledby="sale-refund-title"
        >
          <div class="my-sale-detail-section__title">
            <h2 id="sale-refund-title">환불 요청</h2>
          </div>

          <dl v-if="latestRefund" class="my-sale-detail-grid">
            <div>
              <dt>상태</dt>
              <dd>{{ REFUND_STATUS_LABELS[latestRefund.status] }}</dd>
            </div>
            <div>
              <dt>사유</dt>
              <dd>{{ REFUND_REASON_LABELS[latestRefund.reason] }}</dd>
            </div>
            <div class="my-sale-detail-grid__wide">
              <dt>상세 사유</dt>
              <dd>{{ latestRefund.detailReason }}</dd>
            </div>
          </dl>

          <template v-if="activeRefund">
            <p v-if="refundReviewErrorMessage" class="my-sale-detail-form__error" role="alert">
              {{ refundReviewErrorMessage }}
            </p>
            <div class="my-sale-detail-form__field">
              <label for="sale-rejection-reason">거절 사유(거절 시 필수)</label>
              <textarea id="sale-rejection-reason" v-model="rejectionReasonInput" rows="2"></textarea>
            </div>
            <div class="my-sale-detail-form__actions">
              <button
                type="button"
                :disabled="isRefundReviewSubmitting || !rejectionReasonInput.trim()"
                @click="rejectRefund"
              >
                거절
              </button>
              <button type="button" :disabled="isRefundReviewSubmitting" @click="approveRefund">
                승인
              </button>
            </div>
          </template>
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
  min-height: var(--badge-height-compact);
  padding: 2px 10px;
  border-radius: var(--radius-badge);
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-snug);
}

.my-sale-detail-page__header button,
.my-sale-detail-state button,
.my-sale-detail-section__title button,
.my-sale-detail-form__actions button {
  min-height: var(--button-height-sm);
  padding: 0 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-relaxed);
  cursor: pointer;
}

.my-sale-detail-card,
.my-sale-detail-section,
.my-sale-detail-state {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
  box-shadow: none;
}

.my-sale-detail-card {
  display: grid;
  overflow: hidden;
  grid-template-columns: 240px minmax(0, 1fr);
}

.my-sale-detail-card img {
  width: 240px;
  height: 100%;
  min-height: var(--surface-min-height-sm);
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
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-extrabold);
  line-height: var(--line-height-2xl-loose);
}

.my-sale-detail-card__body p {
  color: var(--color-text-secondary);
  font-size: var(--font-size-button-small);
  line-height: var(--line-height-relaxed);
}

.my-sale-detail-card__body strong {
  color: var(--color-text-primary);
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-extrabold);
  line-height: var(--line-height-2xl);
}

.my-sale-detail-section {
  display: grid;
  gap: var(--space-4);
  padding: var(--space-5);
}

.my-sale-detail-section__title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}

.my-sale-detail-section__title h2 {
  color: var(--color-text-primary);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-extrabold);
  line-height: var(--line-height-lg);
}

.my-sale-detail-empty {
  color: var(--color-text-muted);
  font-size: var(--font-size-caption);
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
  font-size: var(--font-size-xs);
  line-height: var(--line-height-snug);
}

.my-sale-detail-grid dd {
  color: var(--color-text-primary);
  font-size: var(--font-size-body);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-relaxed);
  overflow-wrap: anywhere;
}

.my-sale-detail-form {
  display: grid;
  gap: var(--space-3);
}

.my-sale-detail-form__field {
  display: grid;
  gap: var(--space-1);
}

.my-sale-detail-form__field label {
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
}

.my-sale-detail-form__field input,
.my-sale-detail-form__field select,
.my-sale-detail-form__field textarea {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-size: var(--font-size-body);
}

.my-sale-detail-form__error {
  color: var(--color-danger, #d64545);
  font-size: var(--font-size-caption);
}

.my-sale-detail-form__actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}

.my-sale-detail-state {
  display: grid;
  justify-items: center;
  gap: var(--space-3);
  padding: var(--space-10);
  color: var(--color-text-secondary);
  font-size: var(--font-size-button-small);
  line-height: var(--line-height-relaxed);
  text-align: center;
}

.my-sale-detail-state strong {
  color: var(--color-text-primary);
  font-size: var(--font-size-md);
  line-height: var(--line-height-body);
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
.my-sale-detail-state button:hover,
.my-sale-detail-section__title button:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.my-sale-detail-page__header button:focus-visible,
.my-sale-detail-state button:focus-visible {
  outline: var(--focus-ring-width) solid var(--overlay-focus-ring);
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
