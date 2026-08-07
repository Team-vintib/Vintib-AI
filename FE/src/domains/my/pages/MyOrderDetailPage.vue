<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '@/domains/auth/stores/authStore'
import { MY_ORDER_STATUS_LABELS } from '@/domains/my/constants/myMockData'
import { confirmOrder, getOrderDetail, updateOrderAddress } from '@/domains/order/api/orderApi'
import type { OrderAddressInput, OrderSummary } from '@/domains/order/types/order.types'
import { getProductPrimaryImageUrl } from '@/domains/product/api/productApi'
import { createRefund, getRefunds } from '@/domains/refund/api/refundApi'
import { REFUND_REASON_OPTIONS, REFUND_STATUS_LABELS } from '@/domains/refund/constants/refundOptions'
import type { RefundReason, RefundRequestInfo } from '@/domains/refund/types/refund.types'
import { getShipment } from '@/domains/shipping/api/shipmentApi'
import type { OrderShipmentInfo } from '@/domains/shipping/types/shipping.types'
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
const orderId = computed(() => Number(route.params.orderId))

const canEditAddress = computed(() => order.value?.status === 'PAID')
const canConfirm = computed(() => order.value?.status === 'DELIVERED')
/**
 * BE의 웹훅 구독 실패 폴백(deliveryapi.co.kr 자격증명 없는 환경 등)은 order.status만 DELIVERED로
 * 즉시 확정하고 shipment.trackingStatus는 영영 null로 남긴다(실 웹훅에서만 채워짐) — order.status를
 * 상한으로 같이 봐야 이 경우에도 "배송 완료"가 반영된다.
 */
const shipmentStatusLabel = computed(() => {
  if (shipment.value?.trackingStatusLabel) return shipment.value.trackingStatusLabel
  if (order.value?.status === 'DELIVERED') return MY_ORDER_STATUS_LABELS.DELIVERED
  return '송장 등록됨'
})
const activeRefund = computed(() => refunds.value.find((refund) => refund.status === 'REQUESTED') ?? null)
const canRequestRefund = computed(
  () =>
    !!order.value &&
    ['PAID', 'SHIPPING', 'DELIVERED'].includes(order.value.status) &&
    !activeRefund.value,
)
const latestRefund = computed(() => refunds.value[0] ?? null)

const isAddressFormOpen = ref(false)
const addressForm = ref<OrderAddressInput>({
  recipientName: '',
  recipientPhone: '',
  zipcode: '',
  address1: '',
  address2: '',
})
const isAddressSubmitting = ref(false)
const addressErrorMessage = ref('')

const isConfirmSubmitting = ref(false)
const confirmErrorMessage = ref('')

const isRefundFormOpen = ref(false)
const refundReason = ref<RefundReason>('NOT_AS_DESCRIBED')
const refundDetailReason = ref('')
const isRefundSubmitting = ref(false)
const refundErrorMessage = ref('')

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
    const orderDetail = await getOrderDetail(orderId.value)
    order.value = orderDetail

    const [shipmentResult, refundsResult, thumbnailUrl] = await Promise.all([
      getShipment(orderId.value).catch(() => null),
      getRefunds(orderId.value).catch(() => []),
      getProductPrimaryImageUrl(orderDetail.product.id).catch(() => ''),
    ])

    shipment.value = shipmentResult
    refunds.value = refundsResult
    productThumbnailUrl.value = thumbnailUrl
    prefillAddressForm()
    loadState.value = 'success'
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message
    loadState.value = 'error'
  }
}

const prefillAddressForm = () => {
  if (!shipment.value) return

  addressForm.value = {
    recipientName: shipment.value.recipientName,
    recipientPhone: shipment.value.recipientPhone,
    zipcode: shipment.value.zipcode,
    address1: shipment.value.address1,
    address2: shipment.value.address2 ?? '',
  }
}

const openAddressForm = () => {
  prefillAddressForm()
  addressErrorMessage.value = ''
  isAddressFormOpen.value = true
}

const submitAddress = async () => {
  if (!order.value) return

  isAddressSubmitting.value = true
  addressErrorMessage.value = ''

  try {
    shipment.value = await updateOrderAddress(order.value.orderId, {
      ...addressForm.value,
      address2: addressForm.value.address2 || undefined,
    })
    isAddressFormOpen.value = false
  } catch (error) {
    addressErrorMessage.value = normalizeApiError(error).message
  } finally {
    isAddressSubmitting.value = false
  }
}

const submitConfirm = async () => {
  if (!order.value) return

  isConfirmSubmitting.value = true
  confirmErrorMessage.value = ''

  try {
    order.value = await confirmOrder(order.value.orderId)
  } catch (error) {
    confirmErrorMessage.value = normalizeApiError(error).message
  } finally {
    isConfirmSubmitting.value = false
  }
}

const openRefundForm = () => {
  refundReason.value = 'NOT_AS_DESCRIBED'
  refundDetailReason.value = ''
  refundErrorMessage.value = ''
  isRefundFormOpen.value = true
}

const submitRefund = async () => {
  if (!order.value || !refundDetailReason.value.trim()) return

  isRefundSubmitting.value = true
  refundErrorMessage.value = ''

  try {
    const created = await createRefund(order.value.orderId, {
      reason: refundReason.value,
      detailReason: refundDetailReason.value.trim(),
    })
    refunds.value = [created, ...refunds.value]
    isRefundFormOpen.value = false
  } catch (error) {
    refundErrorMessage.value = normalizeApiError(error).message
  } finally {
    isRefundSubmitting.value = false
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
          <img :src="productThumbnailUrl" :alt="order.product.title" />
          <div class="my-order-detail-card__body">
            <span>{{ MY_ORDER_STATUS_LABELS[order.status] }}</span>
            <h2>{{ order.product.title }}</h2>
            <p>{{ order.sellerNickname }}</p>
            <strong>{{ order.orderPrice.toLocaleString('ko-KR') }}P</strong>
          </div>
        </article>

        <section class="my-order-detail-section" aria-labelledby="product-title">
          <div class="my-order-detail-section__title">
            <h2 id="product-title">상품 정보</h2>
          </div>
          <dl class="my-order-detail-grid">
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

        <section class="my-order-detail-section" aria-labelledby="payment-title">
          <div class="my-order-detail-section__title">
            <h2 id="payment-title">구매 정보</h2>
          </div>
          <dl class="my-order-detail-grid">
            <div>
              <dt>구매 일시</dt>
              <dd>{{ formatOrderDate(order.createdAt) }}</dd>
            </div>
            <div>
              <dt>결제 금액</dt>
              <dd>{{ order.orderPrice.toLocaleString('ko-KR') }}P</dd>
            </div>
            <div>
              <dt>구매 방식</dt>
              <dd>즉시 구매</dd>
            </div>
            <div>
              <dt>주문 상태</dt>
              <dd>{{ MY_ORDER_STATUS_LABELS[order.status] }}</dd>
            </div>
          </dl>
        </section>

        <section class="my-order-detail-section" aria-labelledby="shipping-title">
          <div class="my-order-detail-section__title">
            <h2 id="shipping-title">배송지</h2>
            <button v-if="canEditAddress" type="button" @click="openAddressForm">
              {{ shipment ? '배송지 수정' : '배송지 등록' }}
            </button>
          </div>

          <form v-if="isAddressFormOpen" class="my-order-detail-form" @submit.prevent="submitAddress">
            <div class="my-order-detail-form__field">
              <label for="order-recipient-name">받는 사람</label>
              <input id="order-recipient-name" v-model="addressForm.recipientName" type="text" required />
            </div>
            <div class="my-order-detail-form__field">
              <label for="order-recipient-phone">연락처</label>
              <input id="order-recipient-phone" v-model="addressForm.recipientPhone" type="tel" required />
            </div>
            <div class="my-order-detail-form__field">
              <label for="order-zipcode">우편번호</label>
              <input id="order-zipcode" v-model="addressForm.zipcode" type="text" required />
            </div>
            <div class="my-order-detail-form__field">
              <label for="order-address1">주소</label>
              <input id="order-address1" v-model="addressForm.address1" type="text" required />
            </div>
            <div class="my-order-detail-form__field">
              <label for="order-address2">상세 주소</label>
              <input id="order-address2" v-model="addressForm.address2" type="text" />
            </div>
            <p v-if="addressErrorMessage" class="my-order-detail-form__error" role="alert">
              {{ addressErrorMessage }}
            </p>
            <div class="my-order-detail-form__actions">
              <button type="button" @click="isAddressFormOpen = false">취소</button>
              <button type="submit" :disabled="isAddressSubmitting">
                {{ isAddressSubmitting ? '저장 중…' : '저장' }}
              </button>
            </div>
          </form>

          <dl v-else-if="shipment" class="my-order-detail-grid">
            <div>
              <dt>받는 사람</dt>
              <dd>{{ shipment.recipientName }}</dd>
            </div>
            <div>
              <dt>연락처</dt>
              <dd>{{ shipment.recipientPhone }}</dd>
            </div>
            <div class="my-order-detail-grid__wide">
              <dt>배송지</dt>
              <dd>({{ shipment.zipcode }}) {{ shipment.address1 }} {{ shipment.address2 }}</dd>
            </div>
          </dl>

          <p v-else class="my-order-detail-empty">등록된 배송지가 없습니다.</p>
        </section>

        <section class="my-order-detail-section" aria-labelledby="delivery-title">
          <div class="my-order-detail-section__title">
            <h2 id="delivery-title">배송 정보</h2>
          </div>
          <dl v-if="shipment?.trackingNumber" class="my-order-detail-grid">
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
              <dd>{{ shipmentStatusLabel }}</dd>
            </div>
            <div>
              <dt>발송/도착 일시</dt>
              <dd>
                {{ shipment.shippedAt ? formatOrderDate(shipment.shippedAt) : '-' }} /
                {{ shipment.deliveredAt ? formatOrderDate(shipment.deliveredAt) : '-' }}
              </dd>
            </div>
          </dl>
          <p v-else class="my-order-detail-empty">아직 송장이 등록되지 않았습니다.</p>
        </section>

        <section v-if="canConfirm" class="my-order-detail-section" aria-labelledby="confirm-title">
          <div class="my-order-detail-section__title">
            <h2 id="confirm-title">구매 확정</h2>
          </div>
          <p class="my-order-detail-help">
            상품을 확인하셨다면 구매를 확정해 주세요. 확정 후에는 판매자에게 대금이 정산됩니다.
          </p>
          <p v-if="confirmErrorMessage" class="my-order-detail-form__error" role="alert">
            {{ confirmErrorMessage }}
          </p>
          <button type="button" class="my-order-detail-primary-action" :disabled="isConfirmSubmitting" @click="submitConfirm">
            {{ isConfirmSubmitting ? '처리 중…' : '구매 확정하기' }}
          </button>
        </section>

        <section class="my-order-detail-section" aria-labelledby="refund-title">
          <div class="my-order-detail-section__title">
            <h2 id="refund-title">환불</h2>
            <button v-if="canRequestRefund" type="button" @click="openRefundForm">환불 요청</button>
          </div>

          <form v-if="isRefundFormOpen" class="my-order-detail-form" @submit.prevent="submitRefund">
            <div class="my-order-detail-form__field">
              <label for="refund-reason">환불 사유</label>
              <select id="refund-reason" v-model="refundReason">
                <option v-for="option in REFUND_REASON_OPTIONS" :key="option.reason" :value="option.reason">
                  {{ option.label }}
                </option>
              </select>
            </div>
            <div class="my-order-detail-form__field">
              <label for="refund-detail">상세 사유</label>
              <textarea id="refund-detail" v-model="refundDetailReason" rows="3" required></textarea>
            </div>
            <p v-if="refundErrorMessage" class="my-order-detail-form__error" role="alert">
              {{ refundErrorMessage }}
            </p>
            <div class="my-order-detail-form__actions">
              <button type="button" @click="isRefundFormOpen = false">취소</button>
              <button type="submit" :disabled="isRefundSubmitting || !refundDetailReason.trim()">
                {{ isRefundSubmitting ? '요청 중…' : '환불 요청하기' }}
              </button>
            </div>
          </form>

          <dl v-else-if="latestRefund" class="my-order-detail-grid">
            <div>
              <dt>상태</dt>
              <dd>{{ REFUND_STATUS_LABELS[latestRefund.status] }}</dd>
            </div>
            <div>
              <dt>요청 일시</dt>
              <dd>{{ formatOrderDate(latestRefund.requestedAt) }}</dd>
            </div>
            <div class="my-order-detail-grid__wide">
              <dt>상세 사유</dt>
              <dd>{{ latestRefund.detailReason }}</dd>
            </div>
            <div v-if="latestRefund.rejectionReason" class="my-order-detail-grid__wide">
              <dt>거절 사유</dt>
              <dd>{{ latestRefund.rejectionReason }}</dd>
            </div>
          </dl>

          <p v-else class="my-order-detail-empty">환불 요청 내역이 없습니다.</p>
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
  min-height: var(--badge-height-compact);
  padding: 2px 10px;
  border-radius: var(--radius-badge);
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-snug);
}

.my-order-detail-page__header button,
.my-order-detail-state button,
.my-order-detail-section__title button,
.my-order-detail-form__actions button {
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

.my-order-detail-primary-action {
  min-height: var(--button-height-sm);
  padding: 0 20px;
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-control);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-bold);
  cursor: pointer;
}

.my-order-detail-primary-action:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.my-order-detail-card,
.my-order-detail-section,
.my-order-detail-state {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
  box-shadow: none;
}

.my-order-detail-card {
  display: grid;
  overflow: hidden;
  grid-template-columns: 240px minmax(0, 1fr);
}

.my-order-detail-card img {
  width: 240px;
  height: 100%;
  min-height: var(--surface-min-height-sm);
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
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-extrabold);
  line-height: var(--line-height-2xl-loose);
}

.my-order-detail-card__body p {
  color: var(--color-text-secondary);
  font-size: var(--font-size-button-small);
  line-height: var(--line-height-relaxed);
}

.my-order-detail-card__body strong {
  color: var(--color-text-primary);
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-extrabold);
  line-height: var(--line-height-2xl);
}

.my-order-detail-section {
  display: grid;
  gap: var(--space-4);
  padding: var(--space-5);
}

.my-order-detail-section__title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}

.my-order-detail-section__title h2 {
  color: var(--color-text-primary);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-extrabold);
  line-height: var(--line-height-lg);
}

.my-order-detail-help {
  color: var(--color-text-secondary);
  font-size: var(--font-size-caption);
  line-height: var(--line-height-relaxed);
}

.my-order-detail-empty {
  color: var(--color-text-muted);
  font-size: var(--font-size-caption);
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
  font-size: var(--font-size-xs);
  line-height: var(--line-height-snug);
}

.my-order-detail-grid dd {
  color: var(--color-text-primary);
  font-size: var(--font-size-body);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-relaxed);
  overflow-wrap: anywhere;
}

.my-order-detail-form {
  display: grid;
  gap: var(--space-3);
}

.my-order-detail-form__field {
  display: grid;
  gap: var(--space-1);
}

.my-order-detail-form__field label {
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
}

.my-order-detail-form__field input,
.my-order-detail-form__field select,
.my-order-detail-form__field textarea {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-size: var(--font-size-body);
}

.my-order-detail-form__error {
  color: var(--color-danger, #d64545);
  font-size: var(--font-size-caption);
}

.my-order-detail-form__actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}

.my-order-detail-state {
  display: grid;
  justify-items: center;
  gap: var(--space-3);
  padding: var(--space-10);
  color: var(--color-text-secondary);
  font-size: var(--font-size-button-small);
  line-height: var(--line-height-relaxed);
  text-align: center;
}

.my-order-detail-state strong {
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

.my-order-detail-page__header button:hover,
.my-order-detail-state button:hover,
.my-order-detail-section__title button:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.my-order-detail-page__header button:focus-visible,
.my-order-detail-state button:focus-visible {
  outline: var(--focus-ring-width) solid var(--overlay-focus-ring);
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
