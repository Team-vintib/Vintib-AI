<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import SearchLiveResultCard from '@/domains/search/components/SearchLiveResultCard.vue'
import SearchMemberResultCard from '@/domains/search/components/SearchMemberResultCard.vue'
import SearchResultTabs from '@/domains/search/components/SearchResultTabs.vue'
import SearchStatePanel from '@/domains/search/components/SearchStatePanel.vue'
import { SEARCH_MOCK_RESULTS } from '@/domains/search/constants/searchMockData'
import type {
  SearchProductResult,
  SearchResultTabId,
  SearchStateContent,
  SearchStateKind,
} from '@/domains/search/types/search.types'
import { ROUTE_NAMES } from '@/shared/constants/routes'
import DefaultLayout from '@/shared/layouts/DefaultLayout.vue'

const route = useRoute()
const router = useRouter()

const validTabIds: SearchResultTabId[] = ['all', 'product', 'live', 'member']
const validMockStatuses = ['loading', 'error', 'empty'] as const
const categoryFilterOptions = [
  { id: '아우터', label: '아우터' },
  { id: '상의', label: '상의' },
  { id: '하의', label: '하의' },
  { id: '원피스', label: '원피스' },
  { id: '신발', label: '신발' },
  { id: '액세서리', label: '액세서리' },
  { id: '시계', label: '시계' },
] as const
const conditionFilterOptions = [
  { id: 'S', label: 'S급' },
  { id: 'A', label: 'A급' },
  { id: 'B', label: 'B급' },
  { id: 'C', label: 'C급' },
] as const
const saleTypeFilterOptions = [
  { id: 'DIRECT', label: '즉시 구매' },
  { id: 'AUCTION', label: '경매' },
] as const

const getQueryString = (value: unknown) => (typeof value === 'string' ? value : '')
const getQueryArray = (value: unknown) =>
  getQueryString(value)
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
const getQueryNumber = (value: unknown) => {
  const queryValue = getQueryString(value)

  if (!queryValue) {
    return undefined
  }

  const parsedValue = Number(queryValue)

  return Number.isFinite(parsedValue) ? parsedValue : undefined
}

const queryKeyword = computed(() => getQueryString(route.query.keyword).trim())
const queryCategoryIds = computed(() => getQueryArray(route.query.categories))
const queryConditionIds = computed(() => getQueryArray(route.query.conditions))
const querySaleTypeIds = computed(() => getQueryArray(route.query.saleTypes))
const queryMinPrice = computed(() => getQueryNumber(route.query.minPrice))
const queryMaxPrice = computed(() => getQueryNumber(route.query.maxPrice))
const mockStatus = computed(() => {
  const queryStatus = getQueryString(route.query.status)

  return validMockStatuses.includes(queryStatus as (typeof validMockStatuses)[number])
    ? queryStatus
    : ''
})
const activeTabId = computed<SearchResultTabId>(() => {
  const queryType = getQueryString(route.query.type)

  return validTabIds.includes(queryType as SearchResultTabId)
    ? (queryType as SearchResultTabId)
    : 'all'
})

const searchKeyword = ref(queryKeyword.value)
const selectedCategoryIds = ref<string[]>(queryCategoryIds.value)
const selectedConditionIds = ref<string[]>(queryConditionIds.value)
const selectedSaleTypeIds = ref<string[]>(querySaleTypeIds.value)
const minPriceInput = ref(queryMinPrice.value?.toString() ?? '')
const maxPriceInput = ref(queryMaxPrice.value?.toString() ?? '')
const likedProductIds = ref(
  new Set(
    SEARCH_MOCK_RESULTS.products.filter((product) => product.isLiked).map((product) => product.id),
  ),
)
const followedMemberIds = ref(
  new Set(
    SEARCH_MOCK_RESULTS.members.filter((member) => member.isFollowing).map((member) => member.id),
  ),
)
const liveMessage = ref('')

watch(queryKeyword, (keyword) => {
  searchKeyword.value = keyword
})

watch(queryCategoryIds, (categoryIds) => {
  selectedCategoryIds.value = categoryIds
})

watch(queryConditionIds, (conditionIds) => {
  selectedConditionIds.value = conditionIds
})

watch(querySaleTypeIds, (saleTypeIds) => {
  selectedSaleTypeIds.value = saleTypeIds
})

watch(queryMinPrice, (minPrice) => {
  minPriceInput.value = minPrice?.toString() ?? ''
})

watch(queryMaxPrice, (maxPrice) => {
  maxPriceInput.value = maxPrice?.toString() ?? ''
})

const isPriceRangeInvalid = computed(
  () =>
    queryMinPrice.value !== undefined &&
    queryMaxPrice.value !== undefined &&
    queryMinPrice.value > queryMaxPrice.value,
)

const hasPriceFilter = computed(
  () => queryMinPrice.value !== undefined || queryMaxPrice.value !== undefined,
)
const hasProductFilter = computed(
  () =>
    hasPriceFilter.value ||
    queryCategoryIds.value.length > 0 ||
    queryConditionIds.value.length > 0 ||
    querySaleTypeIds.value.length > 0,
)

const filteredProducts = computed(() => {
  if (mockStatus.value === 'empty') {
    return []
  }

  if (isPriceRangeInvalid.value) {
    return []
  }

  return SEARCH_MOCK_RESULTS.products.filter((product) => {
    if (
      queryCategoryIds.value.length > 0 &&
      !queryCategoryIds.value.includes(product.categoryName)
    ) {
      return false
    }

    if (
      queryConditionIds.value.length > 0 &&
      !queryConditionIds.value.includes(product.conditionGrade)
    ) {
      return false
    }

    if (querySaleTypeIds.value.length > 0 && !querySaleTypeIds.value.includes(product.saleType)) {
      return false
    }

    if (queryMinPrice.value !== undefined && product.price < queryMinPrice.value) {
      return false
    }

    if (queryMaxPrice.value !== undefined && product.price > queryMaxPrice.value) {
      return false
    }

    return true
  })
})

const visibleLives = computed(() => (mockStatus.value === 'empty' ? [] : SEARCH_MOCK_RESULTS.lives))
const visibleMembers = computed(() =>
  mockStatus.value === 'empty' ? [] : SEARCH_MOCK_RESULTS.members,
)
const totalResultCount = computed(
  () => filteredProducts.value.length + visibleLives.value.length + visibleMembers.value.length,
)

const activeTabResultCount = computed(() => {
  if (activeTabId.value === 'product') {
    return filteredProducts.value.length
  }

  if (activeTabId.value === 'live') {
    return visibleLives.value.length
  }

  if (activeTabId.value === 'member') {
    return visibleMembers.value.length
  }

  return totalResultCount.value
})

const resultTabs = computed(() => [
  { id: 'all' as const, label: '전체', count: totalResultCount.value },
  { id: 'product' as const, label: '상품', count: filteredProducts.value.length },
  { id: 'live' as const, label: '라이브', count: visibleLives.value.length },
  { id: 'member' as const, label: '회원', count: visibleMembers.value.length },
])

const resultSummary = computed(() => {
  if (!queryKeyword.value) {
    return '검색어를 입력하면 상품, 라이브, 회원 결과를 함께 확인할 수 있습니다.'
  }

  return `'${queryKeyword.value}' 검색 결과 ${totalResultCount.value.toLocaleString('ko-KR')}건`
})

const panelTitle = computed(
  () => resultTabs.value.find((tab) => tab.id === activeTabId.value)?.label ?? '전체',
)

const hasKeyword = computed(() => queryKeyword.value.length > 0)
const searchState = computed<SearchStateKind | null>(() => {
  if (!hasKeyword.value) {
    return 'initial'
  }

  if (mockStatus.value === 'loading') {
    return 'loading'
  }

  if (mockStatus.value === 'error') {
    return 'error'
  }

  if (isPriceRangeInvalid.value) {
    return 'price-error'
  }

  if (activeTabResultCount.value === 0) {
    return hasProductFilter.value ? 'filter-empty' : 'empty'
  }

  return null
})

const stateContent = computed<SearchStateContent>(() => {
  if (searchState.value === 'loading') {
    return {
      title: '검색 결과를 불러오는 중입니다.',
      description: '입력한 검색어와 필터 조건에 맞는 결과를 확인하고 있습니다.',
    }
  }

  if (searchState.value === 'error') {
    return {
      title: '검색 결과를 불러오지 못했습니다.',
      description: '잠시 후 다시 시도해 주세요. 같은 문제가 계속되면 다른 검색어로 다시 확인해 주세요.',
      actionLabel: '다시 시도',
    }
  }

  if (searchState.value === 'price-error') {
    return {
      title: '가격 범위를 확인해 주세요.',
      description: '최소 가격은 최대 가격보다 클 수 없습니다.',
      actionLabel: '가격 초기화',
    }
  }

  if (searchState.value === 'filter-empty') {
    return {
      title: '필터 조건에 맞는 결과가 없습니다.',
      description: '가격 범위를 넓히거나 필터를 초기화해 다시 확인해 주세요.',
      actionLabel: '필터 초기화',
    }
  }

  if (searchState.value === 'empty') {
    return {
      title: '검색 결과가 없습니다.',
      description: '검색어를 다시 입력하거나 다른 유형의 결과를 확인해 보세요.',
      actionLabel: '검색어 수정',
    }
  }

  return {
    title: '검색어를 입력해 주세요.',
    description: '상품, 라이브, 회원 결과가 유형별 탭으로 정리됩니다.',
  }
})

const pushSearchQuery = async (query: Record<string, string | undefined>) => {
  await router.push({
    name: ROUTE_NAMES.SEARCH,
    query,
  })
}

const submitSearch = async () => {
  const keyword = searchKeyword.value.trim()

  await pushSearchQuery(keyword ? { keyword } : {})
}

const selectTab = async (tabId: SearchResultTabId) => {
  await pushSearchQuery({
    ...route.query,
    type: tabId === 'all' ? undefined : tabId,
  } as Record<string, string | undefined>)

  liveMessage.value = `${resultTabs.value.find((tab) => tab.id === tabId)?.label ?? '전체'} 결과 탭을 선택했습니다.`
}

const toggleFilterValue = (selectedIds: string[], targetId: string, isSelected: boolean) => {
  if (isSelected) {
    return [...selectedIds, targetId]
  }

  return selectedIds.filter((id) => id !== targetId)
}

const handleCategoryChange = (event: Event, categoryId: string) => {
  selectedCategoryIds.value = toggleFilterValue(
    selectedCategoryIds.value,
    categoryId,
    (event.target as HTMLInputElement).checked,
  )
}

const handleConditionChange = (event: Event, conditionId: string) => {
  selectedConditionIds.value = toggleFilterValue(
    selectedConditionIds.value,
    conditionId,
    (event.target as HTMLInputElement).checked,
  )
}

const handleSaleTypeChange = (event: Event, saleTypeId: string) => {
  selectedSaleTypeIds.value = toggleFilterValue(
    selectedSaleTypeIds.value,
    saleTypeId,
    (event.target as HTMLInputElement).checked,
  )
}

const applyProductFilters = async () => {
  const minPrice = minPriceInput.value.trim()
  const maxPrice = maxPriceInput.value.trim()

  await pushSearchQuery({
    ...route.query,
    categories: selectedCategoryIds.value.length ? selectedCategoryIds.value.join(',') : undefined,
    conditions: selectedConditionIds.value.length
      ? selectedConditionIds.value.join(',')
      : undefined,
    saleTypes: selectedSaleTypeIds.value.length ? selectedSaleTypeIds.value.join(',') : undefined,
    minPrice: minPrice || undefined,
    maxPrice: maxPrice || undefined,
    status: undefined,
  } as Record<string, string | undefined>)

  liveMessage.value = '가격 필터를 적용했습니다.'
}

const resetProductFilters = async () => {
  selectedCategoryIds.value = []
  selectedConditionIds.value = []
  selectedSaleTypeIds.value = []
  minPriceInput.value = ''
  maxPriceInput.value = ''

  await pushSearchQuery({
    ...route.query,
    categories: undefined,
    conditions: undefined,
    saleTypes: undefined,
    minPrice: undefined,
    maxPrice: undefined,
    status: undefined,
  } as Record<string, string | undefined>)

  liveMessage.value = '필터를 초기화했습니다.'
}

const retrySearch = async () => {
  await pushSearchQuery({
    ...route.query,
    status: undefined,
  } as Record<string, string | undefined>)
}

const handleStateAction = async () => {
  if (searchState.value === 'price-error' || searchState.value === 'filter-empty') {
    await resetProductFilters()
    return
  }

  if (searchState.value === 'error') {
    await retrySearch()
    return
  }

  if (searchState.value === 'empty') {
    searchKeyword.value = ''
  }
}

const toggleLike = (productId: number) => {
  const nextLikedProductIds = new Set(likedProductIds.value)

  if (nextLikedProductIds.has(productId)) {
    nextLikedProductIds.delete(productId)
  } else {
    nextLikedProductIds.add(productId)
  }

  likedProductIds.value = nextLikedProductIds
}

const toggleFollow = (memberId: number) => {
  const nextFollowedMemberIds = new Set(followedMemberIds.value)

  if (nextFollowedMemberIds.has(memberId)) {
    nextFollowedMemberIds.delete(memberId)
  } else {
    nextFollowedMemberIds.add(memberId)
  }

  followedMemberIds.value = nextFollowedMemberIds
}

const formatPrice = (value: number) => `${value.toLocaleString('ko-KR')}P`
const getSaleTypeLabel = (product: SearchProductResult) =>
  product.saleType === 'AUCTION' ? '경매 예정' : '바로 구매'
</script>

<template>
  <DefaultLayout>
    <section class="search-page" aria-labelledby="search-page-title">
      <form class="search-page__search" role="search" @submit.prevent="submitSearch">
        <label class="sr-only" for="search-keyword">통합 검색어</label>
        <svg class="search-page__search-icon" aria-hidden="true" viewBox="0 0 24 24">
          <circle cx="11" cy="11" r="7" />
          <path d="m20 20-3.8-3.8" />
        </svg>
        <input
          id="search-keyword"
          v-model="searchKeyword"
          type="search"
          placeholder="브랜드, 상품명, 판매자 또는 라이브를 검색해 보세요"
        />
        <button type="submit">검색</button>
      </form>

      <header class="search-page__header">
        <div>
          <p class="search-page__eyebrow">통합 검색</p>
          <h1 id="search-page-title" class="search-page__title">{{ resultSummary }}</h1>
        </div>
      </header>

      <div class="search-page__layout">
        <aside class="search-page__filters" aria-label="검색 필터">
          <h2 class="search-page__filter-title">필터</h2>

          <form class="search-page__product-filter" @submit.prevent="applyProductFilters">
            <fieldset>
              <legend>카테고리</legend>

              <label
                v-for="option in categoryFilterOptions"
                :key="option.id"
                class="search-page__checkbox-option"
              >
                <input
                  type="checkbox"
                  :checked="selectedCategoryIds.includes(option.id)"
                  @change="handleCategoryChange($event, option.id)"
                />
                <span>{{ option.label }}</span>
              </label>
            </fieldset>

            <fieldset>
              <legend>상태</legend>

              <label
                v-for="option in conditionFilterOptions"
                :key="option.id"
                class="search-page__checkbox-option"
              >
                <input
                  type="checkbox"
                  :checked="selectedConditionIds.includes(option.id)"
                  @change="handleConditionChange($event, option.id)"
                />
                <span>{{ option.label }}</span>
              </label>
            </fieldset>

            <fieldset>
              <legend>가격대</legend>

              <label for="search-min-price">최소 가격</label>
              <input
                id="search-min-price"
                v-model="minPriceInput"
                inputmode="numeric"
                type="number"
                min="0"
                placeholder="예: 10000"
              />

              <label for="search-max-price">최대 가격</label>
              <input
                id="search-max-price"
                v-model="maxPriceInput"
                inputmode="numeric"
                type="number"
                min="0"
                placeholder="예: 100000"
              />

              <p v-if="isPriceRangeInvalid" class="search-page__field-error" role="alert">
                최소 가격은 최대 가격보다 클 수 없습니다.
              </p>
            </fieldset>

            <fieldset>
              <legend>판매 유형</legend>

              <label
                v-for="option in saleTypeFilterOptions"
                :key="option.id"
                class="search-page__checkbox-option"
              >
                <input
                  type="checkbox"
                  :checked="selectedSaleTypeIds.includes(option.id)"
                  @change="handleSaleTypeChange($event, option.id)"
                />
                <span>{{ option.label }}</span>
              </label>
            </fieldset>

            <div class="search-page__filter-actions">
              <button type="button" @click="resetProductFilters">초기화</button>
              <button type="submit">적용</button>
            </div>
          </form>
        </aside>

        <div class="search-page__results">
          <SearchResultTabs
            :tabs="resultTabs"
            :active-tab-id="activeTabId"
            @select="selectTab"
          />

          <p class="sr-only" aria-live="polite">{{ liveMessage }}</p>

          <div
            :id="`search-panel-${activeTabId}`"
            class="search-page__tabpanel"
            role="tabpanel"
            :aria-labelledby="`search-tab-${activeTabId}`"
          >
            <SearchStatePanel
              v-if="searchState"
              :state="searchState"
              :content="stateContent"
              @action="handleStateAction"
            />

            <template v-else>
              <section
                v-if="activeTabId === 'all' || activeTabId === 'product'"
                class="search-page__section"
                aria-labelledby="search-products-title"
              >
                <div class="search-page__section-header">
                  <h2 id="search-products-title">상품</h2>
                  <span>{{ filteredProducts.length }}개</span>
                </div>

                <div class="search-page__product-grid">
                  <article
                    v-for="product in filteredProducts"
                    :key="product.id"
                    class="search-product-card"
                  >
                    <RouterLink
                      class="search-product-card__media"
                      :to="{ name: ROUTE_NAMES.PRODUCT_DETAIL, params: { productId: product.id } }"
                    >
                      <img
                        class="search-product-card__image"
                        :src="product.imageUrl"
                        :alt="product.imageAlt"
                      />
                      <span class="search-product-card__grade">{{ product.conditionGrade }}급</span>
                    </RouterLink>

                    <button
                      class="search-product-card__like"
                      :class="{
                        'search-product-card__like--active': likedProductIds.has(product.id),
                      }"
                      type="button"
                      :aria-label="
                        likedProductIds.has(product.id)
                          ? `${product.name} 찜 해제`
                          : `${product.name} 찜하기`
                      "
                      :aria-pressed="likedProductIds.has(product.id)"
                      @click="toggleLike(product.id)"
                    >
                      <svg aria-hidden="true" viewBox="0 0 24 24">
                        <path
                          d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78L12 21.23l8.84-8.84a5.5 5.5 0 0 0 0-7.78Z"
                        />
                      </svg>
                    </button>

                    <div class="search-product-card__body">
                      <p class="search-product-card__brand">{{ product.brand }}</p>
                      <RouterLink
                        class="search-product-card__name"
                        :to="{ name: ROUTE_NAMES.PRODUCT_DETAIL, params: { productId: product.id } }"
                      >
                        {{ product.name }}
                      </RouterLink>
                      <p class="search-product-card__seller">판매자 {{ product.sellerName }}</p>
                      <div class="search-product-card__meta">
                        <strong>{{ formatPrice(product.price) }}</strong>
                        <span
                          class="search-product-card__badge"
                          :class="{
                            'search-product-card__badge--auction': product.saleType === 'AUCTION',
                          }"
                        >
                          {{ getSaleTypeLabel(product) }}
                        </span>
                      </div>
                    </div>
                  </article>
                </div>
              </section>

              <section
                v-if="activeTabId === 'all' || activeTabId === 'live'"
                class="search-page__section"
                aria-labelledby="search-lives-title"
              >
                <div class="search-page__section-header">
                  <h2 id="search-lives-title">라이브</h2>
                  <span>{{ visibleLives.length }}개</span>
                </div>

                <div class="search-page__card-grid">
                  <SearchLiveResultCard
                    v-for="live in visibleLives"
                    :key="live.id"
                    :live="live"
                  />
                </div>
              </section>

              <section
                v-if="activeTabId === 'all' || activeTabId === 'member'"
                class="search-page__section"
                aria-labelledby="search-members-title"
              >
                <div class="search-page__section-header">
                  <h2 id="search-members-title">회원</h2>
                  <span>{{ visibleMembers.length }}명</span>
                </div>

                <div class="search-page__member-list">
                  <SearchMemberResultCard
                    v-for="member in visibleMembers"
                    :key="member.id"
                    :member="member"
                    :is-following="followedMemberIds.has(member.id)"
                    @toggle-follow="toggleFollow"
                  />
                </div>
              </section>
            </template>
          </div>

          <p class="search-page__panel-label">현재 탭: {{ panelTitle }}</p>
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

.search-page {
  width: 100%;
}

.search-page__search {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  min-height: 52px;
  padding: 0 var(--space-2) 0 var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
}

.search-page__search:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
}

.search-page__search-icon {
  width: 20px;
  height: 20px;
  color: var(--color-text-muted);
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-width: 1.8;
}

.search-page__search input {
  min-width: 0;
  height: 50px;
  padding: 0 var(--space-3);
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--color-text-primary);
}

.search-page__search input::placeholder {
  color: var(--color-text-muted);
}

.search-page__search button {
  min-width: 72px;
  height: var(--button-height-small);
  border: 0;
  border-radius: var(--radius-control);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-weight: 700;
}

.search-page__search button:hover {
  background: var(--color-primary-hover);
}

.search-page__search button:focus-visible {
  outline: 3px solid var(--color-primary-soft);
  outline-offset: 2px;
}

.search-page__header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--space-6);
  margin-top: var(--space-10);
}

.search-page__eyebrow {
  color: var(--color-primary);
  font-size: 14px;
  font-weight: 800;
  line-height: 20px;
}

.search-page__title {
  margin-top: var(--space-2);
  color: var(--color-text-primary);
  font-size: 32px;
  font-weight: 800;
  line-height: 42px;
}

.search-page__layout {
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr);
  align-items: start;
  gap: var(--space-8);
  margin-top: var(--space-8);
}

.search-page__filters {
  position: sticky;
  top: var(--space-6);
  padding: var(--space-6);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
}

.search-page__filter-title {
  font-size: 17px;
  font-weight: 800;
  line-height: 24px;
}

.search-page__product-filter {
  margin-top: var(--space-6);
}

.search-page__product-filter fieldset {
  display: grid;
  gap: var(--space-3);
  border: 0;
}

.search-page__product-filter fieldset + fieldset {
  margin-top: var(--space-6);
}

.search-page__product-filter legend {
  margin-bottom: var(--space-2);
  color: var(--color-text-primary);
  font-weight: 800;
}

.search-page__product-filter label {
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: 700;
  line-height: 20px;
}

.search-page__checkbox-option {
  display: flex;
  align-items: center;
  min-height: 24px;
  gap: var(--space-3);
}

.search-page__checkbox-option input {
  width: 16px;
  height: 16px;
  accent-color: var(--color-primary);
}

.search-page__product-filter input[type='number'] {
  width: 100%;
  height: var(--button-height-standard);
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  outline: 0;
  background: var(--color-surface);
  color: var(--color-text-primary);
}

.search-page__product-filter input:focus-visible {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
}

.search-page__field-error {
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-control);
  background: var(--color-error-soft);
  color: var(--color-error);
  font-size: 13px;
  line-height: 20px;
}

.search-page__filter-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-2);
  margin-top: var(--space-5);
}

.search-page__filter-actions button {
  height: var(--button-height-small);
  border-radius: var(--radius-control);
  font-weight: 700;
}

.search-page__filter-actions button:first-child {
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text-primary);
}

.search-page__filter-actions button:last-child {
  border: 1px solid var(--color-primary);
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

.search-page__filter-actions button:focus-visible {
  outline: 3px solid var(--color-primary-soft);
  outline-offset: 2px;
}

.search-page__results {
  min-width: 0;
}

.search-page__tabpanel {
  padding-top: var(--space-6);
}

.search-page__section + .search-page__section {
  margin-top: var(--space-10);
}

.search-page__section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  margin-bottom: var(--space-4);
}

.search-page__section-header h2 {
  font-size: 22px;
  font-weight: 800;
  line-height: 30px;
}

.search-page__section-header span,
.search-page__panel-label {
  color: var(--color-text-secondary);
  font-size: 13px;
  line-height: 20px;
}

.search-page__product-grid,
.search-page__card-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-5);
}

.search-page__member-list {
  display: grid;
  gap: var(--space-4);
}

.search-page__panel-label {
  margin-top: var(--space-6);
}

.search-product-card {
  position: relative;
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
  transition:
    border-color 160ms ease,
    transform 160ms ease;
}

.search-product-card:hover {
  border-color: var(--color-border-strong);
  transform: translateY(-2px);
}

.search-product-card__media {
  position: relative;
  display: block;
  overflow: hidden;
  aspect-ratio: 4 / 5;
  background: var(--color-surface-secondary);
}

.search-product-card__media:focus-visible,
.search-product-card__name:focus-visible,
.search-product-card__like:focus-visible {
  outline: 3px solid var(--color-primary-soft);
  outline-offset: 2px;
}

.search-product-card__image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.search-product-card__grade {
  position: absolute;
  top: var(--space-3);
  left: var(--space-3);
  padding: 2px var(--space-2);
  border-radius: var(--radius-badge);
  background: rgba(255, 255, 255, 0.92);
  color: var(--color-text-primary);
  font-size: 12px;
  font-weight: 800;
  line-height: 18px;
}

.search-product-card__like {
  position: absolute;
  top: var(--space-3);
  right: var(--space-3);
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  border: 1px solid rgba(225, 224, 218, 0.8);
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.94);
  color: var(--color-text-secondary);
}

.search-product-card__like svg {
  width: 20px;
  height: 20px;
  fill: transparent;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.8;
}

.search-product-card__like:hover,
.search-product-card__like--active {
  color: var(--color-auction);
}

.search-product-card__like--active svg {
  fill: currentColor;
}

.search-product-card__body {
  display: grid;
  gap: var(--space-1);
  padding: var(--space-4);
}

.search-product-card__brand,
.search-product-card__seller {
  overflow: hidden;
  color: var(--color-text-muted);
  font-size: 13px;
  line-height: 20px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.search-product-card__brand {
  color: var(--color-primary);
  font-weight: 700;
}

.search-product-card__name {
  overflow: hidden;
  color: var(--color-text-primary);
  font-size: 17px;
  font-weight: 700;
  line-height: 24px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.search-product-card__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  margin-top: var(--space-2);
}

.search-product-card__meta strong {
  font-size: 16px;
  font-variant-numeric: tabular-nums;
  line-height: 24px;
}

.search-product-card__badge {
  flex: 0 0 auto;
  padding: 3px var(--space-2);
  border-radius: var(--radius-badge);
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-size: 12px;
  font-weight: 700;
  line-height: 16px;
}

.search-product-card__badge--auction {
  background: var(--color-auction-soft);
  color: var(--color-auction);
}

@media (max-width: 1180px) {
  .search-page__product-grid,
  .search-page__card-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 1024px) {
  .search-page__layout {
    grid-template-columns: 1fr;
  }

  .search-page__filters {
    position: static;
  }
}

@media (max-width: 720px) {
  .search-page__title {
    font-size: 26px;
    line-height: 36px;
  }

  .search-page__product-grid,
  .search-page__card-grid {
    grid-template-columns: 1fr;
  }

  .search-page__search {
    grid-template-columns: auto minmax(0, 1fr);
    row-gap: var(--space-2);
    padding: var(--space-3);
  }

  .search-page__search button {
    grid-column: 1 / -1;
    width: 100%;
  }
}
</style>
