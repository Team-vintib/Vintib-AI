<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/domains/auth/stores/authStore'
import { getMyWishList, removeMyWish } from '@/domains/my/api/myApi'
import type { MyWishItem } from '@/domains/my/types/my.types'
import { getCategories } from '@/domains/product/api/productApi'
import {
  PRODUCT_CONDITION_OPTIONS,
  PRODUCT_SALE_TYPE_TABS,
} from '@/domains/product/constants/productListMockData'
import { useWishStore } from '@/domains/product/stores/wishStore'
import type { ProductSaleType, ProductSaleTypeTab } from '@/domains/product/types/productList.types'
import { normalizeApiError } from '@/shared/api/http'
import AppSearchBar from '@/shared/components/AppSearchBar.vue'
import { ROUTE_NAMES, ROUTE_PATHS } from '@/shared/constants/routes'
import DefaultLayout from '@/shared/layouts/DefaultLayout.vue'

interface WishlistCategoryOption {
  id: number
  label: string
}

const router = useRouter()
const authStore = useAuthStore()
const wishStore = useWishStore()

const wishes = ref<MyWishItem[]>([])
const categoryOptions = ref<WishlistCategoryOption[]>([])
const loadState = ref<'idle' | 'loading' | 'success' | 'error'>('idle')
const errorMessage = ref('')
const actionMessage = ref('')
const removingProductId = ref<number | null>(null)
const searchKeyword = ref('')
const selectedSaleType = ref<ProductSaleTypeTab['id']>('ALL')
const selectedCategoryIds = ref<number[]>([])
const selectedConditionIds = ref<string[]>([])
const minimumPrice = ref('')
const maximumPrice = ref('')
const appliedMinimumPrice = ref<number | null>(null)
const appliedMaximumPrice = ref<number | null>(null)
const priceError = ref('')

const filteredWishes = computed(() => {
  const normalizedKeyword = searchKeyword.value.trim().toLowerCase()

  return wishes.value.filter((wish) => {
    const product = wish.product
    const matchesKeyword =
      !normalizedKeyword ||
      `${product.name} ${product.brand}`.toLowerCase().includes(normalizedKeyword)
    const matchesSaleType = selectedSaleType.value === 'ALL' || product.saleType === selectedSaleType.value
    const matchesCategory =
      selectedCategoryIds.value.length === 0 ||
      (typeof product.categoryId === 'number' && selectedCategoryIds.value.includes(product.categoryId))
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

const toggleCategory = (categoryId: number) => {
  selectedCategoryIds.value = selectedCategoryIds.value.includes(categoryId)
    ? selectedCategoryIds.value.filter((selectedId) => selectedId !== categoryId)
    : [...selectedCategoryIds.value, categoryId]
}

const toggleCondition = (conditionId: string) => {
  selectedConditionIds.value = selectedConditionIds.value.includes(conditionId)
    ? selectedConditionIds.value.filter((selectedId) => selectedId !== conditionId)
    : [...selectedConditionIds.value, conditionId]
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
  searchKeyword.value = ''
  selectedSaleType.value = 'ALL'
  selectedCategoryIds.value = []
  selectedConditionIds.value = []
  minimumPrice.value = ''
  maximumPrice.value = ''
  appliedMinimumPrice.value = null
  appliedMaximumPrice.value = null
  priceError.value = ''
  actionMessage.value = '찜 목록 조건을 초기화했습니다.'
}

const getSaleTypeCount = (saleType: ProductSaleTypeTab['id']) => {
  if (saleType === 'ALL') {
    return wishes.value.length
  }

  return wishes.value.filter((wish) => wish.product.saleType === saleType).length
}

const getStatusLabel = (saleStatus?: string) => {
  if (saleStatus === 'SOLD') return '판매 완료'
  if (saleStatus === 'PRIVATE') return '비공개'
  if (saleStatus === 'AUCTION_IN_PROGRESS') return '경매 진행 중'
  if (saleStatus === 'AUCTION_SCHEDULED') return '경매 예정'

  return ''
}

const formatPrice = (saleType: ProductSaleType, price: number) =>
  saleType === 'AUCTION' ? '경매 예정' : `${price.toLocaleString('ko-KR')}P`

const goToProductDetail = (productId: number) => {
  void router.push({ name: ROUTE_NAMES.PRODUCT_DETAIL, params: { productId } })
}

const removeWishItem = async (productId: number) => {
  if (!authStore.user?.id) {
    return
  }

  removingProductId.value = productId
  actionMessage.value = ''

  try {
    await removeMyWish(authStore.user.id, productId)
    wishes.value = wishes.value.filter((wish) => wish.product.id !== productId)
    wishStore.setProductWish(productId, false)
    actionMessage.value = '찜한 상품에서 제거했습니다.'
  } catch (error) {
    actionMessage.value = normalizeApiError(error).message
  } finally {
    removingProductId.value = null
  }
}

const loadCategories = async () => {
  try {
    const categories = await getCategories()

    categoryOptions.value = categories
      .filter((category) => category.depth <= 2)
      .map((category) => ({ id: category.id, label: category.name }))
  } catch {
    categoryOptions.value = []
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
  void loadCategories()
  void loadWishes()
})
</script>

<template>
  <DefaultLayout>
    <section class="wishlist-page" aria-labelledby="wishlist-title">
      <header class="wishlist-page__header">
        <div>
          <h1 id="wishlist-title">찜한 상품</h1>
          <p>관심 상품을 검색하고 구매 방식별로 확인하세요.</p>
        </div>
        <strong>{{ wishes.length.toLocaleString('ko-KR') }}개</strong>
      </header>

      <p v-if="actionMessage" class="wishlist-page__message" role="status">
        {{ actionMessage }}
      </p>

      <AppSearchBar
        v-model="searchKeyword"
        search-label="찜 상품 검색"
        placeholder="찜한 상품명 또는 브랜드를 검색해 보세요"
        @submit="applyFilters"
      />

      <div v-if="loadState === 'loading'" class="wishlist-page__state" role="status">
        찜한 상품을 불러오는 중입니다.
      </div>

      <div v-else-if="loadState === 'error'" class="wishlist-page__state" role="alert">
        <strong>{{ errorMessage }}</strong>
        <button type="button" @click="loadWishes">다시 시도</button>
      </div>

      <div v-else-if="wishes.length" class="wishlist-page__content">
        <aside class="wishlist-filter" aria-label="찜 상품 필터">
          <fieldset class="wishlist-filter__group">
            <legend>카테고리</legend>
            <p v-if="!categoryOptions.length" class="wishlist-filter__empty">
              카테고리를 불러오는 중입니다.
            </p>
            <label v-for="category in categoryOptions" :key="category.id">
              <input
                type="checkbox"
                :checked="selectedCategoryIds.includes(category.id)"
                @change="toggleCategory(category.id)"
              />
              <span>{{ category.label }}</span>
            </label>
          </fieldset>

          <fieldset class="wishlist-filter__group">
            <legend>상태</legend>
            <label v-for="condition in PRODUCT_CONDITION_OPTIONS" :key="condition.id">
              <input
                type="checkbox"
                :checked="selectedConditionIds.includes(condition.id)"
                @change="toggleCondition(condition.id)"
              />
              <span>{{ condition.label }}</span>
            </label>
          </fieldset>

          <fieldset class="wishlist-filter__group">
            <legend>가격</legend>
            <div class="wishlist-filter__price">
              <label>
                <span>최소 가격</span>
                <input
                  v-model="minimumPrice"
                  type="number"
                  min="0"
                  step="1000"
                  inputmode="numeric"
                  placeholder="0"
                  :aria-invalid="Boolean(priceError)"
                  :aria-describedby="priceError ? 'wishlist-price-error' : undefined"
                />
              </label>
              <label>
                <span>최대 가격</span>
                <input
                  v-model="maximumPrice"
                  type="number"
                  min="0"
                  step="1000"
                  inputmode="numeric"
                  placeholder="제한 없음"
                  :aria-invalid="Boolean(priceError)"
                  :aria-describedby="priceError ? 'wishlist-price-error' : undefined"
                />
              </label>
            </div>
            <p v-if="priceError" id="wishlist-price-error" class="wishlist-filter__error" role="alert">
              {{ priceError }}
            </p>
          </fieldset>

          <div class="wishlist-filter__actions">
            <button type="button" @click="resetFilters">
              초기화
              <span v-if="selectedFilterCount">({{ selectedFilterCount }})</span>
            </button>
            <button type="button" @click="applyFilters">적용</button>
          </div>
        </aside>

        <div class="wishlist-results">
          <div class="wishlist-tabs" role="tablist" aria-label="찜 상품 판매 방식">
            <button
              v-for="tab in PRODUCT_SALE_TYPE_TABS"
              :key="tab.id"
              type="button"
              role="tab"
              :aria-selected="selectedSaleType === tab.id"
              :class="{ 'wishlist-tabs__item--active': selectedSaleType === tab.id }"
              @click="selectSaleType(tab.id)"
            >
              {{ tab.label }}
              <span>{{ getSaleTypeCount(tab.id) }}</span>
            </button>
          </div>

          <p class="wishlist-results__message" role="status">{{ resultMessage }}</p>

          <div v-if="filteredWishes.length" class="wishlist-grid">
            <article v-for="wish in filteredWishes" :key="wish.product.id" class="wishlist-card">
              <button type="button" class="wishlist-card__main" @click="goToProductDetail(wish.product.id)">
                <img :src="wish.product.imageUrl" :alt="wish.product.imageAlt" />
                <span>{{ wish.product.saleType === 'AUCTION' ? '경매 예정' : '즉시 구매' }}</span>
                <strong>{{ wish.product.name }}</strong>
                <p>{{ formatPrice(wish.product.saleType, wish.product.price) }}</p>
              </button>
              <div class="wishlist-card__meta">
                <span>{{ wish.product.brand }}</span>
              </div>
              <div class="wishlist-card__status">
                <span v-if="getStatusLabel(wish.product.saleStatus)">
                  {{ getStatusLabel(wish.product.saleStatus) }}
                </span>
                <span>{{ wish.product.conditionGrade }}급</span>
              </div>
              <button
                type="button"
                class="wishlist-card__remove"
                :disabled="removingProductId === wish.product.id"
                @click="removeWishItem(wish.product.id)"
              >
                {{ removingProductId === wish.product.id ? '해제 중' : '찜 해제' }}
              </button>
            </article>
          </div>
          <p v-else class="wishlist-page__empty">검색어나 필터 조건을 다시 확인해 주세요.</p>
        </div>
      </div>

      <p v-else class="wishlist-page__empty">찜한 상품이 없습니다.</p>
    </section>
  </DefaultLayout>
</template>

<style scoped lang="scss">
.wishlist-page {
  display: grid;
  gap: var(--space-8);
}

.wishlist-page__header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--space-6);
}

.wishlist-page__header h1 {
  color: var(--color-text-primary);
  font-size: 36px;
  font-weight: 700;
  line-height: 48px;
}

.wishlist-page__header p,
.wishlist-page__header strong {
  color: var(--color-text-secondary);
  font-size: 16px;
  line-height: 26px;
}

.wishlist-page__message,
.wishlist-results__message {
  color: var(--color-text-secondary);
  font-size: 13px;
  line-height: 20px;
}

.wishlist-page__message {
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface-secondary);
}

.wishlist-page__content {
  display: grid;
  grid-template-columns: 224px minmax(0, 1fr);
  align-items: start;
  gap: var(--space-8);
}

.wishlist-filter {
  position: sticky;
  top: var(--space-6);
  display: grid;
  gap: var(--space-6);
  padding: var(--space-6);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
}

.wishlist-filter__group {
  display: grid;
  gap: var(--space-3);
  min-width: 0;
  border: 0;
}

.wishlist-filter__group legend {
  color: var(--color-text-primary);
  font-size: 14px;
  font-weight: var(--font-weight-bold);
  line-height: 20px;
}

.wishlist-filter__price input {
  width: 100%;
  min-width: 0;
  height: var(--button-height-small);
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-primary);
}

.wishlist-filter__price input:focus {
  border-color: var(--color-primary);
  outline: 0;
  box-shadow: none;
}

.wishlist-filter__actions button,
.wishlist-card__remove,
.wishlist-page__state button {
  min-height: var(--button-height-small);
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: var(--font-weight-bold);
  line-height: 20px;
}

.wishlist-filter__actions button:hover,
.wishlist-card__remove:hover:not(:disabled),
.wishlist-page__state button:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.wishlist-filter__group label {
  display: flex;
  align-items: center;
  min-height: 28px;
  gap: var(--space-2);
  color: var(--color-text-secondary);
  font-size: 13px;
  line-height: 18px;
  cursor: pointer;
}

.wishlist-filter__group input[type='checkbox'] {
  width: 15px;
  height: 15px;
  accent-color: var(--color-primary);
}

.wishlist-filter__empty,
.wishlist-filter__error {
  color: var(--color-text-secondary);
  font-size: 13px;
  line-height: 20px;
}

.wishlist-filter__error {
  color: var(--color-error);
  font-weight: var(--font-weight-bold);
}

.wishlist-filter__price {
  display: grid;
  gap: var(--space-3);
}

.wishlist-filter__price label {
  display: grid;
  gap: var(--space-2);
  color: var(--color-text-secondary);
  font-size: 12px;
  font-weight: var(--font-weight-bold);
  line-height: 18px;
}

.wishlist-filter__actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-2);
}

.wishlist-filter__actions button:last-child {
  border-color: var(--color-primary);
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

.wishlist-results {
  display: grid;
  min-width: 0;
  gap: var(--space-5);
}

.wishlist-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--color-border);
}

.wishlist-tabs button {
  display: inline-flex;
  align-items: center;
  min-height: 36px;
  gap: var(--space-2);
  padding: 0 var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: var(--font-weight-bold);
}

.wishlist-tabs button:hover,
.wishlist-tabs__item--active {
  border-color: var(--color-primary) !important;
  background: var(--color-primary-soft) !important;
  color: var(--color-primary) !important;
}

.wishlist-tabs button span {
  color: inherit;
  font-size: 12px;
}

.wishlist-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-5);
}

.wishlist-card {
  display: grid;
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
  box-shadow: none;
}

.wishlist-card__main {
  display: grid;
  width: 100%;
  min-width: 0;
  padding: 0;
  border: 0;
  background: transparent;
  color: inherit;
  text-align: left;
}

.wishlist-card__main:hover strong {
  color: var(--color-primary);
}

.wishlist-card__main img {
  display: block;
  width: 100%;
  aspect-ratio: 1 / 1;
  background: var(--color-surface-secondary);
  object-fit: cover;
}

.wishlist-card__main span,
.wishlist-card__main strong,
.wishlist-card__main p {
  margin-right: var(--space-4);
  margin-left: var(--space-4);
}

.wishlist-card__main span {
  justify-self: start;
  min-height: 24px;
  padding: 2px 10px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-badge);
  margin-top: var(--space-4);
  background: var(--color-surface-secondary);
  color: var(--color-text-secondary);
  font-size: 12px;
  font-weight: var(--font-weight-bold);
  line-height: 18px;
}

.wishlist-card__main strong {
  overflow: hidden;
  margin-top: var(--space-2);
  color: var(--color-text-primary);
  font-size: 15px;
  font-weight: var(--font-weight-extrabold);
  line-height: 22px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.wishlist-card__main p {
  margin-top: var(--space-2);
  color: var(--color-text-primary);
  font-size: 16px;
  font-weight: var(--font-weight-extrabold);
  line-height: 24px;
}

.wishlist-card__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  min-width: 0;
  padding: var(--space-3) var(--space-4) 0;
  color: var(--color-text-secondary);
  font-size: 12px;
  line-height: 18px;
}

.wishlist-card__meta span {
  overflow: hidden;
  min-width: 0;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.wishlist-card__status {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  min-width: 0;
  padding: var(--space-3) var(--space-4) 0;
}

.wishlist-card__status span {
  min-height: 22px;
  padding: 1px var(--space-2);
  border-radius: var(--radius-badge);
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-size: 12px;
  font-weight: var(--font-weight-bold);
  line-height: 18px;
}

.wishlist-card__remove {
  margin: var(--space-3) var(--space-4) var(--space-4);
}

.wishlist-card__remove:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.wishlist-page__empty,
.wishlist-page__state {
  display: grid;
  justify-items: center;
  min-height: 320px;
  place-content: center;
  gap: var(--space-4);
  padding: var(--space-8);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface-secondary);
  color: var(--color-text-secondary);
  text-align: center;
}

@media (max-width: 1180px) {
  .wishlist-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 980px) {
  .wishlist-page__content {
    grid-template-columns: 1fr;
  }

  .wishlist-filter {
    position: static;
  }
}

@media (max-width: 640px) {
  .wishlist-page__header {
    align-items: flex-start;
    flex-direction: column;
  }

  .wishlist-page__header h1 {
    font-size: 30px;
    line-height: 40px;
  }

  .wishlist-filter__actions,
  .wishlist-grid {
    grid-template-columns: 1fr;
  }
}
</style>
