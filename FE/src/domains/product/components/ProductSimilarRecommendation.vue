<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { useAuthStore } from '@/domains/auth/stores/authStore'
import { addWish, getSimilarProducts, removeWish } from '@/domains/product/api/productApi'
import ProductCard from '@/domains/product/components/ProductCard.vue'
import { useWishStore } from '@/domains/product/stores/wishStore'

import type { ProductListItem } from '@/domains/product/types/productList.types'

const props = defineProps<{
  productId: number
}>()

const authStore = useAuthStore()
const wishStore = useWishStore()

const MAX_VISIBLE_PRODUCTS = 5
const products = ref<ProductListItem[]>([])
const loadState = ref<'loading' | 'loaded' | 'error'>('loading')
const currentPage = ref(0)

const pageCount = computed(() =>
  Math.max(1, Math.ceil(products.value.length / MAX_VISIBLE_PRODUCTS)),
)

const visibleProducts = computed(() => {
  const start = currentPage.value * MAX_VISIBLE_PRODUCTS
  return products.value.slice(start, start + MAX_VISIBLE_PRODUCTS)
})

const trackStyle = computed(() => ({
  '--visible-card-count': Math.max(visibleProducts.value.length, 1),
}))

const canMovePrevious = computed(() => currentPage.value > 0)
const canMoveNext = computed(() => currentPage.value < pageCount.value - 1)

const load = async (productId: number) => {
  loadState.value = 'loading'
  currentPage.value = 0

  try {
    const list = await getSimilarProducts(productId)
    products.value = list
    wishStore.hydrateProducts(list)
    loadState.value = 'loaded'
  } catch {
    products.value = []
    loadState.value = 'error'
  }
}

const movePage = (direction: 1 | -1) => {
  const nextPage = currentPage.value + direction

  if (nextPage < 0 || nextPage >= pageCount.value) return

  currentPage.value = nextPage
}

const isLiked = (product: ProductListItem) => wishStore.isProductWished(product.id, product.isLiked)

const handleToggleLike = async (productId: number) => {
  const target = products.value.find((product) => product.id === productId)
  if (!target) return

  const wasLiked = wishStore.isProductWished(productId, target.isLiked)
  wishStore.setProductWish(productId, !wasLiked)

  // 비회원은 로컬 상태만 바꾼다(실제 찜 API는 로그인 필요).
  if (!authStore.user) return

  try {
    if (wasLiked) {
      await removeWish(authStore.user.id, productId)
    } else {
      await addWish(authStore.user.id, productId)
    }
  } catch {
    wishStore.setProductWish(productId, wasLiked)
  }
}

watch(
  () => props.productId,
  () => {
    void load(props.productId)
  },
  { immediate: true },
)
</script>

<template>
  <section
    v-if="loadState !== 'loaded' || products.length > 0"
    class="similar-recommend"
    aria-labelledby="similar-recommend-title"
  >
    <div class="similar-recommend__head">
      <h2 id="similar-recommend-title">유사 상품 추천</h2>
    </div>

    <p v-if="loadState === 'loading'" class="similar-recommend__state">유사 상품을 불러오는 중…</p>
    <p v-else-if="loadState === 'error'" class="similar-recommend__state">
      유사 상품을 불러오지 못했습니다.
    </p>
    <div v-else-if="products.length" class="similar-recommend__carousel">
      <button
        class="similar-recommend__arrow"
        type="button"
        aria-label="이전 유사 상품 보기"
        :disabled="!canMovePrevious"
        @click="movePage(-1)"
      >
        ‹
      </button>

      <ul class="similar-recommend__track" :style="trackStyle">
        <li v-for="product in visibleProducts" :key="product.id" class="similar-recommend__item">
          <ProductCard
            :product="product"
            :is-liked="isLiked(product)"
            @toggle-like="handleToggleLike"
          />
        </li>
      </ul>

      <button
        class="similar-recommend__arrow"
        type="button"
        aria-label="다음 유사 상품 보기"
        :disabled="!canMoveNext"
        @click="movePage(1)"
      >
        ›
      </button>
    </div>
  </section>
</template>

<style scoped lang="scss">
.similar-recommend {
  margin-top: var(--space-8);
}

.similar-recommend__head {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: var(--space-4);
  margin-bottom: var(--space-4);
}

.similar-recommend__head h2 {
  color: var(--color-text-primary);
  font-size: var(--font-size-2xl-plus);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-2xl-plus);
}

.similar-recommend__carousel {
  display: grid;
  grid-template-columns: var(--button-height-small) minmax(0, 1fr) var(--button-height-small);
  align-items: center;
  gap: var(--space-3);
}

/* 좌우 이동이 있다는 걸 먼저 알아채야 해서, 배경·테두리·글자를 한 단계씩 올린다. */
.similar-recommend__arrow {
  display: grid;
  width: 44px;
  height: 44px;
  padding: 0;
  border: 1px solid var(--color-border-strong);
  border-radius: 50%;
  background: var(--color-surface-secondary);
  color: var(--color-text-primary);
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-medium);
  line-height: 1;
  place-items: center;
  transition:
    border-color var(--transition-base),
    background-color var(--transition-base),
    color var(--transition-base);
}

.similar-recommend__arrow:not(:disabled):hover {
  border-color: var(--color-primary);
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

.similar-recommend__arrow:disabled {
  cursor: default;
  opacity: 0.3;
}

.similar-recommend__arrow:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

.similar-recommend__state {
  padding: var(--space-8) 0;
  color: var(--color-text-muted);
  font-size: var(--font-size-button-small);
  text-align: center;
}

/* 카드 수가 5개 미만이면 남는 가로를 나눠 갖게 해 여백이 뜨지 않게 한다(5개일 때는 자동으로
   좁아져 넘치지 않는다). 카드가 지나치게 커지지 않도록 항목에 상한만 둔다. */
.similar-recommend__track {
  display: grid;
  grid-template-columns: repeat(var(--visible-card-count), minmax(0, 1fr));
  gap: var(--space-4);
  list-style: none;
}

.similar-recommend__item {
  width: 100%;
  max-width: 210px;
  min-width: 0;
  margin: 0 auto;
}

/* 상세 하단 추천은 훑어보는 자리라 목록 페이지(4:5)보다 세로를 줄인다. */
.similar-recommend__item :deep(.product-card__media) {
  aspect-ratio: 1 / 1;
}

@media (max-width: 720px) {
  .similar-recommend__carousel {
    grid-template-columns: var(--button-height-small) minmax(0, 1fr) var(--button-height-small);
    gap: var(--space-2);
  }

  .similar-recommend__track {
    grid-template-columns: repeat(var(--visible-card-count), minmax(140px, 200px));
    justify-content: start;
    padding-bottom: var(--space-2);
    overflow-x: auto;
  }
}
</style>
