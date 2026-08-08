<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import {
  convertProductToDirectSale,
  getProductDetail,
  scheduleProductAuction,
} from '@/domains/product/api/productApi'
import { normalizeApiError } from '@/shared/api/http'
import AppInlineNotice from '@/shared/components/AppInlineNotice.vue'

import type { LiveUnsoldProduct } from '@/domains/auction/types/liveAuction.types'

const props = defineProps<{
  product: LiveUnsoldProduct
}>()

// 처리 결과를 그대로 올려 보낸다 — 방송 종료 대시보드의 상품별 결과·미판매 배지가 바뀐
// 판매 방식과 가격을 바로 반영해야 하기 때문이다.
const emit = defineEmits<{
  handled: [
    result: { productId: number; saleType: 'DIRECT_SALE' | 'AUCTION'; price: number | null },
  ]
}>()

type Mode = 'idle' | 'direct-form' | 'auction-confirm' | 'processing' | 'done'

const mode = ref<Mode>('idle')
const doneLabel = ref('')
const errorMessage = ref('')

// 등록된 상품 정보 — GET /products/{id}로 채우고, 실패 시 라이브 상품 데이터로 대체.
const infoLoading = ref(true)
const imageUrl = ref<string | null>(props.product.thumbnailUrl)
const brand = ref<string | null>(null)
const conditionLabel = ref<string | null>(null)
const registeredPrice = ref<number | null>(props.product.startPrice)
const priceInput = ref('')
// 경매를 건 적 없는 미판매 상품도 이 화면에 온다. 이미 정찰제로 걸려 있던 상품에
// "상시 판매로 전환"은 의미가 없으므로, 판매 방식에 따라 선택지 자체를 다르게 준다.
//   경매 예정 상품 → 상시 판매로 전환 / 경매 예정 유지(변경 없음)
//   정찰제 상품    → 가격 수정하기 / 경매 예정으로 전환(PATCH auction-schedule)
// 편성 상품 목록에서 받은 판매 방식을 기준으로 둔다. 상품 상세(GET /products/{id})는 상품에
// 따라 500이 나서(요청 029) 그것만 믿으면 문구가 경매용으로 굳어버린다.
const isDirectSale = ref(props.product.saleType === 'DIRECT_SALE')

const priceChoiceLabel = computed(() => (isDirectSale.value ? '가격 수정하기' : '상시 판매로 전환'))
const priceFormLabel = computed(() => (isDirectSale.value ? '판매 가격' : '상시 판매 가격'))
const priceSubmitLabel = computed(() => (isDirectSale.value ? '가격 저장' : '상시 판매로 전환'))

const keepLabel = computed(() => (isDirectSale.value ? '경매 예정으로 전환' : '경매 예정 유지'))
const keepConfirmText = computed(() =>
  isDirectSale.value
    ? '이 상품을 경매 예정으로 되돌릴까요? 지정된 가격이 사라지고 다음 방송에서 경매로 올릴 수 있어요.'
    : '이 상품을 경매 예정 상태로 두시겠어요? 다음 방송에서 다시 경매로 올릴 수 있어요.',
)

const loadDetail = async () => {
  infoLoading.value = true
  try {
    const detail = await getProductDetail(props.product.productId)
    imageUrl.value = detail.images[0]?.url ?? imageUrl.value
    brand.value = detail.brand || brand.value
    conditionLabel.value = detail.conditionLabel || conditionLabel.value
    registeredPrice.value = detail.price

    // 편성 목록에 판매 방식이 없을 때만 상세로 보강한다.
    if (props.product.saleType == null) {
      isDirectSale.value = detail.saleType === 'DIRECT_SALE'
    }
  } catch {
    // 상품 상세는 상품에 따라 500이 난다(요청 029) — 실패해도 편성 목록에서 받은 값으로 계속 쓴다.
  } finally {
    infoLoading.value = false
  }
}

onMounted(loadDetail)

const openDirectForm = () => {
  errorMessage.value = ''
  priceInput.value = registeredPrice.value != null ? String(registeredPrice.value) : ''
  mode.value = 'direct-form'
}

const cancelDirectForm = () => {
  errorMessage.value = ''
  mode.value = 'idle'
}

const confirmDirectSale = async () => {
  const price = Number(priceInput.value)

  if (!Number.isFinite(price) || price <= 0) {
    errorMessage.value = '판매 가격을 입력해 주세요.'
    return
  }

  mode.value = 'processing'
  errorMessage.value = ''

  const wasDirectSale = isDirectSale.value

  try {
    await convertProductToDirectSale(props.product.productId, price)
    registeredPrice.value = price
    isDirectSale.value = true
    doneLabel.value = `${wasDirectSale ? '가격 수정' : '상시 판매 전환'} · ${price.toLocaleString('ko-KR')}P`
    mode.value = 'done'
    emit('handled', { productId: props.product.productId, saleType: 'DIRECT_SALE', price })
  } catch (error) {
    const apiError = normalizeApiError(error)

    // 이미 상시 판매 중인 상품의 가격 수정은 아직 BE에 엔드포인트가 없다(P003, 요청 046).
    // 지원되면 같은 호출이 그대로 통하므로 FE는 손댈 게 없다.
    errorMessage.value =
      wasDirectSale && apiError.code === 'P003'
        ? '가격 수정은 아직 준비 중입니다. 경매 예정으로 전환한 뒤 다시 가격을 지정할 수 있어요.'
        : apiError.message || '처리에 실패했습니다. 다시 시도해 주세요.'
    mode.value = 'direct-form'
  }
}

// 되돌릴 수 없는 선택이라 가격 지정과 똑같이 확인 단계를 거친다.
const openAuctionConfirm = () => {
  errorMessage.value = ''
  mode.value = 'auction-confirm'
}

const cancelAuctionConfirm = () => {
  mode.value = 'idle'
}

const keepAuctionScheduled = async () => {
  errorMessage.value = ''

  // 경매 예정 상품은 상태를 바꿀 게 없어 화면에서만 처리 완료로 표시한다.
  if (!isDirectSale.value) {
    doneLabel.value = '경매 예정 유지'
    mode.value = 'done'
    emit('handled', {
      productId: props.product.productId,
      saleType: 'AUCTION',
      price: registeredPrice.value,
    })
    return
  }

  mode.value = 'processing'

  try {
    await scheduleProductAuction(props.product.productId)
    isDirectSale.value = false
    // 경매 예정으로 돌아가면 서버에서 가격이 비워진다(Product#scheduleAuction).
    registeredPrice.value = null
    doneLabel.value = '경매 예정 전환'
    mode.value = 'done'
    emit('handled', { productId: props.product.productId, saleType: 'AUCTION', price: null })
  } catch (error) {
    errorMessage.value =
      normalizeApiError(error).message || '처리에 실패했습니다. 다시 시도해 주세요.'
    mode.value = 'auction-confirm'
  }
}
</script>

<template>
  <article class="unsold-item" :class="{ 'unsold-item--done': mode === 'done' }">
    <div class="unsold-item__info">
      <div class="unsold-item__thumb" :class="{ 'unsold-item__thumb--empty': !imageUrl }">
        <img v-if="imageUrl" :src="imageUrl" :alt="`${product.title} 이미지`" />
      </div>
      <div class="unsold-item__meta">
        <p v-if="brand" class="unsold-item__brand">{{ brand }}</p>
        <h3 class="unsold-item__title">{{ product.title }}</h3>
        <p class="unsold-item__sub">
          <span v-if="conditionLabel">{{ conditionLabel }}</span>
          <span v-if="registeredPrice !== null" class="unsold-item__reg-price">
            등록가 {{ registeredPrice.toLocaleString('ko-KR') }}P
          </span>
          <span v-else-if="infoLoading">정보 불러오는 중…</span>
        </p>
      </div>
      <span v-if="mode === 'done'" class="unsold-item__done-badge">{{ doneLabel }}</span>
    </div>

    <!-- 처리 완료 -->
    <p v-if="mode === 'done'" class="unsold-item__done-note">처리 완료됐어요.</p>

    <!-- 판매 가격 입력 -->
    <div v-else-if="mode === 'direct-form'" class="unsold-item__direct">
      <label :for="`unsold-price-${product.productId}`">{{ priceFormLabel }}</label>
      <div class="unsold-item__price-row">
        <input
          :id="`unsold-price-${product.productId}`"
          v-model="priceInput"
          type="number"
          inputmode="numeric"
          min="0"
          placeholder="가격 입력"
        />
        <span>P</span>
      </div>
      <AppInlineNotice v-if="errorMessage" variant="error">{{ errorMessage }}</AppInlineNotice>
      <div class="unsold-item__direct-actions">
        <button type="button" class="unsold-item__ghost" @click="cancelDirectForm">취소</button>
        <button type="button" class="unsold-item__primary" @click="confirmDirectSale">
          {{ priceSubmitLabel }}
        </button>
      </div>
    </div>

    <!-- 그대로 두기 확인 -->
    <div v-else-if="mode === 'auction-confirm'" class="unsold-item__confirm">
      <p class="unsold-item__confirm-text">{{ keepConfirmText }}</p>
      <div class="unsold-item__direct-actions">
        <button type="button" class="unsold-item__ghost" @click="cancelAuctionConfirm">취소</button>
        <button type="button" class="unsold-item__primary" @click="keepAuctionScheduled">
          {{ keepLabel }}
        </button>
      </div>
    </div>

    <!-- 선택 -->
    <div v-else class="unsold-item__actions">
      <button
        type="button"
        class="unsold-item__choice"
        :disabled="mode === 'processing'"
        @click="openDirectForm"
      >
        {{ priceChoiceLabel }}
      </button>
      <button
        type="button"
        class="unsold-item__choice unsold-item__choice--auction"
        :disabled="mode === 'processing'"
        @click="openAuctionConfirm"
      >
        {{ keepLabel }}
      </button>
    </div>

    <AppInlineNotice v-if="errorMessage && mode !== 'direct-form'" variant="error">
      {{ errorMessage }}
    </AppInlineNotice>
  </article>
</template>

<style scoped lang="scss">
.unsold-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-4);
  border: 1px solid var(--color-live-border);
  border-radius: var(--radius-card);
  background: var(--color-live-surface);
}

.unsold-item--done {
  opacity: 0.72;
}

.unsold-item__info {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.unsold-item__thumb {
  width: 56px;
  height: var(--button-height-tall);
  flex-shrink: 0;
  overflow: hidden;
  border-radius: var(--radius-control);
  background: var(--color-live-surface-raised);
}

.unsold-item__thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.unsold-item__meta {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  gap: 2px;
}

.unsold-item__brand {
  color: var(--color-live-text-secondary);
  font-size: var(--font-size-2xs);
}

.unsold-item__title {
  overflow: hidden;
  color: var(--color-live-text-primary);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-bold);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.unsold-item__sub {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  color: var(--color-live-text-secondary);
  font-size: var(--font-size-xs);
}

.unsold-item__reg-price {
  color: var(--color-live-text-primary);
  font-weight: var(--font-weight-semibold);
}

.unsold-item__done-badge {
  flex-shrink: 0;
  padding: 4px 10px;
  border-radius: var(--radius-badge);
  background: var(--color-live);
  color: var(--color-text-inverse);
  font-size: var(--font-size-2xs);
  font-weight: var(--font-weight-bold);
}

.unsold-item__done-note {
  color: var(--color-live-text-secondary);
  font-size: var(--font-size-xs);
}

.unsold-item__actions {
  display: grid;
  gap: var(--space-2);
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.unsold-item__choice {
  min-height: var(--button-height-compact);
  border: 1px solid var(--color-live);
  border-radius: var(--radius-control);
  background: color-mix(in srgb, var(--color-live) 16%, transparent);
  color: var(--color-live-text-primary);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-bold);
}

.unsold-item__choice:hover:not(:disabled) {
  background: color-mix(in srgb, var(--color-live) 28%, transparent);
}

.unsold-item__choice--auction {
  border-color: var(--color-live-border);
  background: var(--color-live-surface-raised);
  color: var(--color-live-text-secondary);
}

.unsold-item__choice:disabled {
  opacity: 0.6;
}

.unsold-item__direct,
.unsold-item__confirm {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.unsold-item__confirm-text {
  color: var(--color-live-text-secondary);
  font-size: var(--font-size-xs);
  line-height: var(--line-height-control);
}

.unsold-item__direct label {
  color: var(--color-live-text-secondary);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-semibold);
}

.unsold-item__price-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.unsold-item__price-row input {
  width: 100%;
  min-height: var(--button-height-tight);
  padding: 0 var(--space-3);
  border: 1px solid var(--color-live-border);
  border-radius: var(--radius-control);
  background: var(--color-live-background);
  color: var(--color-live-text-primary);
  font-size: var(--font-size-button-small);
}

.unsold-item__price-row span {
  color: var(--color-live-text-secondary);
  font-size: var(--font-size-button-small);
}

.unsold-item__direct-actions {
  display: flex;
  gap: var(--space-2);
}

.unsold-item__ghost {
  min-height: var(--button-height-tight);
  padding: 0 var(--space-4);
  border: 1px solid var(--color-live-border);
  border-radius: var(--radius-control);
  background: transparent;
  color: var(--color-live-text-primary);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-semibold);
}

.unsold-item__primary {
  min-height: var(--button-height-tight);
  flex: 1;
  border: 0;
  border-radius: var(--radius-control);
  background: var(--color-live);
  color: var(--color-text-inverse);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-bold);
}

.unsold-item__primary:hover {
  opacity: 0.92;
}
</style>
