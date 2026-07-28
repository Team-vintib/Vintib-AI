<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import SearchLiveResultCard from '@/domains/search/components/SearchLiveResultCard.vue'
import SearchMemberResultCard from '@/domains/search/components/SearchMemberResultCard.vue'
import SearchResultTabs from '@/domains/search/components/SearchResultTabs.vue'
import { SEARCH_MOCK_RESULTS } from '@/domains/search/constants/searchMockData'
import type {
  SearchProductResult,
  SearchResultTabId,
} from '@/domains/search/types/search.types'
import { ROUTE_NAMES } from '@/shared/constants/routes'
import DefaultLayout from '@/shared/layouts/DefaultLayout.vue'

const route = useRoute()
const router = useRouter()

const validTabIds: SearchResultTabId[] = ['all', 'product', 'live', 'member']

const getQueryString = (value: unknown) => (typeof value === 'string' ? value : '')

const queryKeyword = computed(() => getQueryString(route.query.keyword).trim())
const activeTabId = computed<SearchResultTabId>(() => {
  const queryType = getQueryString(route.query.type)

  return validTabIds.includes(queryType as SearchResultTabId)
    ? (queryType as SearchResultTabId)
    : 'all'
})

const searchKeyword = ref(queryKeyword.value)
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

const totalResultCount = computed(
  () =>
    SEARCH_MOCK_RESULTS.products.length +
    SEARCH_MOCK_RESULTS.lives.length +
    SEARCH_MOCK_RESULTS.members.length,
)

const resultTabs = computed(() => [
  { id: 'all' as const, label: '전체', count: totalResultCount.value },
  { id: 'product' as const, label: '상품', count: SEARCH_MOCK_RESULTS.products.length },
  { id: 'live' as const, label: '라이브', count: SEARCH_MOCK_RESULTS.lives.length },
  { id: 'member' as const, label: '회원', count: SEARCH_MOCK_RESULTS.members.length },
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

const submitSearch = async () => {
  const keyword = searchKeyword.value.trim()

  await router.push({
    name: ROUTE_NAMES.SEARCH,
    query: keyword ? { keyword, type: 'all' } : {},
  })
}

const selectTab = async (tabId: SearchResultTabId) => {
  const nextQuery = {
    ...route.query,
    type: tabId === 'all' ? undefined : tabId,
  }

  await router.push({
    name: ROUTE_NAMES.SEARCH,
    query: nextQuery,
  })

  liveMessage.value = `${resultTabs.value.find((tab) => tab.id === tabId)?.label ?? '전체'} 결과 탭을 선택했습니다.`
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
          <p class="search-page__filter-copy">카테고리, 브랜드, 가격대 필터는 다음 작업에서 상태 화면과 함께 연결합니다.</p>
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
            <div v-if="!hasKeyword" class="search-page__intro">
              <strong>검색어를 입력해 주세요.</strong>
              <p>상품, 라이브, 회원 결과가 유형별 탭으로 정리됩니다.</p>
            </div>

            <template v-else>
              <section
                v-if="activeTabId === 'all' || activeTabId === 'product'"
                class="search-page__section"
                aria-labelledby="search-products-title"
              >
                <div class="search-page__section-header">
                  <h2 id="search-products-title">상품</h2>
                  <span>{{ SEARCH_MOCK_RESULTS.products.length }}개</span>
                </div>

                <div class="search-page__product-grid">
                  <article
                    v-for="product in SEARCH_MOCK_RESULTS.products"
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
                      :class="{ 'search-product-card__like--active': likedProductIds.has(product.id) }"
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
                  <span>{{ SEARCH_MOCK_RESULTS.lives.length }}개</span>
                </div>

                <div class="search-page__card-grid">
                  <SearchLiveResultCard
                    v-for="live in SEARCH_MOCK_RESULTS.lives"
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
                  <span>{{ SEARCH_MOCK_RESULTS.members.length }}명</span>
                </div>

                <div class="search-page__member-list">
                  <SearchMemberResultCard
                    v-for="member in SEARCH_MOCK_RESULTS.members"
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

.search-page__filter-copy {
  margin-top: var(--space-3);
  color: var(--color-text-secondary);
  font-size: 13px;
  line-height: 20px;
}

.search-page__results {
  min-width: 0;
}

.search-page__tabpanel {
  padding-top: var(--space-6);
}

.search-page__intro {
  display: grid;
  gap: var(--space-2);
  min-height: 280px;
  place-content: center;
  padding: var(--space-8);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
  text-align: center;
}

.search-page__intro strong {
  font-size: 20px;
  line-height: 28px;
}

.search-page__intro p {
  color: var(--color-text-secondary);
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
