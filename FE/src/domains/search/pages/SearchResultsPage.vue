<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '@/domains/auth/stores/authStore'
import SearchLiveResultCard from '@/domains/search/components/SearchLiveResultCard.vue'
import SearchMemberResultCard from '@/domains/search/components/SearchMemberResultCard.vue'
import SearchResultTabs from '@/domains/search/components/SearchResultTabs.vue'
import SearchStatePanel from '@/domains/search/components/SearchStatePanel.vue'
import {
  SEARCH_CATEGORY_FILTER_OPTIONS,
  SEARCH_CONDITION_FILTER_OPTIONS,
  SEARCH_SALE_TYPE_FILTER_OPTIONS,
} from '@/domains/search/constants/searchFilterOptions'
import { SEARCH_MOCK_RESULTS } from '@/domains/search/constants/searchMockData'
import type {
  SearchProductResult,
  SearchResultTabId,
  SearchSortOptionId,
  SearchStateContent,
  SearchStateKind,
} from '@/domains/search/types/search.types'
import { ROUTE_NAMES } from '@/shared/constants/routes'
import DefaultLayout from '@/shared/layouts/DefaultLayout.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const validTabIds: SearchResultTabId[] = ['all', 'product', 'live', 'member']
const validSortOptionIds: SearchSortOptionId[] = ['LATEST', 'PRICE_ASC', 'PRICE_DESC']
const validMockStatuses = ['loading', 'error', 'empty'] as const
const SEARCH_RESULT_PREVIEW_LIMIT = 3
const SEARCH_PRODUCT_PAGE_SIZE = 3
const SEARCH_LIVE_PAGE_SIZE = 2
const SEARCH_MEMBER_PAGE_SIZE = 2
const SEARCH_SORT_OPTIONS: { id: SearchSortOptionId; label: string }[] = [
  { id: 'LATEST', label: '최신순' },
  { id: 'PRICE_ASC', label: '가격 낮은순' },
  { id: 'PRICE_DESC', label: '가격 높은순' },
]

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
const queryPage = computed(() => {
  const page = getQueryNumber(route.query.page)

  if (page === undefined || page < 1) {
    return 1
  }

  return Math.floor(page)
})
const querySortOption = computed<SearchSortOptionId>(() => {
  const querySort = getQueryString(route.query.sort)

  return validSortOptionIds.includes(querySort as SearchSortOptionId)
    ? (querySort as SearchSortOptionId)
    : 'LATEST'
})
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
type SearchFilterChipKind = 'category' | 'condition' | 'saleType' | 'price'

interface SearchFilterChip {
  id: string
  label: string
  kind: SearchFilterChipKind
  value?: string
}

const getFilterOptionLabel = (
  options: { id: string; label: string }[],
  optionId: string,
  fallback = optionId,
) => options.find((option) => option.id === optionId)?.label ?? fallback

const selectedFilterChips = computed<SearchFilterChip[]>(() => {
  const categoryChips = queryCategoryIds.value.map((categoryId) => ({
    id: `category-${categoryId}`,
    kind: 'category' as const,
    value: categoryId,
    label: getFilterOptionLabel(SEARCH_CATEGORY_FILTER_OPTIONS, categoryId),
  }))
  const conditionChips = queryConditionIds.value.map((conditionId) => ({
    id: `condition-${conditionId}`,
    kind: 'condition' as const,
    value: conditionId,
    label: getFilterOptionLabel(SEARCH_CONDITION_FILTER_OPTIONS, conditionId),
  }))
  const saleTypeChips = querySaleTypeIds.value.map((saleTypeId) => ({
    id: `sale-type-${saleTypeId}`,
    kind: 'saleType' as const,
    value: saleTypeId,
    label: getFilterOptionLabel(SEARCH_SALE_TYPE_FILTER_OPTIONS, saleTypeId),
  }))

  if (!hasPriceFilter.value) {
    return [...categoryChips, ...conditionChips, ...saleTypeChips]
  }

  const minPrice = queryMinPrice.value?.toLocaleString('ko-KR') ?? '0'
  const maxPrice = queryMaxPrice.value?.toLocaleString('ko-KR') ?? '제한 없음'

  return [
    ...categoryChips,
    ...conditionChips,
    ...saleTypeChips,
    {
      id: 'price-range',
      kind: 'price',
      label: `₩ ${minPrice} - ₩ ${maxPrice}`,
    },
  ]
})
const normalizedKeyword = computed(() => queryKeyword.value.toLocaleLowerCase('ko-KR'))

const matchesKeyword = (values: string[]) => {
  if (!normalizedKeyword.value) {
    return true
  }

  return values.some((value) => value.toLocaleLowerCase('ko-KR').includes(normalizedKeyword.value))
}

const filteredProducts = computed(() => {
  if (mockStatus.value === 'empty') {
    return []
  }

  if (isPriceRangeInvalid.value) {
    return []
  }

  return SEARCH_MOCK_RESULTS.products.filter((product) => {
    if (
      !matchesKeyword([
        product.brand,
        product.name,
        product.sellerName,
        product.categoryName,
        product.conditionGrade,
        product.saleType,
      ])
    ) {
      return false
    }

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

const sortedProducts = computed(() => {
  const products = [...filteredProducts.value]

  if (querySortOption.value === 'PRICE_ASC') {
    return products.sort((firstProduct, secondProduct) => firstProduct.price - secondProduct.price)
  }

  if (querySortOption.value === 'PRICE_DESC') {
    return products.sort((firstProduct, secondProduct) => secondProduct.price - firstProduct.price)
  }

  return products.sort(
    (firstProduct, secondProduct) =>
      new Date(secondProduct.createdAt).getTime() - new Date(firstProduct.createdAt).getTime(),
  )
})

const visibleLives = computed(() => {
  if (mockStatus.value === 'empty') {
    return []
  }

  return SEARCH_MOCK_RESULTS.lives.filter((live) =>
    matchesKeyword([live.title, live.hostName, live.status]),
  )
})
const visibleMembers = computed(() => {
  if (mockStatus.value === 'empty') {
    return []
  }

  return SEARCH_MOCK_RESULTS.members.filter((member) =>
    matchesKeyword([member.nickname, member.description]),
  )
})
const totalResultCount = computed(
  () => filteredProducts.value.length + visibleLives.value.length + visibleMembers.value.length,
)
const previewProducts = computed(() => sortedProducts.value.slice(0, SEARCH_RESULT_PREVIEW_LIMIT))
const previewLives = computed(() => visibleLives.value.slice(0, SEARCH_RESULT_PREVIEW_LIMIT))
const previewMembers = computed(() => visibleMembers.value.slice(0, SEARCH_RESULT_PREVIEW_LIMIT))

const getPageCount = (totalCount: number, pageSize: number) =>
  Math.max(1, Math.ceil(totalCount / pageSize))

const activePageSize = computed(() => {
  if (activeTabId.value === 'live') {
    return SEARCH_LIVE_PAGE_SIZE
  }

  if (activeTabId.value === 'member') {
    return SEARCH_MEMBER_PAGE_SIZE
  }

  return SEARCH_PRODUCT_PAGE_SIZE
})

const activePaginationTotalCount = computed(() => {
  if (activeTabId.value === 'live') {
    return visibleLives.value.length
  }

  if (activeTabId.value === 'member') {
    return visibleMembers.value.length
  }

  if (activeTabId.value === 'product') {
    return sortedProducts.value.length
  }

  return 0
})

const activePageCount = computed(() =>
  getPageCount(activePaginationTotalCount.value, activePageSize.value),
)
const currentPage = computed(() => Math.min(queryPage.value, activePageCount.value))
const hasPagination = computed(
  () => activeTabId.value !== 'all' && activePaginationTotalCount.value > activePageSize.value,
)
const visiblePageNumbers = computed(() =>
  Array.from({ length: activePageCount.value }, (_, index) => index + 1),
)
const getPageSlice = <T,>(items: T[], pageSize: number) => {
  const startIndex = (currentPage.value - 1) * pageSize

  return items.slice(startIndex, startIndex + pageSize)
}
const pagedProducts = computed(() => getPageSlice(sortedProducts.value, SEARCH_PRODUCT_PAGE_SIZE))
const pagedLives = computed(() => getPageSlice(visibleLives.value, SEARCH_LIVE_PAGE_SIZE))
const pagedMembers = computed(() => getPageSlice(visibleMembers.value, SEARCH_MEMBER_PAGE_SIZE))

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

  await pushSearchQuery(keyword ? { keyword, page: undefined } : {})
}

const selectTab = async (tabId: SearchResultTabId) => {
  await pushSearchQuery({
    ...route.query,
    type: tabId === 'all' ? undefined : tabId,
    page: undefined,
  } as Record<string, string | undefined>)

  liveMessage.value = `${resultTabs.value.find((tab) => tab.id === tabId)?.label ?? '전체'} 결과 탭을 선택했습니다.`
}

const handleSortChange = async (event: Event) => {
  const sortOption = (event.target as HTMLSelectElement).value as SearchSortOptionId

  await pushSearchQuery({
    ...route.query,
    sort: sortOption === 'LATEST' ? undefined : sortOption,
    page: undefined,
  } as Record<string, string | undefined>)

  liveMessage.value = `${getFilterOptionLabel(SEARCH_SORT_OPTIONS, sortOption, '최신순')}으로 정렬했습니다.`
}

const viewAllResults = async (tabId: Exclude<SearchResultTabId, 'all'>) => {
  await pushSearchQuery({
    ...route.query,
    type: tabId,
    page: undefined,
  } as Record<string, string | undefined>)

  liveMessage.value = `${resultTabs.value.find((tab) => tab.id === tabId)?.label ?? ''} 전체 결과로 이동했습니다.`
}

const moveToPage = async (page: number) => {
  if (page < 1 || page > activePageCount.value || page === currentPage.value) {
    return
  }

  await pushSearchQuery({
    ...route.query,
    page: page === 1 ? undefined : page.toString(),
  } as Record<string, string | undefined>)

  liveMessage.value = `${page}페이지 결과를 표시합니다.`
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
    page: undefined,
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
    page: undefined,
  } as Record<string, string | undefined>)

  liveMessage.value = '필터를 초기화했습니다.'
}

const removeFilterChip = async (chip: SearchFilterChip) => {
  if (chip.kind === 'category') {
    selectedCategoryIds.value = selectedCategoryIds.value.filter((id) => id !== chip.value)
  }

  if (chip.kind === 'condition') {
    selectedConditionIds.value = selectedConditionIds.value.filter((id) => id !== chip.value)
  }

  if (chip.kind === 'saleType') {
    selectedSaleTypeIds.value = selectedSaleTypeIds.value.filter((id) => id !== chip.value)
  }

  if (chip.kind === 'price') {
    minPriceInput.value = ''
    maxPriceInput.value = ''
  }

  await pushSearchQuery({
    ...route.query,
    categories: selectedCategoryIds.value.length ? selectedCategoryIds.value.join(',') : undefined,
    conditions: selectedConditionIds.value.length
      ? selectedConditionIds.value.join(',')
      : undefined,
    saleTypes: selectedSaleTypeIds.value.length ? selectedSaleTypeIds.value.join(',') : undefined,
    minPrice: chip.kind === 'price' ? undefined : route.query.minPrice?.toString(),
    maxPrice: chip.kind === 'price' ? undefined : route.query.maxPrice?.toString(),
    status: undefined,
    page: undefined,
  } as Record<string, string | undefined>)

  liveMessage.value = `${chip.label} 필터를 해제했습니다.`
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

const requireAuthenticatedAction = async () => {
  authStore.hydrateSession()

  if (authStore.isAuthenticated) {
    return true
  }

  await router.push({
    name: ROUTE_NAMES.AUTH_LOGIN,
    query: { redirect: route.fullPath },
  })

  return false
}

const toggleLike = async (productId: number) => {
  if (!(await requireAuthenticatedAction())) {
    return
  }

  const nextLikedProductIds = new Set(likedProductIds.value)

  if (nextLikedProductIds.has(productId)) {
    nextLikedProductIds.delete(productId)
  } else {
    nextLikedProductIds.add(productId)
  }

  likedProductIds.value = nextLikedProductIds
}

const toggleFollow = async (memberId: number) => {
  if (!(await requireAuthenticatedAction())) {
    return
  }

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
          <div class="search-page__filter-header">
            <h2 class="search-page__filter-title">필터</h2>
            <button type="button" @click="resetProductFilters">초기화</button>
          </div>

          <form class="search-page__product-filter" @submit.prevent="applyProductFilters">
            <details class="search-page__filter-group" open>
              <summary>카테고리</summary>

              <div class="search-page__filter-group-body">
                <label
                  v-for="option in SEARCH_CATEGORY_FILTER_OPTIONS"
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
              </div>
            </details>

            <details class="search-page__filter-group" open>
              <summary>상품 상태</summary>

              <div class="search-page__filter-group-body">
                <label
                  v-for="option in SEARCH_CONDITION_FILTER_OPTIONS"
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
              </div>
            </details>

            <details class="search-page__filter-group" open>
              <summary>가격 범위</summary>

              <div class="search-page__filter-group-body">
                <label for="search-min-price">최소 가격</label>
                <input
                  id="search-min-price"
                  v-model="minPriceInput"
                  inputmode="numeric"
                  type="number"
                  min="0"
                  placeholder="₩ 0"
                />

                <label for="search-max-price">최대 가격</label>
                <input
                  id="search-max-price"
                  v-model="maxPriceInput"
                  inputmode="numeric"
                  type="number"
                  min="0"
                  placeholder="₩ 300000"
                />

                <p v-if="isPriceRangeInvalid" class="search-page__field-error" role="alert">
                  최소 가격은 최대 가격보다 클 수 없습니다.
                </p>
              </div>
            </details>

            <details class="search-page__filter-group" open>
              <summary>판매 유형</summary>

              <div class="search-page__filter-group-body">
                <label
                  v-for="option in SEARCH_SALE_TYPE_FILTER_OPTIONS"
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
              </div>
            </details>

            <div class="search-page__filter-actions">
              <button type="submit">적용</button>
            </div>
          </form>
        </aside>

        <div class="search-page__results">
          <div class="search-page__result-header">
            <SearchResultTabs
              :tabs="resultTabs"
              :active-tab-id="activeTabId"
              @select="selectTab"
            />

            <div
              v-if="activeTabId === 'all' || activeTabId === 'product'"
              class="search-page__sort-toolbar"
            >
              <span>{{ filteredProducts.length }}개</span>
              <label class="sr-only" for="search-product-sort">검색 상품 정렬</label>
              <select
                id="search-product-sort"
                :value="querySortOption"
                @change="handleSortChange"
              >
                <option
                  v-for="sortOption in SEARCH_SORT_OPTIONS"
                  :key="sortOption.id"
                  :value="sortOption.id"
                >
                  {{ sortOption.label }}
                </option>
              </select>
            </div>
          </div>

          <p class="sr-only" aria-live="polite">{{ liveMessage }}</p>

          <div v-if="selectedFilterChips.length" class="search-page__selected-filters">
            <span>선택된 필터</span>
            <button
              v-for="chip in selectedFilterChips"
              :key="chip.id"
              type="button"
              @click="removeFilterChip(chip)"
            >
              {{ chip.label }} <span aria-hidden="true">×</span>
            </button>
            <button type="button" class="search-page__clear-filters" @click="resetProductFilters">
              전체 해제
            </button>
          </div>

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
                  <div class="search-page__section-summary">
                    <span>{{ filteredProducts.length }}개</span>
                    <button
                      v-if="activeTabId === 'all' && filteredProducts.length > SEARCH_RESULT_PREVIEW_LIMIT"
                      type="button"
                      @click="viewAllResults('product')"
                    >
                      전체보기
                    </button>
                  </div>
                </div>

                <div class="search-page__product-grid">
                  <article
                    v-for="product in activeTabId === 'all' ? previewProducts : pagedProducts"
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
                  <div class="search-page__section-summary">
                    <span>{{ visibleLives.length }}개</span>
                    <button
                      v-if="activeTabId === 'all' && visibleLives.length > SEARCH_RESULT_PREVIEW_LIMIT"
                      type="button"
                      @click="viewAllResults('live')"
                    >
                      전체보기
                    </button>
                  </div>
                </div>

                <div class="search-page__card-grid">
                  <SearchLiveResultCard
                    v-for="live in activeTabId === 'all' ? previewLives : pagedLives"
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
                  <div class="search-page__section-summary">
                    <span>{{ visibleMembers.length }}명</span>
                    <button
                      v-if="activeTabId === 'all' && visibleMembers.length > SEARCH_RESULT_PREVIEW_LIMIT"
                      type="button"
                      @click="viewAllResults('member')"
                    >
                      전체보기
                    </button>
                  </div>
                </div>

                <div class="search-page__member-list">
                  <SearchMemberResultCard
                    v-for="member in activeTabId === 'all' ? previewMembers : pagedMembers"
                    :key="member.id"
                    :member="member"
                    :is-following="followedMemberIds.has(member.id)"
                    @toggle-follow="toggleFollow"
                  />
                </div>
              </section>

              <nav
                v-if="hasPagination"
                class="search-page__pagination"
                aria-label="검색 결과 페이지"
              >
                <button
                  type="button"
                  aria-label="이전 페이지"
                  :disabled="currentPage === 1"
                  @click="moveToPage(currentPage - 1)"
                >
                  <svg aria-hidden="true" viewBox="0 0 24 24">
                    <path d="m15 18-6-6 6-6" />
                  </svg>
                </button>
                <button
                  v-for="page in visiblePageNumbers"
                  :key="page"
                  type="button"
                  :class="{ 'search-page__page--active': currentPage === page }"
                  :aria-current="currentPage === page ? 'page' : undefined"
                  @click="moveToPage(page)"
                >
                  {{ page }}
                </button>
                <button
                  type="button"
                  aria-label="다음 페이지"
                  :disabled="currentPage === activePageCount"
                  @click="moveToPage(currentPage + 1)"
                >
                  <svg aria-hidden="true" viewBox="0 0 24 24">
                    <path d="m9 18 6-6-6-6" />
                  </svg>
                </button>
              </nav>
            </template>
          </div>

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
  font-weight: var(--font-weight-bold);
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
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-extrabold);
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
  grid-template-columns: var(--filter-panel-width) minmax(0, 1fr);
  align-items: start;
  gap: var(--space-8);
  margin-top: var(--space-8);
}

.search-page__filters {
  align-self: start;
  width: var(--filter-panel-width);
  padding: var(--space-2) 0;
  border-top: 1px solid var(--color-border);
  border-bottom: 1px solid var(--color-border);
  background: transparent;
}

.search-page__filter-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-3) 0;
}

.search-page__filter-header button {
  border: 0;
  background: transparent;
  color: var(--color-text-muted);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-semibold);
}

.search-page__filter-header button:hover {
  color: var(--color-primary);
}

.search-page__filter-title {
  font-size: var(--font-size-body);
  font-weight: var(--font-weight-extrabold);
  line-height: var(--line-height-body);
}

.search-page__product-filter {
  display: grid;
}

.search-page__filter-group {
  border-top: 1px solid var(--color-border);
}

.search-page__filter-group summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 48px;
  color: var(--color-text-primary);
  cursor: pointer;
  font-size: var(--font-size-body);
  font-weight: var(--font-weight-bold);
  list-style: none;
}

.search-page__filter-group summary::-webkit-details-marker {
  display: none;
}

.search-page__filter-group summary::after {
  color: var(--color-text-muted);
  content: '⌃';
  font-size: var(--font-size-caption);
}

.search-page__filter-group:not([open]) summary::after {
  content: '⌄';
}

.search-page__filter-group-body {
  display: grid;
  gap: var(--space-2);
  padding-bottom: var(--space-4);
}

.search-page__product-filter label {
  color: var(--color-text-secondary);
  font-size: var(--font-size-body);
  font-weight: var(--font-weight-regular);
  line-height: var(--line-height-body);
}

.search-page__checkbox-option {
  display: flex;
  align-items: center;
  min-height: var(--filter-option-min-height);
  gap: var(--space-3);
  cursor: pointer;
}

.search-page__checkbox-option input {
  display: grid;
  place-content: center;
  width: 17px;
  height: 17px;
  margin: 0;
  border: 1px solid var(--color-border-strong);
  border-radius: 4px;
  appearance: none;
  background: var(--color-surface);
}

.search-page__checkbox-option input::before {
  width: 9px;
  height: 9px;
  border-radius: 2px;
  background: var(--color-primary);
  content: '';
  transform: scale(0);
  transition: transform 120ms ease;
}

.search-page__checkbox-option input:checked {
  border-color: var(--color-primary);
}

.search-page__checkbox-option input:checked::before {
  transform: scale(1);
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
  margin-top: var(--space-4);
}

.search-page__filter-actions button {
  height: var(--button-height-small);
  border-radius: var(--radius-control);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-semibold);
}

.search-page__filter-actions button {
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

.search-page__result-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--space-6);
  min-height: 48px;
  border-bottom: 1px solid var(--color-border);
}

.search-page__sort-toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding-bottom: var(--space-2);
  color: var(--color-text-secondary);
  font-size: var(--font-size-caption);
}

.search-page__sort-toolbar select {
  min-width: 136px;
  height: var(--button-height-small);
  padding: 0 var(--space-8) 0 var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  outline: 0;
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-regular);
}

.search-page__sort-toolbar select:focus-visible {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
}

.search-page__selected-filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  margin-top: var(--space-4);
  color: var(--color-text-secondary);
  font-size: var(--font-size-caption);
  line-height: 22px;
}

.search-page__selected-filters > span {
  margin-right: var(--space-1);
  font-weight: var(--font-weight-semibold);
}

.search-page__selected-filters button {
  min-height: 28px;
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: 999px;
  background: var(--color-surface);
  color: var(--color-text-secondary);
  font-size: var(--font-size-caption);
}

.search-page__selected-filters button:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.search-page__selected-filters .search-page__clear-filters {
  margin-left: auto;
  border-color: transparent;
  background: transparent;
  color: var(--color-text-muted);
  font-weight: var(--font-weight-semibold);
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

.search-page__section-header span {
  color: var(--color-text-secondary);
  font-size: var(--font-size-caption);
  line-height: 20px;
}

.search-page__section-summary {
  display: inline-flex;
  align-items: center;
  gap: var(--space-3);
}

.search-page__section-summary button {
  min-height: 30px;
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-semibold);
}

.search-page__section-summary button:hover,
.search-page__section-summary button:focus-visible {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.search-page__product-grid,
.search-page__card-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-6);
}

.search-page__member-list {
  display: grid;
  gap: var(--space-4);
}

.search-page__pagination {
  display: flex;
  justify-content: center;
  gap: var(--space-2);
  margin-top: var(--space-12);
}

.search-page__pagination button {
  display: grid;
  place-items: center;
  min-width: 40px;
  height: 40px;
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: 50%;
  background: var(--color-surface);
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-semibold);
}

.search-page__pagination button:hover:not(:disabled),
.search-page__pagination button:focus-visible,
.search-page__page--active {
  border-color: var(--color-primary);
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

.search-page__pagination button:focus-visible {
  outline: 3px solid var(--color-primary-soft);
  outline-offset: 2px;
}

.search-page__pagination button:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.search-page__pagination svg {
  width: 18px;
  height: 18px;
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 2;
}

.search-product-card {
  position: relative;
  display: grid;
  gap: var(--space-3);
  transition: transform 180ms ease;
}

.search-product-card:hover {
  transform: translateY(-4px);
}

.search-product-card__media {
  position: relative;
  display: block;
  overflow: hidden;
  aspect-ratio: 4 / 5;
  border-radius: 14px;
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
  transition: transform 220ms ease;
}

.search-product-card:hover .search-product-card__image {
  transform: scale(1.02);
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
  padding: 0 var(--space-1);
}

.search-product-card__brand,
.search-product-card__seller {
  overflow: hidden;
  color: var(--color-text-muted);
  font-size: var(--font-size-caption);
  line-height: 20px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.search-product-card__brand {
  color: var(--color-primary);
  font-weight: var(--font-weight-bold);
}

.search-product-card__name {
  display: -webkit-box;
  overflow: hidden;
  color: var(--color-text-primary);
  font-size: 17px;
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-body);
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.search-product-card__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  margin-top: var(--space-2);
}

.search-product-card__meta strong {
  font-size: 19px;
  font-variant-numeric: tabular-nums;
  font-weight: var(--font-weight-extrabold);
  line-height: var(--line-height-body);
}

.search-product-card__badge {
  flex: 0 0 auto;
  padding: 3px var(--space-2);
  border-radius: var(--radius-badge);
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-size: 12px;
  font-weight: var(--font-weight-bold);
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
    width: 100%;
  }

  .search-page__product-filter {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    column-gap: var(--space-8);
    row-gap: var(--space-5);
  }

  .search-page__filter-actions {
    grid-column: 1 / -1;
  }
}

@media (max-width: 720px) {
  .search-page__title {
    font-size: 26px;
    line-height: 36px;
  }

  .search-page__result-header {
    display: grid;
    gap: var(--space-3);
  }

  .search-page__sort-toolbar {
    justify-content: flex-end;
    padding-bottom: var(--space-3);
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

@media (max-width: 520px) {
  .search-page__product-filter {
    grid-template-columns: 1fr;
  }
}
</style>
