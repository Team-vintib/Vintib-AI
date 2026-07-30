<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/domains/auth/stores/authStore'
import {
  addWish,
  getProductList,
  removeWish,
} from '@/domains/product/api/productApi'
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
import AppSearchBar from '@/shared/components/AppSearchBar.vue'
import { ROUTE_NAMES } from '@/shared/constants/routes'
import DefaultLayout from '@/shared/layouts/DefaultLayout.vue'

const router = useRouter()
const authStore = useAuthStore()
const selectedCategoryIds = ref<string[]>([])
const selectedConditionIds = ref<string[]>([])
const selectedSaleType = ref<ProductSaleTypeTab['id']>('ALL')
const selectedSortOption = ref<ProductSortOption>('LATEST')
const selectedPage = ref(1)
const searchKeyword = ref('')
const minimumPrice = ref('')
const maximumPrice = ref('')
const appliedMinimumPrice = ref<number | null>(null)
const appliedMaximumPrice = ref<number | null>(null)
const priceError = ref('')
const products = ref(PRODUCT_LIST_MOCK_DATA)
const totalProductCount = ref(PRODUCT_LIST_MOCK_DATA.length)
const totalPageCount = ref(1)
const isLoadingProducts = ref(false)
const productLoadError = ref('')
const likedProductIds = ref(new Set(PRODUCT_LIST_MOCK_DATA.filter((product) => product.isLiked).map((product) => product.id)))
const filterStatusMessage = ref('')

const selectedFilterCount = computed(
  () =>
    selectedCategoryIds.value.length +
    selectedConditionIds.value.length +
    Number(Boolean(minimumPrice.value)) +
    Number(Boolean(maximumPrice.value)),
)

const filteredProducts = computed(() => products.value)
const visiblePageNumbers = computed(() =>
  Array.from({ length: totalPageCount.value }, (_, index) => index + 1),
)

const parseOptionalPrice = (value: string) => {
  if (!value) {
    return null
  }

  const parsedPrice = Number(value)
  return Number.isFinite(parsedPrice) ? parsedPrice : null
}

const handleFilterReset = () => {
  selectedCategoryIds.value = []
  selectedConditionIds.value = []
  minimumPrice.value = ''
  maximumPrice.value = ''
  appliedMinimumPrice.value = null
  appliedMaximumPrice.value = null
  priceError.value = ''
  selectedPage.value = 1
  filterStatusMessage.value = '선택한 필터를 초기화했습니다.'
  void loadProducts()
}

const handleFilterApply = () => {
  const nextMinimumPrice = parseOptionalPrice(minimumPrice.value)
  const nextMaximumPrice = parseOptionalPrice(maximumPrice.value)

  if (
    (nextMinimumPrice !== null && nextMinimumPrice < 0) ||
    (nextMaximumPrice !== null && nextMaximumPrice < 0)
  ) {
    priceError.value = '가격은 0 이상으로 입력해 주세요.'
    return
  }

  if (
    nextMinimumPrice !== null &&
    nextMaximumPrice !== null &&
    nextMinimumPrice > nextMaximumPrice
  ) {
    priceError.value = '최소 가격은 최대 가격보다 클 수 없습니다.'
    return
  }

  priceError.value = ''
  appliedMinimumPrice.value = nextMinimumPrice
  appliedMaximumPrice.value = nextMaximumPrice
  selectedPage.value = 1
  void loadProducts()
}

const handleSearch = async (keyword: string) => {
  await router.push({
    name: ROUTE_NAMES.SEARCH,
    query: keyword ? { keyword, type: 'product' } : { type: 'product' },
  })
}

const loadProducts = async () => {
  isLoadingProducts.value = true
  productLoadError.value = ''

  try {
    const response = await getProductList({
      categoryIds: selectedCategoryIds.value,
      conditionGrades: selectedConditionIds.value,
      maxPrice: appliedMaximumPrice.value,
      minPrice: appliedMinimumPrice.value,
      page: selectedPage.value,
      saleType: selectedSaleType.value,
      sort: selectedSortOption.value,
    })

    products.value = response.items
    totalProductCount.value = response.meta.totalElements
    totalPageCount.value = Math.max(response.meta.totalPages, 1)
    likedProductIds.value = new Set(response.items.filter((product) => product.isLiked).map((product) => product.id))
    filterStatusMessage.value =
      selectedFilterCount.value > 0
        ? `선택한 필터를 적용해 상품 ${response.meta.totalElements}개를 찾았습니다.`
        : '전체 상품 조건을 선택했습니다.'
  } catch {
    products.value = PRODUCT_LIST_MOCK_DATA
    totalProductCount.value = PRODUCT_LIST_MOCK_DATA.length
    totalPageCount.value = 1
    likedProductIds.value = new Set(PRODUCT_LIST_MOCK_DATA.filter((product) => product.isLiked).map((product) => product.id))
    productLoadError.value = '상품 목록을 불러오지 못해 임시 데이터를 표시합니다.'
  } finally {
    isLoadingProducts.value = false
  }
}

const handleToggleLike = async (productId: number) => {
  if (!authStore.isAuthenticated || !authStore.user?.id) {
    await router.push({ name: ROUTE_NAMES.AUTH_LOGIN })
    return
  }

  const wasLiked = likedProductIds.value.has(productId)
  const nextLikedProductIds = new Set(likedProductIds.value)

  if (wasLiked) {
    nextLikedProductIds.delete(productId)
  } else {
    nextLikedProductIds.add(productId)
  }

  likedProductIds.value = nextLikedProductIds

  try {
    if (wasLiked) {
      await removeWish(authStore.user.id, productId)
    } else {
      await addWish(authStore.user.id, productId)
    }
  } catch {
    likedProductIds.value = new Set(
      wasLiked
        ? [...nextLikedProductIds, productId]
        : [...nextLikedProductIds].filter((likedProductId) => likedProductId !== productId),
    )
  }
}

const moveToPage = (page: number) => {
  if (page < 1 || page > totalPageCount.value || page === selectedPage.value) {
    return
  }

  selectedPage.value = page
  void loadProducts()
}

onMounted(() => {
  void loadProducts()
})
</script>

<template>
  <DefaultLayout>
    <section class="product-list-page" aria-labelledby="product-list-title">
      <header class="product-list-page__header">
        <h1 id="product-list-title">상품</h1>
        <p>지금 구매 가능한 상품과 라이브 경매 예정 상품을 둘러보세요.</p>
      </header>

      <AppSearchBar
        v-model="searchKeyword"
        search-label="상품 검색"
        placeholder="브랜드, 상품명, 판매자 또는 라이브를 검색해 보세요"
        @submit="handleSearch"
      />

      <div class="product-list-page__content">
        <ProductFilterPanel
          v-model:selected-category-ids="selectedCategoryIds"
          v-model:selected-condition-ids="selectedConditionIds"
          v-model:minimum-price="minimumPrice"
          v-model:maximum-price="maximumPrice"
          :price-error="priceError"
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
                @click="selectedSaleType = tab.id; selectedPage = 1; loadProducts()"
              >
                {{ tab.label }}
              </button>
            </div>

            <div class="product-list-page__toolbar">
              <p>총 {{ totalProductCount }}개</p>
              <label class="sr-only" for="product-sort">상품 정렬</label>
              <select id="product-sort" v-model="selectedSortOption" @change="loadProducts">
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

          <p v-if="productLoadError" class="product-list-page__notice" role="status">
            {{ productLoadError }}
          </p>

          <div
            v-if="!isLoadingProducts && filteredProducts.length"
            class="product-list-page__grid"
            aria-label="상품 목록"
          >
            <ProductCard
              v-for="product in filteredProducts"
              :key="product.id"
              :product="product"
              :is-liked="likedProductIds.has(product.id)"
              @toggle-like="handleToggleLike"
            />
          </div>

          <div v-else-if="isLoadingProducts" class="product-list-page__empty" role="status">
            <strong>상품 목록을 불러오는 중입니다.</strong>
          </div>

          <div v-else class="product-list-page__empty" role="status">
            <svg aria-hidden="true" viewBox="0 0 24 24">
              <circle cx="11" cy="11" r="7" />
              <path d="m20 20-3.8-3.8" />
            </svg>
            <strong>조건에 맞는 상품이 없습니다.</strong>
            <p>가격 범위를 다시 설정하거나 필터를 초기화해 주세요.</p>
            <button type="button" @click="handleFilterReset">필터 초기화</button>
          </div>

          <nav
            v-if="filteredProducts.length"
            class="product-list-page__pagination"
            aria-label="상품 목록 페이지"
          >
            <button type="button" aria-label="이전 페이지" disabled>
              <svg aria-hidden="true" viewBox="0 0 24 24">
                <path d="m15 18-6-6 6-6" />
              </svg>
            </button>
            <button
              v-for="page in visiblePageNumbers"
              :key="page"
              type="button"
              :class="{ 'product-list-page__page--active': selectedPage === page }"
              :aria-current="selectedPage === page ? 'page' : undefined"
              @click="moveToPage(page)"
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
  display: grid;
  gap: var(--space-8);
  width: 100%;
}

.product-list-page__header {
  display: grid;
  gap: var(--space-2);
}

.product-list-page__header h1 {
  color: var(--color-text-primary);
  font-size: 36px;
  font-weight: 700;
  line-height: 48px;
}

.product-list-page__header p {
  color: var(--color-text-secondary);
  font-size: 16px;
  line-height: 26px;
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

.product-list-page__notice {
  margin-bottom: var(--space-4);
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface-secondary);
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: 600;
  line-height: 18px;
}

.product-list-page__grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-6);
}

.product-list-page__empty {
  display: grid;
  justify-items: center;
  min-height: 360px;
  place-content: center;
  padding: var(--space-8);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface-secondary);
  color: var(--color-text-secondary);
  text-align: center;
}

.product-list-page__empty svg {
  width: 36px;
  height: 36px;
  margin-bottom: var(--space-4);
  color: var(--color-text-muted);
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-width: 1.6;
}

.product-list-page__empty strong {
  color: var(--color-text-primary);
  font-size: 18px;
}

.product-list-page__empty p {
  margin-top: var(--space-2);
  font-size: 14px;
}

.product-list-page__empty button {
  min-height: var(--button-height-small);
  margin-top: var(--space-5);
  padding: 0 var(--space-4);
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-control);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-weight: 600;
}

.product-list-page__empty button:hover {
  border-color: var(--color-primary-hover);
  background: var(--color-primary-hover);
}

.product-list-page__empty button:focus-visible {
  outline: 3px solid var(--color-primary-soft);
  outline-offset: 2px;
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
  .product-list-page__header h1 {
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
