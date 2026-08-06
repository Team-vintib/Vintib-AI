<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/domains/auth/stores/authStore'
import { getMyWishList, removeMyWish } from '@/domains/my/api/myApi'
import type { MyWishItem } from '@/domains/my/types/my.types'
import { buildProductCategoryOptions, getCategories } from '@/domains/product/api/productApi'
import ProductCard from '@/domains/product/components/ProductCard.vue'
import ProductFilterPanel from '@/domains/product/components/ProductFilterPanel.vue'
import {
  PRODUCT_SALE_TYPE_TABS,
  PRODUCT_SORT_OPTIONS,
} from '@/domains/product/constants/productListMockData'
import { useWishStore } from '@/domains/product/stores/wishStore'
import type {
  ProductCategoryOption,
  ProductSaleTypeTab,
  ProductSortOption,
} from '@/domains/product/types/productList.types'
import { normalizeApiError } from '@/shared/api/http'
import AppSearchBar from '@/shared/components/AppSearchBar.vue'
import { ROUTE_NAMES, ROUTE_PATHS } from '@/shared/constants/routes'
import DefaultLayout from '@/shared/layouts/DefaultLayout.vue'

const router = useRouter()
const authStore = useAuthStore()
const wishStore = useWishStore()

const wishes = ref<MyWishItem[]>([])
const categoryOptions = ref<ProductCategoryOption[]>([])
const isLoadingCategories = ref(true)
const categoryLoadError = ref('')
const loadState = ref<'idle' | 'loading' | 'success' | 'error'>('idle')
const errorMessage = ref('')
const actionMessage = ref('')
const removingProductId = ref<number | null>(null)
const searchKeyword = ref('')
const selectedSaleType = ref<ProductSaleTypeTab['id']>('ALL')
const selectedSortOption = ref<ProductSortOption>('LATEST')
const selectedCategoryIds = ref<number[]>([])
const selectedConditionIds = ref<string[]>([])
const minimumPrice = ref('')
const maximumPrice = ref('')
const appliedMinimumPrice = ref<number | null>(null)
const appliedMaximumPrice = ref<number | null>(null)
const priceError = ref('')

const categoryStatusMessage = computed(() => {
  if (isLoadingCategories.value) return '카테고리를 불러오는 중입니다.'
  if (categoryLoadError.value) return categoryLoadError.value
  return '선택할 수 있는 카테고리가 없습니다.'
})

// 상품 목록 페이지와 같은 방식(소분류를 대분류로 묶은 옵션)으로 카테고리를 필터링한다 —
// 선택된 옵션의 categoryIds를 펼쳐서 상품의 실제 categoryId와 비교한다.
const expandedSelectedCategoryIds = computed(() => {
  const selectedIds = new Set(selectedCategoryIds.value)

  return [
    ...new Set(
      categoryOptions.value
        .filter((option) => selectedIds.has(option.id))
        .flatMap((option) => option.categoryIds),
    ),
  ]
})

const compareWishes = (first: MyWishItem, second: MyWishItem) => {
  if (selectedSortOption.value === 'PRICE_ASC') {
    return first.product.price - second.product.price
  }

  if (selectedSortOption.value === 'PRICE_DESC') {
    return second.product.price - first.product.price
  }

  return new Date(second.wishedAt).getTime() - new Date(first.wishedAt).getTime()
}

const filteredWishes = computed(() => {
  const normalizedKeyword = searchKeyword.value.trim().toLowerCase()

  return wishes.value
    .filter((wish) => {
      const product = wish.product
      const matchesKeyword =
        !normalizedKeyword ||
        `${product.name} ${product.brand}`.toLowerCase().includes(normalizedKeyword)
      const matchesSaleType = selectedSaleType.value === 'ALL' || product.saleType === selectedSaleType.value
      const matchesCategory =
        expandedSelectedCategoryIds.value.length === 0 ||
        (typeof product.categoryId === 'number' &&
          expandedSelectedCategoryIds.value.includes(product.categoryId))
      const matchesCondition =
        selectedConditionIds.value.length === 0 ||
        selectedConditionIds.value.includes(product.conditionGrade)
      const matchesMinPrice =
        appliedMinimumPrice.value === null ||
        (product.saleType === 'DIRECT' && product.price >= appliedMinimumPrice.value)
      const matchesMaxPrice =
        appliedMaximumPrice.value === null ||
        (product.saleType === 'DIRECT' && product.price <= appliedMaximumPrice.value)

      return (
        matchesKeyword &&
        matchesSaleType &&
        matchesCategory &&
        matchesCondition &&
        matchesMinPrice &&
        matchesMaxPrice
      )
    })
    .sort(compareWishes)
})

const selectedFilterCount = computed(
  () =>
    selectedCategoryIds.value.length +
    selectedConditionIds.value.length +
    Number(appliedMinimumPrice.value !== null) +
    Number(appliedMaximumPrice.value !== null),
)

const resultMessage = computed(() => {
  if (!wishes.value.length) {
    return '찜한 상품이 없습니다.'
  }

  if (!filteredWishes.value.length) {
    return '조건에 맞는 찜 상품이 없습니다.'
  }

  return `찜 상품 ${filteredWishes.value.length}개를 표시합니다.`
})

const selectSaleType = (saleType: ProductSaleTypeTab['id']) => {
  selectedSaleType.value = saleType
}

const parseOptionalPrice = (value: string) => {
  if (!value) {
    return null
  }

  const parsedPrice = Number(value)
  return Number.isFinite(parsedPrice) ? parsedPrice : null
}

const applyFilters = () => {
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
}

const resetFilters = () => {
  selectedCategoryIds.value = []
  selectedConditionIds.value = []
  minimumPrice.value = ''
  maximumPrice.value = ''
  appliedMinimumPrice.value = null
  appliedMaximumPrice.value = null
  priceError.value = ''
  actionMessage.value = '찜 목록 조건을 초기화했습니다.'
}

const removeWishItem = async (productId: number) => {
  if (!authStore.user?.id || removingProductId.value === productId) {
    return
  }

  removingProductId.value = productId
  actionMessage.value = ''
  wishStore.setProductWish(productId, false)

  try {
    await removeMyWish(authStore.user.id, productId)
    wishes.value = wishes.value.filter((wish) => wish.product.id !== productId)
    actionMessage.value = '찜한 상품에서 제거했습니다.'
  } catch (error) {
    wishStore.setProductWish(productId, true)
    actionMessage.value = normalizeApiError(error).message
  } finally {
    removingProductId.value = null
  }
}

const loadCategoryOptions = async () => {
  isLoadingCategories.value = true
  categoryLoadError.value = ''

  try {
    const categories = await getCategories()

    categoryOptions.value = buildProductCategoryOptions(categories)
  } catch {
    categoryOptions.value = []
    categoryLoadError.value = '카테고리를 불러오지 못했습니다.'
  } finally {
    isLoadingCategories.value = false
  }
}

const loadWishes = async () => {
  await authStore.validateStoredSession()

  if (!authStore.user?.id) {
    await router.push({
      name: ROUTE_NAMES.AUTH_LOGIN,
      query: { redirect: ROUTE_PATHS.WISHLIST },
    })
    return
  }

  loadState.value = 'loading'
  errorMessage.value = ''

  try {
    const response = await getMyWishList(authStore.user.id)

    wishes.value = response.items
    wishStore.hydrateProducts(response.items.map((wish) => ({ id: wish.product.id, isLiked: true })))
    loadState.value = 'success'
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message
    wishes.value = []
    loadState.value = 'error'
  }
}

onMounted(() => {
  void loadCategoryOptions()
  void loadWishes()
})
</script>

<template>
  <DefaultLayout>
    <section class="wishlist-page" aria-label="찜한 상품">
      <AppSearchBar
        v-model="searchKeyword"
        search-label="찜 상품 검색"
        placeholder="찜한 상품명 또는 브랜드를 검색해 보세요"
        @submit="applyFilters"
      />

      <p v-if="actionMessage" class="wishlist-page__message" role="status">
        {{ actionMessage }}
      </p>

      <div v-if="loadState === 'loading'" class="wishlist-page__state" role="status">
        찜한 상품을 불러오는 중입니다.
      </div>

      <div v-else-if="loadState === 'error'" class="wishlist-page__state" role="alert">
        <strong>{{ errorMessage }}</strong>
        <button type="button" @click="loadWishes">다시 시도</button>
      </div>

      <div v-else-if="wishes.length" class="wishlist-page__content">
        <ProductFilterPanel
          :category-options="categoryOptions"
          :category-status-message="categoryStatusMessage"
          v-model:selected-category-ids="selectedCategoryIds"
          v-model:selected-condition-ids="selectedConditionIds"
          v-model:minimum-price="minimumPrice"
          v-model:maximum-price="maximumPrice"
          :price-error="priceError"
          :can-reset="selectedFilterCount > 0"
          @reset="resetFilters"
          @apply="applyFilters"
        />

        <div class="wishlist-results">
          <div class="wishlist-results__header">
            <div class="wishlist-results__tabs" role="tablist" aria-label="판매 방식">
              <button
                v-for="tab in PRODUCT_SALE_TYPE_TABS"
                :key="tab.id"
                class="wishlist-results__tab"
                :class="{ 'wishlist-results__tab--active': selectedSaleType === tab.id }"
                type="button"
                role="tab"
                :aria-selected="selectedSaleType === tab.id"
                @click="selectSaleType(tab.id)"
              >
                {{ tab.label }}
              </button>
            </div>

            <div class="wishlist-results__toolbar">
              <p>총 {{ filteredWishes.length }}개</p>
              <label class="sr-only" for="wishlist-sort">찜 상품 정렬</label>
              <select id="wishlist-sort" v-model="selectedSortOption">
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

          <p class="sr-only" aria-live="polite">{{ resultMessage }}</p>

          <div v-if="filteredWishes.length" class="wishlist-grid">
            <ProductCard
              v-for="wish in filteredWishes"
              :key="wish.product.id"
              :product="wish.product"
              :is-liked="wishStore.isProductWished(wish.product.id, true)"
              @toggle-like="removeWishItem"
            />
          </div>
          <div v-else class="wishlist-page__empty">
            <svg aria-hidden="true" viewBox="0 0 24 24">
              <circle cx="11" cy="11" r="7" />
              <path d="m20 20-3.8-3.8" />
            </svg>
            <strong>조건에 맞는 찜 상품이 없습니다.</strong>
            <p>검색어나 필터 조건을 다시 확인해 주세요.</p>
            <button type="button" @click="resetFilters">필터 초기화</button>
          </div>
        </div>
      </div>

      <p v-else class="wishlist-page__empty">찜한 상품이 없습니다.</p>
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

.wishlist-page {
  display: grid;
  gap: var(--space-8);
}

.wishlist-page__message {
  color: var(--color-text-secondary);
  font-size: var(--font-size-caption);
  line-height: var(--line-height-control);
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface-secondary);
}

.wishlist-page__content {
  display: grid;
  grid-template-columns: var(--filter-panel-width) minmax(0, 1fr);
  align-items: start;
  gap: var(--space-8);
}

.wishlist-page__state,
.wishlist-page__state button {
  min-height: var(--button-height-small);
}

.wishlist-page__state button {
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-control);
}

.wishlist-page__state button:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.wishlist-results {
  display: grid;
  min-width: 0;
  gap: var(--space-5);
}

.wishlist-results__header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--space-6);
  min-height: var(--button-height-standard);
  margin-bottom: var(--space-5);
  border-bottom: 1px solid var(--color-border);
}

.wishlist-results__tabs {
  display: flex;
  align-self: stretch;
}

.wishlist-results__tab {
  min-width: 96px;
  padding: 0 var(--space-4);
  border: 0;
  border-bottom: 2px solid transparent;
  background: transparent;
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-semibold);
}

.wishlist-results__tab:hover,
.wishlist-results__tab--active {
  border-bottom-color: var(--color-primary);
  color: var(--color-primary);
}

.wishlist-results__tab:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: calc(var(--focus-ring-offset) * -1);
}

.wishlist-results__toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding-bottom: var(--space-2);
  color: var(--color-text-secondary);
  font-size: var(--font-size-caption);
}

.wishlist-results__toolbar p {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.01em;
}

.wishlist-results__toolbar select {
  min-width: 136px;
  height: var(--button-height-small);
  padding: 0 var(--space-8) 0 var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  outline: 0;
  background: var(--color-surface);
  color: var(--color-text-primary);
}

.wishlist-results__toolbar select:focus-visible {
  border-color: var(--color-border-underline);
}

.wishlist-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space-5);
}

.wishlist-page__empty,
.wishlist-page__state {
  display: grid;
  justify-items: center;
  min-height: var(--surface-min-height-lg);
  place-content: center;
  gap: var(--space-4);
  padding: var(--space-8);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface-secondary);
  color: var(--color-text-secondary);
  text-align: center;
}

.wishlist-page__empty svg {
  width: var(--button-height-small);
  height: var(--button-height-small);
  margin-bottom: var(--space-4);
  color: var(--color-text-muted);
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-width: 1.6;
}

.wishlist-page__empty strong {
  color: var(--color-text-primary);
  font-size: var(--font-size-lg);
}

.wishlist-page__empty p {
  margin-top: var(--space-2);
  font-size: var(--font-size-button-small);
}

.wishlist-page__empty button {
  min-height: var(--button-height-small);
  margin-top: var(--space-5);
  padding: 0 var(--space-4);
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-control);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-weight: var(--font-weight-semibold);
}

.wishlist-page__empty button:hover {
  border-color: var(--color-primary-hover);
  background: var(--color-primary-hover);
}

.wishlist-page__empty button:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

@media (max-width: 1180px) {
  .wishlist-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 1024px) {
  .wishlist-page__content {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .wishlist-results__header {
    align-items: stretch;
    flex-direction: column;
    border-bottom: 0;
  }

  .wishlist-results__tabs {
    min-height: var(--button-height-standard);
    border-bottom: 1px solid var(--color-border);
  }

  .wishlist-results__tab {
    flex: 1;
    min-width: 0;
    padding: 0 var(--space-2);
  }

  .wishlist-results__toolbar {
    justify-content: space-between;
  }

  .wishlist-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .wishlist-grid {
    grid-template-columns: 1fr;
  }
}
</style>
