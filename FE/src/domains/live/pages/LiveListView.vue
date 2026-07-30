<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { getLiveListViewData, isLiveListApiEnabled } from '@/domains/live/api/liveListApi'
import LiveListCard from '@/domains/live/components/LiveListCard.vue'
import LiveListFilter from '@/domains/live/components/LiveListFilter.vue'
import LiveListState from '@/domains/live/components/LiveListState.vue'
import {
  LIVE_CATEGORY_FILTER_OPTIONS,
  LIVE_SORT_OPTIONS,
  LIVE_STATUS_FILTER_OPTIONS,
} from '@/domains/live/constants/liveListFilterOptions'
import { normalizeApiError } from '@/shared/api/http'
import AppSearchBar from '@/shared/components/AppSearchBar.vue'
import { ROUTE_NAMES } from '@/shared/constants/routes'
import DefaultLayout from '@/shared/layouts/DefaultLayout.vue'

import type {
  LiveCategoryFilter,
  LiveListItem,
  LiveListLoadState,
  LiveListMockScenario,
  LiveSortOption,
  LiveStatusFilter,
} from '@/domains/live/types/liveList.types'

const LIVE_LIST_MOCK_SCENARIOS: LiveListMockScenario[] = ['default', 'loading', 'empty', 'error']

const route = useRoute()
const router = useRouter()
const liveList = ref<LiveListItem[]>([])
const loadState = ref<LiveListLoadState>('loading')
const errorMessage = ref('')
const searchKeyword = ref('')
const selectedCategory = ref<LiveCategoryFilter>('ALL')
const selectedStatus = ref<LiveStatusFilter>('ALL')
const selectedSort = ref<LiveSortOption>('LATEST')
const apiEnabled = isLiveListApiEnabled()
let loadRequestId = 0

const canResetFilters = computed(
  () =>
    selectedCategory.value !== 'ALL' ||
    selectedStatus.value !== 'ALL' ||
    selectedSort.value !== 'LATEST',
)

const getMockScenario = (): LiveListMockScenario => {
  const queryValue = Array.isArray(route.query.mock) ? route.query.mock[0] : route.query.mock

  return LIVE_LIST_MOCK_SCENARIOS.includes(queryValue as LiveListMockScenario)
    ? (queryValue as LiveListMockScenario)
    : 'default'
}

const getOptionLabel = <T extends string>(options: { id: T; label: string }[], selectedId: T) =>
  options.find((option) => option.id === selectedId)?.label ?? selectedId

const compareById = (first: LiveListItem, second: LiveListItem) => second.id - first.id

const publicLiveList = computed(() => liveList.value.filter((live) => live.status !== 'ENDED'))

const sortedLiveList = computed(() => {
  const filteredLiveList = publicLiveList.value.filter((live) => {
    const matchesCategory =
      selectedCategory.value === 'ALL' || live.category === selectedCategory.value
    const matchesStatus = selectedStatus.value === 'ALL' || live.status === selectedStatus.value

    return matchesCategory && matchesStatus
  })

  return [...filteredLiveList].sort((first, second) => {
    if (selectedSort.value === 'VIEWERS_DESC') {
      return second.viewerCount - first.viewerCount || compareById(first, second)
    }

    if (selectedSort.value === 'TITLE_ASC') {
      return first.title.localeCompare(second.title, 'ko-KR') || compareById(first, second)
    }

    return (
      new Date(second.broadcastAt).getTime() - new Date(first.broadcastAt).getTime() ||
      compareById(first, second)
    )
  })
})

const isLoading = computed(() => loadState.value === 'loading')
const hasLoadError = computed(() => loadState.value === 'error')
const isEmpty = computed(() => loadState.value === 'success' && publicLiveList.value.length === 0)
const isFilterEmpty = computed(
  () =>
    loadState.value === 'success' &&
    publicLiveList.value.length > 0 &&
    sortedLiveList.value.length === 0,
)

const resultStatusMessage = computed(() => {
  if (isLoading.value) {
    return '라이브 목록을 불러오는 중입니다.'
  }

  if (hasLoadError.value) {
    return errorMessage.value
  }

  const condition = [
    getOptionLabel(LIVE_CATEGORY_FILTER_OPTIONS, selectedCategory.value),
    getOptionLabel(LIVE_STATUS_FILTER_OPTIONS, selectedStatus.value),
    getOptionLabel(LIVE_SORT_OPTIONS, selectedSort.value),
  ].join(', ')

  return `${condition} 조건으로 라이브 ${sortedLiveList.value.length}개를 표시합니다.`
})

const loadLiveList = async () => {
  const requestId = ++loadRequestId
  const scenario = getMockScenario()

  liveList.value = []
  loadState.value = 'loading'
  errorMessage.value = ''

  if (!apiEnabled && scenario === 'loading') {
    return
  }

  try {
    const response = await getLiveListViewData(
      {
        status: selectedStatus.value === 'ALL' ? undefined : selectedStatus.value,
        sort: selectedSort.value,
        page: 0,
        size: 12,
      },
      scenario,
    )

    if (requestId !== loadRequestId) return

    liveList.value = response.items
    loadState.value = 'success'
  } catch (error) {
    if (requestId !== loadRequestId) return

    const apiError = normalizeApiError(error)

    errorMessage.value =
      apiError.code === 'UNKNOWN_ERROR'
        ? '라이브 목록을 불러오지 못했습니다. 네트워크 상태를 확인해 주세요.'
        : apiError.message
    loadState.value = 'error'
  }
}

const resetFilters = () => {
  selectedCategory.value = 'ALL'
  selectedStatus.value = 'ALL'
  selectedSort.value = 'LATEST'
}

const handleSearch = async (keyword: string) => {
  await router.push({
    name: ROUTE_NAMES.SEARCH,
    query: keyword ? { keyword, type: 'live' } : { type: 'live' },
  })
}

watch(
  () => route.query.mock,
  () => {
    void loadLiveList()
  },
  { immediate: true },
)

watch([selectedStatus, selectedSort], () => {
  if (apiEnabled) {
    void loadLiveList()
  }
})

onBeforeUnmount(() => {
  loadRequestId += 1
})
</script>

<template>
  <DefaultLayout content-max-width="1200px">
    <section class="live-list-page" aria-labelledby="live-list-title">
      <header class="live-list-page__header">
        <h1 id="live-list-title">라이브</h1>
        <p>지금 진행 중인 방송과 곧 시작할 라이브를 만나보세요.</p>
      </header>

      <AppSearchBar
        v-model="searchKeyword"
        search-label="라이브 검색"
        placeholder="방송 제목, 판매자 또는 브랜드를 검색해 보세요"
        @submit="handleSearch"
      />

      <div class="live-list-page__content">
        <LiveListFilter
          v-model:selected-category="selectedCategory"
          :can-reset="canResetFilters"
          :disabled="isLoading"
          @reset="resetFilters"
        />

        <div class="live-list-page__results">
          <div class="live-list-page__result-header">
            <div class="live-list-page__tabs" role="tablist" aria-label="방송 상태">
              <button
                v-for="option in LIVE_STATUS_FILTER_OPTIONS"
                :key="option.id"
                type="button"
                role="tab"
                :class="{ 'live-list-page__tab--active': selectedStatus === option.id }"
                :aria-selected="selectedStatus === option.id"
                :disabled="isLoading"
                @click="selectedStatus = option.id"
              >
                {{ option.label }}
              </button>
            </div>

            <div class="live-list-page__toolbar">
              <span aria-live="polite">
                {{ isLoading ? '불러오는 중' : `총 ${sortedLiveList.length}개` }}
              </span>
              <label class="sr-only" for="live-list-sort">라이브 정렬</label>
              <select id="live-list-sort" v-model="selectedSort" :disabled="isLoading">
                <option v-for="option in LIVE_SORT_OPTIONS" :key="option.id" :value="option.id">
                  {{ option.label }}
                </option>
              </select>
            </div>
          </div>

          <p class="sr-only" aria-live="polite">{{ resultStatusMessage }}</p>

          <LiveListState v-if="isLoading" variant="loading" />

          <LiveListState
            v-else-if="hasLoadError"
            variant="error"
            title="라이브 목록을 불러오지 못했습니다"
            :description="errorMessage"
            @action="loadLiveList"
          />

          <LiveListState
            v-else-if="isEmpty"
            variant="empty"
            title="아직 공개된 라이브가 없습니다"
            description="새로운 라이브가 준비되면 이곳에서 바로 확인할 수 있습니다."
          />

          <LiveListState
            v-else-if="isFilterEmpty"
            variant="filter-empty"
            title="조건에 맞는 라이브가 없습니다"
            description="다른 카테고리나 방송 상태를 선택하거나 필터를 초기화해 보세요."
            @action="resetFilters"
          />

          <div v-else class="live-list-page__grid" aria-label="필터링된 라이브 방송 목록">
            <LiveListCard v-for="live in sortedLiveList" :key="live.id" :live="live" />
          </div>
        </div>
      </div>
    </section>
  </DefaultLayout>
</template>

<style scoped lang="scss">
.live-list-page {
  display: grid;
  gap: var(--space-8);
}

.live-list-page__header {
  display: grid;
  gap: var(--space-2);
}

.live-list-page__header h1 {
  color: var(--color-text-primary);
  font-size: clamp(30px, 4vw, 40px);
  font-weight: 800;
  line-height: 1.2;
}

.live-list-page__header p {
  color: var(--color-text-secondary);
  font-size: 16px;
  line-height: 26px;
}

.live-list-page__content {
  display: grid;
  grid-template-columns: var(--filter-panel-width) minmax(0, 1fr);
  align-items: start;
  gap: var(--space-8);
}

.live-list-page__results {
  display: grid;
  min-width: 0;
  gap: var(--space-6);
}

.live-list-page__result-header {
  display: flex;
  align-items: end;
  justify-content: space-between;
  min-height: 48px;
  gap: var(--space-5);
  border-bottom: 1px solid var(--color-border);
}

.live-list-page__tabs {
  display: flex;
  align-items: end;
  gap: var(--space-5);
}

.live-list-page__tabs button {
  position: relative;
  min-height: 48px;
  padding: 0 2px;
  border: 0;
  background: transparent;
  color: var(--color-text-secondary);
  font-size: 15px;
  font-weight: var(--font-weight-semibold);
}

.live-list-page__tabs button::after {
  position: absolute;
  right: 0;
  bottom: -1px;
  left: 0;
  height: 2px;
  background: transparent;
  content: '';
}

.live-list-page__tabs button:hover:not(:disabled),
.live-list-page__tabs button:focus-visible,
.live-list-page__tab--active {
  color: var(--color-primary);
}

.live-list-page__tabs button:focus-visible,
.live-list-page__toolbar select:focus-visible {
  outline: 3px solid var(--color-primary-soft);
  outline-offset: 2px;
}

.live-list-page__tabs button:disabled,
.live-list-page__toolbar select:disabled {
  cursor: wait;
  opacity: 0.6;
}

.live-list-page__tabs .live-list-page__tab--active::after {
  background: var(--color-primary);
}

.live-list-page__toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding-bottom: var(--space-2);
}

.live-list-page__toolbar span {
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: var(--font-weight-semibold);
}

.live-list-page__toolbar select {
  min-height: var(--button-height-small);
  padding: 0 34px 0 var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-size: 13px;
}

.live-list-page__grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-6);
}

@media (max-width: 1024px) {
  .live-list-page__content {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 840px) {
  .live-list-page__grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .live-list-page__result-header {
    align-items: stretch;
    flex-direction: column;
    gap: 0;
  }

  .live-list-page__tabs {
    justify-content: space-between;
  }

  .live-list-page__toolbar {
    justify-content: space-between;
    padding: var(--space-4) 0 0;
  }

  .live-list-page__grid {
    grid-template-columns: minmax(0, 1fr);
    gap: var(--space-5);
  }
}
</style>
