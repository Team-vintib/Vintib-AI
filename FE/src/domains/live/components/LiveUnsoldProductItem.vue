<script setup lang="ts">
import { onMounted, ref } from 'vue'

import {
  convertProductToDirectSale,
  getProductDetail,
  scheduleProductAuction,
} from '@/domains/product/api/productApi'
import { normalizeApiError } from '@/shared/api/http'

import type { LiveWatchProduct } from '@/domains/live/types/liveWatch.types'

const props = defineProps<{
  product: LiveWatchProduct
}>()

const emit = defineEmits<{
  handled: [productId: number]
}>()

type Mode = 'idle' | 'direct-form' | 'processing' | 'done'

const mode = ref<Mode>('idle')
const doneLabel = ref('')
const errorMessage = ref('')

// 등록된 상품 정보 — GET /products/{id}로 채우고, 실패 시 라이브 상품 데이터로 대체.
const infoLoading = ref(true)
const imageUrl = ref<string | null>(props.product.thumbnailUrl)
const brand = ref<string | null>(props.product.brandName)
const conditionLabel = ref<string | null>(props.product.condition)
const registeredPrice = ref<number | null>(props.product.price)
const priceInput = ref('')

const loadDetail = async () => {
  infoLoading.value = true
  try {
    const detail = await getProductDetail(props.product.id)
    imageUrl.value = detail.images[0]?.url ?? imageUrl.value
    brand.value = detail.brand || brand.value
    conditionLabel.value = detail.conditionLabel || conditionLabel.value
    registeredPrice.value = detail.price
  } catch {
    // 미리보기/비로그인 등 상세 조회 실패 시 라이브 상품 데이터 유지(BE 확인 필요).
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

  try {
    await convertProductToDirectSale(props.product.id, price)
    doneLabel.value = `상시 판매 전환 · ${price.toLocaleString('ko-KR')}P`
    mode.value = 'done'
    emit('handled', props.product.id)
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message || '처리에 실패했습니다. 다시 시도해 주세요.'
    mode.value = 'direct-form'
  }
}

const chooseAuction = async () => {
  mode.value = 'processing'
  errorMessage.value = ''

  try {
    await scheduleProductAuction(props.product.id)
    doneLabel.value = '경매 예정'
    mode.value = 'done'
    emit('handled', props.product.id)
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message || '처리에 실패했습니다. 다시 시도해 주세요.'
    mode.value = 'idle'
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

    <!-- 상시 판매 가격 입력 -->
    <div v-else-if="mode === 'direct-form'" class="unsold-item__direct">
      <label :for="`unsold-price-${product.id}`">상시 판매 가격</label>
      <div class="unsold-item__price-row">
        <input
          :id="`unsold-price-${product.id}`"
          v-model="priceInput"
          type="number"
          inputmode="numeric"
          min="0"
          placeholder="가격 입력"
        />
        <span>P</span>
      </div>
      <p v-if="errorMessage" class="unsold-item__error">{{ errorMessage }}</p>
      <div class="unsold-item__direct-actions">
        <button type="button" class="unsold-item__ghost" @click="cancelDirectForm">취소</button>
        <button type="button" class="unsold-item__primary" @click="confirmDirectSale">
          상시 판매로 전환
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
        상시 판매로 전환
      </button>
      <button
        type="button"
        class="unsold-item__choice unsold-item__choice--auction"
        :disabled="mode === 'processing'"
        @click="chooseAuction"
      >
        경매 예정
      </button>
    </div>

    <p v-if="errorMessage && mode !== 'direct-form'" class="unsold-item__error">{{ errorMessage }}</p>
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

.unsold-item__direct {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
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

.unsold-item__error {
  color: var(--color-error);
  font-size: var(--font-size-xs);
}
</style>
