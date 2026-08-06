<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import type { OrderAddressInput } from '@/domains/order/types/order.types'

const props = defineProps<{
  productTitle: string
  productPrice: number
  productThumbnailUrl: string
  pointBalance: number | null
  isBalanceLoading: boolean
  isSubmitting: boolean
  errorMessage: string
  initialAddress?: OrderAddressInput | null
}>()

const emit = defineEmits<{
  close: []
  submit: [address: OrderAddressInput]
}>()

const recipientName = ref(props.initialAddress?.recipientName ?? '')
const recipientPhone = ref(props.initialAddress?.recipientPhone ?? '')
const zipcode = ref(props.initialAddress?.zipcode ?? '')
const address1 = ref(props.initialAddress?.address1 ?? '')
const address2 = ref(props.initialAddress?.address2 ?? '')

// 다이얼로그는 즉시 열리고 잔액/배송지 조회는 그 뒤에 끝나므로, 나중에 도착한 초기 배송지 값을
// 아직 비어 있는 필드에만 채워 넣는다(사용자가 이미 입력한 값은 덮어쓰지 않는다).
watch(
  () => props.initialAddress,
  (value) => {
    if (!value) return

    if (!recipientName.value) recipientName.value = value.recipientName
    if (!recipientPhone.value) recipientPhone.value = value.recipientPhone
    if (!zipcode.value) zipcode.value = value.zipcode
    if (!address1.value) address1.value = value.address1
    if (!address2.value) address2.value = value.address2 ?? ''
  },
)

const isBalanceInsufficient = computed(
  () => props.pointBalance !== null && props.pointBalance < props.productPrice,
)

const isAddressComplete = computed(
  () =>
    recipientName.value.trim() !== '' &&
    recipientPhone.value.trim() !== '' &&
    zipcode.value.trim() !== '' &&
    address1.value.trim() !== '',
)

const canSubmit = computed(
  () =>
    !props.isBalanceLoading &&
    !props.isSubmitting &&
    !isBalanceInsufficient.value &&
    props.pointBalance !== null &&
    isAddressComplete.value,
)

const handleSubmit = () => {
  if (!canSubmit.value) return

  emit('submit', {
    recipientName: recipientName.value.trim(),
    recipientPhone: recipientPhone.value.trim(),
    zipcode: zipcode.value.trim(),
    address1: address1.value.trim(),
    address2: address2.value.trim() || undefined,
  })
}
</script>

<template>
  <div class="purchase-dialog-overlay" role="presentation" @click.self="emit('close')">
    <section
      class="purchase-dialog"
      role="dialog"
      aria-modal="true"
      aria-labelledby="purchase-dialog-title"
    >
      <header class="purchase-dialog__header">
        <h2 id="purchase-dialog-title">구매하기</h2>
        <button type="button" aria-label="닫기" @click="emit('close')">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M6 6l12 12M18 6 6 18" />
          </svg>
        </button>
      </header>

      <article class="purchase-dialog__product">
        <img :src="productThumbnailUrl" :alt="productTitle" />
        <div>
          <p>{{ productTitle }}</p>
          <strong>{{ productPrice.toLocaleString('ko-KR') }}P</strong>
        </div>
      </article>

      <dl class="purchase-dialog__balance">
        <dt>보유 포인트</dt>
        <dd v-if="isBalanceLoading">조회 중…</dd>
        <dd v-else-if="pointBalance === null">잔액을 불러오지 못했습니다.</dd>
        <dd v-else :class="{ 'purchase-dialog__balance-value--low': isBalanceInsufficient }">
          {{ pointBalance.toLocaleString('ko-KR') }}P
        </dd>
      </dl>

      <p v-if="isBalanceInsufficient" class="purchase-dialog__notice" role="alert">
        포인트 잔액이 부족합니다.
        <RouterLink :to="{ name: 'point' }">포인트 충전하러 가기</RouterLink>
      </p>

      <div class="purchase-dialog__divider" role="separator"></div>

      <form class="purchase-dialog__form" @submit.prevent="handleSubmit">
        <h3>배송지 정보</h3>
        <fieldset class="purchase-dialog__address-box">
          <div class="purchase-dialog__field">
            <label for="purchase-recipient-name">받는 사람</label>
            <input id="purchase-recipient-name" v-model="recipientName" type="text" required />
          </div>
          <div class="purchase-dialog__field">
            <label for="purchase-recipient-phone">연락처</label>
            <input id="purchase-recipient-phone" v-model="recipientPhone" type="tel" required />
          </div>
          <div class="purchase-dialog__field">
            <label for="purchase-zipcode">우편번호</label>
            <input id="purchase-zipcode" v-model="zipcode" type="text" required />
          </div>
          <div class="purchase-dialog__field">
            <label for="purchase-address1">주소</label>
            <input id="purchase-address1" v-model="address1" type="text" required />
          </div>
          <div class="purchase-dialog__field">
            <label for="purchase-address2">상세 주소</label>
            <input id="purchase-address2" v-model="address2" type="text" />
          </div>
        </fieldset>

        <p v-if="errorMessage" class="purchase-dialog__error" role="alert">{{ errorMessage }}</p>

        <div class="purchase-dialog__actions">
          <button type="button" @click="emit('close')">취소</button>
          <button type="submit" :disabled="!canSubmit">
            {{ isSubmitting ? '처리 중…' : `${productPrice.toLocaleString('ko-KR')}P 결제하기` }}
          </button>
        </div>
      </form>
    </section>
  </div>
</template>

<style scoped lang="scss">
.purchase-dialog-overlay {
  display: grid;
  position: fixed;
  /* --z-layer-3(=3)는 컴포넌트 내부 로컬 스태킹용이라 헤더(--z-layer-header=10)보다 낮다.
     전역 모달은 그 위로 올라와야 하므로 별도로 높은 값을 쓴다. */
  z-index: 500;
  padding: var(--space-4);
  background: rgba(4, 6, 5, 0.72);
  inset: 0;
  place-items: center;
  backdrop-filter: blur(3px);
}

.purchase-dialog {
  display: grid;
  width: min(440px, 100%);
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

.purchase-dialog__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--color-border);
}

.purchase-dialog__header h2 {
  color: var(--color-text-primary);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-extrabold);
}

.purchase-dialog__header button {
  display: grid;
  width: var(--button-height-compact);
  height: var(--button-height-compact);
  border: none;
  background: none;
  color: var(--color-text-secondary);
  cursor: pointer;
  place-items: center;
}

.purchase-dialog__header button svg {
  width: var(--icon-size-sm);
  height: var(--icon-size-sm);
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-width: 1.8;
}

.purchase-dialog__product {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr);
  gap: var(--space-3);
  align-items: center;
}

.purchase-dialog__product img {
  width: 72px;
  height: 72px;
  border-radius: var(--radius-control);
  object-fit: cover;
}

.purchase-dialog__product p {
  color: var(--color-text-secondary);
  font-size: var(--font-size-caption);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.purchase-dialog__product strong {
  display: block;
  margin-top: var(--space-1);
  color: var(--color-text-primary);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-extrabold);
}

.purchase-dialog__balance {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface-secondary);
}

.purchase-dialog__balance dt {
  color: var(--color-text-secondary);
  font-size: var(--font-size-caption);
}

.purchase-dialog__balance dd {
  color: var(--color-text-primary);
  font-weight: var(--font-weight-bold);
}

.purchase-dialog__balance-value--low {
  color: var(--color-danger, #d64545);
}

.purchase-dialog__notice {
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--color-danger, #d64545);
  border-radius: var(--radius-control);
  background: var(--color-danger-soft, rgba(214, 69, 69, 0.08));
  color: var(--color-danger, #d64545);
  font-size: var(--font-size-caption);
}

.purchase-dialog__notice a {
  color: inherit;
  font-weight: var(--font-weight-bold);
  text-decoration: underline;
}

.purchase-dialog__divider {
  height: 1px;
  margin: 0 calc(var(--space-6) * -1);
  background: var(--color-border);
}

.purchase-dialog__form {
  display: grid;
  gap: var(--space-3);
}

.purchase-dialog__form h3 {
  color: var(--color-text-primary);
  font-size: var(--font-size-body);
  font-weight: var(--font-weight-bold);
}

.purchase-dialog__address-box {
  display: grid;
  gap: var(--space-3);
  margin: 0;
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface-secondary);
}

.purchase-dialog__field {
  display: grid;
  gap: var(--space-1);
}

.purchase-dialog__field label {
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
}

.purchase-dialog__field input {
  height: var(--button-height-sm);
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-size: var(--font-size-body);
}

.purchase-dialog__field input:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 1px;
}

.purchase-dialog__error {
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--color-danger, #d64545);
  border-radius: var(--radius-control);
  background: var(--color-danger-soft, rgba(214, 69, 69, 0.08));
  color: var(--color-danger, #d64545);
  font-size: var(--font-size-caption);
}

.purchase-dialog__actions {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: var(--space-2);
}

.purchase-dialog__actions button {
  height: var(--button-height-major);
  border-radius: var(--radius-control);
  font-size: var(--font-size-body);
  font-weight: var(--font-weight-semibold);
}

.purchase-dialog__actions button[type='button'] {
  border: 1px solid var(--color-border-strong);
  background: var(--color-surface);
  color: var(--color-text-primary);
}

.purchase-dialog__actions button[type='submit'] {
  border: 1px solid var(--color-primary);
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

.purchase-dialog__actions button[type='submit']:disabled {
  cursor: not-allowed;
  border-color: var(--color-border);
  background: var(--color-surface-secondary);
  color: var(--color-text-muted);
}
</style>
