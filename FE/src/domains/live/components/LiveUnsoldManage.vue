<script setup lang="ts">
import { computed, ref } from 'vue'

import LiveUnsoldProductItem from '@/domains/live/components/LiveUnsoldProductItem.vue'

import type { LiveUnsoldProduct } from '@/domains/auction/types/liveAuction.types'

const props = defineProps<{
  products: LiveUnsoldProduct[]
}>()

const emit = defineEmits<{
  back: []
  'to-list': []
}>()

const handledIds = ref<Set<number>>(new Set())

const onHandled = (productId: number) => {
  handledIds.value = new Set(handledIds.value).add(productId)
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
        유찰 상품을 상시 판매로 전환하거나 경매 예정 상태로 유지하세요.
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
        {{ allHandled ? '완료 · 라이브 목록으로' : '남은 상품을 모두 처리해 주세요' }}
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
