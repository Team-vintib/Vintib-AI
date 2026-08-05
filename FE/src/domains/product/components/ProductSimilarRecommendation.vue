<script setup lang="ts">
import { ref, watch } from 'vue'

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

const products = ref<ProductListItem[]>([])
const loadState = ref<'loading' | 'loaded' | 'error'>('loading')
const track = ref<HTMLElement | null>(null)

const load = async (productId: number) => {
  loadState.value = 'loading'

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

const scrollTrack = (direction: 1 | -1) => {
  track.value?.scrollBy({ left: direction * 320, behavior: 'smooth' })
}

const isLiked = (product: ProductListItem) =>
  wishStore.isProductWished(product.id, product.isLiked)

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
  (id) => {
    void load(id)
  },
  { immediate: true },
)
</script>

<template>
  <section class="similar-recommend" aria-labelledby="similar-recommend-title">
    <div class="similar-recommend__head">
      <h2 id="similar-recommend-title">유사 상품 추천</h2>
      <div class="similar-recommend__nav">
        <button type="button" aria-label="이전 상품 보기" @click="scrollTrack(-1)">‹</button>
        <button type="button" aria-label="다음 상품 보기" @click="scrollTrack(1)">›</button>
      </div>
    </div>

    <p v-if="loadState === 'loading'" class="similar-recommend__state">유사 상품을 불러오는 중…</p>
    <p v-else-if="loadState === 'error'" class="similar-recommend__state">
      유사 상품을 불러오지 못했습니다.
    </p>
    <p v-else-if="!products.length" class="similar-recommend__state">추천할 유사 상품이 없습니다.</p>

    <ul v-else ref="track" class="similar-recommend__track">
      <li v-for="product in products" :key="product.id" class="similar-recommend__item">
        <ProductCard
          :product="product"
          :is-liked="isLiked(product)"
          @toggle-like="handleToggleLike"
        />
      </li>
    </ul>
  </section>
</template>

<style scoped lang="scss">
.similar-recommend {
  margin-top: var(--space-8);
}

.similar-recommend__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  margin-bottom: var(--space-4);
}

.similar-recommend__head h2 {
  color: var(--color-text-primary);
  font-size: var(--font-size-lg-plus);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-lg-plus);
}

.similar-recommend__nav {
  display: flex;
  gap: var(--space-2);
}

.similar-recommend__nav button {
  display: grid;
  width: var(--button-height-small);
  height: var(--button-height-small);
  border: 1px solid var(--color-border-strong);
  border-radius: 50%;
  background: var(--color-surface);
  color: var(--color-text-secondary);
  font-size: var(--font-size-lg-plus);
  line-height: 1;
  place-items: center;
  transition:
    border-color var(--transition-base),
    color var(--transition-base);
}

.similar-recommend__nav button:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.similar-recommend__state {
  padding: var(--space-8) 0;
  color: var(--color-text-muted);
  font-size: var(--font-size-button-small);
  text-align: center;
}

.similar-recommend__track {
  display: flex;
  gap: var(--space-4);
  padding-bottom: var(--space-2);
  list-style: none;
  overflow-x: auto;
  scroll-snap-type: x mandatory;
}

.similar-recommend__item {
  flex: 0 0 auto;
  width: 200px;
  scroll-snap-align: start;
}
</style>
