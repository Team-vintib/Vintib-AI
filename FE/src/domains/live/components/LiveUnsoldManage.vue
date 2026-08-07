<script setup lang="ts">
import { computed, ref } from 'vue'

import LiveUnsoldProductItem from '@/domains/live/components/LiveUnsoldProductItem.vue'

import type { LiveUnsoldProduct } from '@/domains/auction/types/liveAuction.types'

const props = defineProps<{
  products: LiveUnsoldProduct[]
}>()

type HandledResult = {
  productId: number
  saleType: 'DIRECT_SALE' | 'AUCTION'
  price: number | null
}

const emit = defineEmits<{
  back: []
  'to-list': []
  handled: [result: HandledResult]
}>()

const handledIds = ref<Set<number>>(new Set())

// 처리 결과는 방송 화면까지 올려 보낸다 — 대시보드의 상품별 결과가 같이 갱신돼야 한다.
const onHandled = (result: HandledResult) => {
  handledIds.value = new Set(handledIds.value).add(result.productId)
  emit('handled', result)
}

const handledCount = computed(
  () => props.products.filter((product) => handledIds.value.has(product.productId)).length,
)

const allHandled = computed(
  () => props.products.length > 0 && handledCount.value === props.products.length,
)
</script>

<template>
  <section class="unsold-manage" aria-labelledby="unsold-manage-title">
    <header class="unsold-manage__head">
      <button type="button" class="unsold-manage__back" @click="emit('back')">← 대시보드</button>
      <h1 id="unsold-manage-title" class="unsold-manage__title">남은 상품 관리</h1>
      <p class="unsold-manage__desc">
        방송에서 팔리지 않은 상품을 상시 판매로 전환하거나 지금 상태로 두세요.
      </p>
      <p class="unsold-manage__progress">{{ handledCount }} / {{ products.length }} 처리됨</p>
    </header>

    <ul class="unsold-manage__list">
      <li v-for="product in products" :key="product.productId">
        <LiveUnsoldProductItem :product="product" @handled="onHandled" />
      </li>
    </ul>

    <div class="unsold-manage__actions">
      <button type="button" class="unsold-manage__ghost" @click="emit('back')">뒤로</button>
      <button
        type="button"
        class="unsold-manage__done"
        :disabled="!allHandled"
        @click="emit('to-list')"
      >
        {{ allHandled ? '완료 · 홈으로 가기' : '남은 상품을 모두 처리해 주세요' }}
      </button>
    </div>
  </section>
</template>

<style scoped lang="scss">
.unsold-manage {
  display: flex;
  width: 100%;
  max-width: 720px;
  flex-direction: column;
  gap: var(--space-4);
  margin: 0 auto;
  padding: var(--space-6) var(--space-4) var(--space-8);
}

.unsold-manage__head {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.unsold-manage__back {
  align-self: flex-start;
  padding: 4px 0;
  border: 0;
  background: transparent;
  color: var(--color-live-text-secondary);
  font-size: var(--font-size-caption);
  cursor: pointer;
}

.unsold-manage__back:hover {
  color: var(--color-live-text-primary);
}

.unsold-manage__title {
  color: var(--color-live-text-primary);
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-extrabold);
}

.unsold-manage__desc {
  color: var(--color-live-text-secondary);
  font-size: var(--font-size-caption);
  line-height: 19px;
}

.unsold-manage__progress {
  align-self: flex-start;
  margin-top: 2px;
  padding: 4px 10px;
  border-radius: var(--radius-chip);
  background: var(--color-live-surface-raised);
  color: var(--color-live-text-primary);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-bold);
}

.unsold-manage__list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.unsold-manage__actions {
  display: flex;
  gap: var(--space-2);
  margin-top: var(--space-2);
}

.unsold-manage__ghost {
  min-height: var(--button-height-loose);
  padding: 0 var(--space-5);
  border: 1px solid var(--color-live-border);
  border-radius: var(--radius-control);
  background: var(--color-live-surface);
  color: var(--color-live-text-primary);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-bold);
}

.unsold-manage__done {
  min-height: var(--button-height-loose);
  flex: 1;
  border: 0;
  border-radius: var(--radius-control);
  background: var(--color-live);
  color: var(--color-text-inverse);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-bold);
}

.unsold-manage__done:disabled {
  background: var(--color-live-surface-raised);
  color: var(--color-live-text-secondary);
  cursor: not-allowed;
}

.unsold-manage__done:not(:disabled):hover {
  opacity: 0.92;
}
</style>
