<script setup lang="ts">
import { computed, ref } from 'vue'

import ProductCard from '@/domains/product/components/ProductCard.vue'
import ProductFilterPanel from '@/domains/product/components/ProductFilterPanel.vue'
import {
  PRODUCT_LIST_MOCK_DATA,
  PRODUCT_SALE_TYPE_TABS,
  PRODUCT_SORT_OPTIONS,
} from '@/domains/product/constants/productListMockData'
import type {
  ProductSaleTypeTab,
  ProductSortOption,
} from '@/domains/product/types/productList.types'
import DefaultLayout from '@/shared/layouts/DefaultLayout.vue'

const selectedCategoryIds = ref<string[]>([])
const selectedConditionIds = ref<string[]>([])
const selectedSaleType = ref<ProductSaleTypeTab['id']>('ALL')
const selectedSortOption = ref<ProductSortOption>('LATEST')
const selectedPage = ref(1)
const searchKeyword = ref('')
const likedProductIds = ref(
  new Set(PRODUCT_LIST_MOCK_DATA.filter((product) => product.isLiked).map((product) => product.id)),
)
const filterStatusMessage = ref('')

const selectedFilterCount = computed(
  () => selectedCategoryIds.value.length + selectedConditionIds.value.length,
)

const handleFilterReset = () => {
  selectedCategoryIds.value = []
  selectedConditionIds.value = []
  filterStatusMessage.value = '선택한 필터를 초기화했습니다.'
}

const handleFilterApply = () => {
  filterStatusMessage.value =
    selectedFilterCount.value > 0
      ? `선택한 필터 ${selectedFilterCount.value}개를 확인했습니다.`
      : '전체 상품 조건을 선택했습니다.'
}

const handleSearch = () => {
  filterStatusMessage.value = searchKeyword.value.trim()
    ? `'${searchKeyword.value.trim()}' 검색 UI를 확인했습니다.`
    : '검색어를 입력해 주세요.'
}

const handleToggleLike = (productId: number) => {
  const nextLikedProductIds = new Set(likedProductIds.value)

  if (nextLikedProductIds.has(productId)) {
    nextLikedProductIds.delete(productId)
  } else {
    nextLikedProductIds.add(productId)
  }

  likedProductIds.value = nextLikedProductIds
}
</script>

<template>
  <DefaultLayout>
    <section class="product-list-page" aria-labelledby="product-list-title">
      <form class="product-list-page__search" role="search" @submit.prevent="handleSearch">
        <label class="sr-only" for="product-list-search">상품 검색</label>
        <svg class="product-list-page__search-icon" aria-hidden="true" viewBox="0 0 24 24">
          <circle cx="11" cy="11" r="7" />
          <path d="m20 20-3.8-3.8" />
        </svg>
        <input
          id="product-list-search"
          v-model="searchKeyword"
          type="search"
          placeholder="브랜드, 상품명, 판매자 또는 라이브를 검색해 보세요"
        />
        <button type="submit">검색</button>
      </form>

      <h1 id="product-list-title" class="product-list-page__title">상품</h1>

      <div class="product-list-page__content">
        <ProductFilterPanel
          v-model:selected-category-ids="selectedCategoryIds"
          v-model:selected-condition-ids="selectedConditionIds"
          @reset="handleFilterReset"
          @apply="handleFilterApply"
        />

        <div class="product-list-page__results">
          <div class="product-list-page__result-header">
            <div class="product-list-page__tabs" role="tablist" aria-label="판매 방식">
              <button
                v-for="tab in PRODUCT_SALE_TYPE_TABS"
                :key="tab.id"
                class="product-list-page__tab"
                :class="{ 'product-list-page__tab--active': selectedSaleType === tab.id }"
                type="button"
                role="tab"
                :aria-selected="selectedSaleType === tab.id"
                @click="selectedSaleType = tab.id"
              >
                {{ tab.label }}
              </button>
            </div>

            <div class="product-list-page__toolbar">
              <p>총 247개</p>
              <label class="sr-only" for="product-sort">상품 정렬</label>
              <select id="product-sort" v-model="selectedSortOption">
                <option
                  v-for="sortOption in PRODUCT_SORT_OPTIONS"
                  :key="sortOption.id"
                  :value="sortOption.id"
                >
                  {{ sortOption.label }}
                </option>
              </select>
            </div>
          </div>

          <p class="sr-only" aria-live="polite">{{ filterStatusMessage }}</p>

          <div class="product-list-page__grid" aria-label="상품 목록">
            <ProductCard
              v-for="product in PRODUCT_LIST_MOCK_DATA"
              :key="product.id"
              :product="product"
              :is-liked="likedProductIds.has(product.id)"
              @toggle-like="handleToggleLike"
            />
          </div>

          <nav class="product-list-page__pagination" aria-label="상품 목록 페이지">
            <button type="button" aria-label="이전 페이지" disabled>
              <svg aria-hidden="true" viewBox="0 0 24 24">
                <path d="m15 18-6-6 6-6" />
              </svg>
            </button>
            <button
              v-for="page in 5"
              :key="page"
              type="button"
              :class="{ 'product-list-page__page--active': selectedPage === page }"
              :aria-current="selectedPage === page ? 'page' : undefined"
              @click="selectedPage = page"
            >
              {{ page }}
            </button>
            <button type="button" aria-label="다음 페이지">
              <svg aria-hidden="true" viewBox="0 0 24 24">
                <path d="m9 18 6-6-6-6" />
              </svg>
            </button>
          </nav>
        </div>
      </div>
    </section>
  </DefaultLayout>
</template>

<style scoped lang="scss">
.sr-only {
  position: absolute;
  overflow: hidden;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.product-list-page {
  width: 100%;
}

.product-list-page__search {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  min-height: 52px;
  padding: 0 var(--space-2) 0 var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
}

.product-list-page__search:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
}

.product-list-page__search-icon {
  width: 20px;
  height: 20px;
  color: var(--color-text-muted);
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-width: 1.8;
}

.product-list-page__search input {
  min-width: 0;
  height: 50px;
  padding: 0 var(--space-3);
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--color-text-primary);
}

.product-list-page__search input::placeholder {
  color: var(--color-text-muted);
}

.product-list-page__search button {
  min-width: 72px;
  height: var(--button-height-small);
  border: 0;
  border-radius: var(--radius-control);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-weight: 600;
}

.product-list-page__search button:hover {
  background: var(--color-primary-hover);
}

.product-list-page__search button:focus-visible {
  outline: 3px solid var(--color-primary-soft);
  outline-offset: 2px;
}

.product-list-page__title {
  margin-top: var(--space-12);
  font-size: 36px;
  font-weight: 700;
  line-height: 48px;
}

.product-list-page__content {
  display: grid;
  grid-template-columns: 224px minmax(0, 1fr);
  align-items: start;
  gap: var(--space-8);
  margin-top: var(--space-8);
}

.product-list-page__results {
  min-width: 0;
}

.product-list-page__result-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--space-6);
  min-height: 48px;
  margin-bottom: var(--space-5);
  border-bottom: 1px solid var(--color-border);
}

.product-list-page__tabs {
  display: flex;
  align-self: stretch;
}

.product-list-page__tab {
  min-width: 96px;
  padding: 0 var(--space-4);
  border: 0;
  border-bottom: 2px solid transparent;
  background: transparent;
  color: var(--color-text-secondary);
  font-weight: 600;
}

.product-list-page__tab:hover,
.product-list-page__tab--active {
  border-bottom-color: var(--color-primary);
  color: var(--color-primary);
}

.product-list-page__tab:focus-visible {
  outline: 3px solid var(--color-primary-soft);
  outline-offset: -3px;
}

.product-list-page__toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding-bottom: var(--space-2);
  color: var(--color-text-secondary);
  font-size: 13px;
}

.product-list-page__toolbar select {
  min-width: 136px;
  height: var(--button-height-small);
  padding: 0 var(--space-8) 0 var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  outline: 0;
  background: var(--color-surface);
  color: var(--color-text-primary);
}

.product-list-page__toolbar select:focus-visible {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
}

.product-list-page__grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-6);
}

.product-list-page__pagination {
  display: flex;
  justify-content: center;
  gap: var(--space-2);
  margin-top: var(--space-12);
}

.product-list-page__pagination button {
  display: grid;
  place-items: center;
  min-width: 40px;
  height: 40px;
  border: 1px solid transparent;
  border-radius: var(--radius-control);
  background: transparent;
  color: var(--color-text-secondary);
}

.product-list-page__pagination button:hover:not(:disabled),
.product-list-page__pagination button:focus-visible,
.product-list-page__page--active {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.product-list-page__pagination button:focus-visible {
  outline: 3px solid var(--color-primary-soft);
  outline-offset: 2px;
}

.product-list-page__pagination button:disabled {
  color: var(--color-text-muted);
  opacity: 0.45;
}

.product-list-page__pagination svg {
  width: 18px;
  height: 18px;
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.8;
}

@media (max-width: 1180px) {
  .product-list-page__grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 1024px) {
  .product-list-page__content {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .product-list-page__title {
    margin-top: var(--space-8);
    font-size: 30px;
    line-height: 40px;
  }

  .product-list-page__result-header {
    align-items: stretch;
    flex-direction: column;
    border-bottom: 0;
  }

  .product-list-page__tabs {
    min-height: 48px;
    border-bottom: 1px solid var(--color-border);
  }

  .product-list-page__tab {
    flex: 1;
    min-width: 0;
    padding: 0 var(--space-2);
  }

  .product-list-page__toolbar {
    justify-content: space-between;
  }

  .product-list-page__grid {
    grid-template-columns: 1fr;
  }
}
</style>
