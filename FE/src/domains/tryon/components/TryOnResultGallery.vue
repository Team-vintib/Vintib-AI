<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { ROUTE_NAMES, ROUTE_PATHS } from '@/shared/constants/routes'

import { TRYON_RESULT_CATEGORIES } from '@/domains/tryon/types/tryOnResult.types'
import type { TryOnResult } from '@/domains/tryon/types/tryOnResult.types'

const props = defineProps<{
  results: TryOnResult[]
  loadState: 'loading' | 'loaded' | 'error'
}>()

const emit = defineEmits<{
  delete: [resultId: number]
  retry: []
}>()

const router = useRouter()

const ALL_TAB = '전체'
const activeCategory = ref<string>(ALL_TAB)
const selectedResult = ref<TryOnResult | null>(null)

// 결과가 실제로 존재하는 카테고리 탭만 노출(전체 + 대분류 순서).
const availableTabs = computed(() => {
  const present = new Set(
    props.results.map((result) => result.category).filter((category): category is string => Boolean(category)),
  )
  const categoryTabs = TRYON_RESULT_CATEGORIES.filter((category) => present.has(category))

  return [ALL_TAB, ...categoryTabs]
})

const filteredResults = computed(() => {
  if (activeCategory.value === ALL_TAB) {
    return props.results
  }

  return props.results.filter((result) => result.category === activeCategory.value)
})

const selectTab = (tab: string) => {
  activeCategory.value = tab
}

const formatDate = (createdAt: string) => createdAt.slice(0, 10).replace(/-/g, '.')

const openDetail = (result: TryOnResult) => {
  selectedResult.value = result
}

const closeDetail = () => {
  selectedResult.value = null
}

const goToProduct = (productId: number) => {
  closeDetail()
  void router.push({ name: ROUTE_NAMES.PRODUCT_DETAIL, params: { productId } })
}

const handleDelete = (resultId: number) => {
  closeDetail()
  emit('delete', resultId)
}

const goToProductList = () => {
  void router.push({ path: ROUTE_PATHS.PRODUCT_LIST })
}

const handleKeydown = (event: KeyboardEvent) => {
  if (event.key === 'Escape') {
    closeDetail()
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeydown)
})
</script>

<template>
  <section class="tryon-results" aria-labelledby="tryon-results-title">
    <header class="tryon-results__header">
      <h2 id="tryon-results-title">저장된 시착 결과</h2>
      <p>내가 입어본 AI 시착 결과를 카테고리별로 확인해 보세요.</p>
    </header>

    <div v-if="loadState === 'loading'" class="tryon-results__state" role="status">
      시착 결과를 불러오는 중입니다…
    </div>

    <div v-else-if="loadState === 'error'" class="tryon-results__state" role="alert">
      <p>시착 결과를 불러오지 못했습니다.</p>
      <button type="button" class="tryon-results__retry" @click="emit('retry')">다시 시도</button>
    </div>

    <template v-else>
      <div v-if="results.length" class="tryon-results__tabs" role="tablist" aria-label="시착 결과 카테고리">
        <button
          v-for="tab in availableTabs"
          :key="tab"
          type="button"
          role="tab"
          class="tryon-results__tab"
          :class="{ 'tryon-results__tab--active': activeCategory === tab }"
          :aria-selected="activeCategory === tab"
          @click="selectTab(tab)"
        >
          {{ tab }}
        </button>
      </div>

      <ul v-if="filteredResults.length" class="tryon-results__grid">
        <li v-for="result in filteredResults" :key="result.id">
          <button type="button" class="tryon-results__card" @click="openDetail(result)">
            <span class="tryon-results__thumb">
              <img :src="result.imageUrl" :alt="`시착 결과 ${result.id}`" />
            </span>
            <span class="tryon-results__meta">
              <span v-if="result.category" class="tryon-results__badge">{{ result.category }}</span>
              <span class="tryon-results__date">{{ formatDate(result.createdAt) }}</span>
            </span>
          </button>
        </li>
      </ul>

      <div v-else-if="results.length" class="tryon-results__empty">
        이 카테고리에 저장된 시착 결과가 없습니다.
      </div>

      <div v-else class="tryon-results__empty tryon-results__empty--first">
        <p>아직 저장된 시착 결과가 없습니다.</p>
        <p class="tryon-results__empty-hint">위에서 옷을 골라 입어보거나, 상품 상세·라이브에서 AI 시착을 해보세요.</p>
        <button type="button" class="tryon-results__empty-cta" @click="goToProductList">
          상품 보러가기
        </button>
      </div>
    </template>

    <div v-if="selectedResult" class="tryon-results__overlay" @click.self="closeDetail">
      <div
        class="tryon-results__detail"
        role="dialog"
        aria-label="시착 결과 상세"
        aria-modal="true"
      >
        <button type="button" class="tryon-results__detail-close" aria-label="닫기" @click="closeDetail">
          ×
        </button>
        <div class="tryon-results__detail-image">
          <img :src="selectedResult.imageUrl" :alt="`시착 결과 ${selectedResult.id} 확대`" />
        </div>
        <div class="tryon-results__detail-info">
          <p class="tryon-results__detail-date">
            <span v-if="selectedResult.category" class="tryon-results__badge">{{ selectedResult.category }}</span>
            {{ formatDate(selectedResult.createdAt) }} 시착
          </p>
          <div class="tryon-results__detail-actions">
            <button
              type="button"
              class="tryon-results__detail-product"
              @click="goToProduct(selectedResult.productId)"
            >
              상품 보기
            </button>
            <button
              type="button"
              class="tryon-results__detail-delete"
              @click="handleDelete(selectedResult.id)"
            >
              삭제
            </button>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped lang="scss">
.tryon-results {
  margin-top: var(--space-10);
}

.tryon-results__header h2 {
  color: var(--color-text-primary);
  font-family: var(--font-display);
  font-size: 24px;
  font-weight: 600;
  letter-spacing: -0.03em;
  line-height: 1.1;
}

.tryon-results__header p {
  margin-top: var(--space-2);
  color: var(--color-text-secondary);
  font-size: 14px;
  font-weight: 300;
  line-height: 20px;
}

.tryon-results__state {
  display: grid;
  gap: var(--space-3);
  justify-items: center;
  padding: var(--space-10);
  margin-top: var(--space-6);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  text-align: center;
}

.tryon-results__retry {
  padding: var(--space-2) var(--space-4);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-weight: 600;
}

.tryon-results__tabs {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: var(--space-6);
}

.tryon-results__tab {
  padding: var(--space-2) var(--space-4);
  border: 1px solid var(--color-border-input);
  border-radius: var(--radius-control);
  background: transparent;
  color: var(--color-text-muted);
  font-size: 13px;
  font-weight: 500;
  line-height: 20px;
  transition:
    border-color 160ms ease,
    background-color 160ms ease,
    color 160ms ease;
}

.tryon-results__tab:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.tryon-results__tab--active {
  border-color: var(--color-primary);
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

.tryon-results__grid {
  display: grid;
  gap: var(--space-4);
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  margin-top: var(--space-5);
  list-style: none;
}

.tryon-results__card {
  display: grid;
  width: 100%;
  padding: 0;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
  overflow: hidden;
  transition:
    border-color 220ms ease,
    transform 620ms cubic-bezier(0.22, 1, 0.36, 1);
}

.tryon-results__card:hover {
  border-color: var(--color-border-strong);
  transform: translateY(-3px);
}

.tryon-results__card:hover .tryon-results__thumb img {
  transform: scale(1.045);
}

.tryon-results__card:focus-visible {
  outline: 1px solid var(--color-primary);
  outline-offset: 2px;
}

.tryon-results__thumb {
  display: block;
  overflow: hidden;
  aspect-ratio: 4 / 5;
  background: var(--color-image-frame);
}

.tryon-results__thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  filter: saturate(0.88) contrast(1.04) brightness(0.95);
  transition: transform 620ms cubic-bezier(0.22, 1, 0.36, 1);
}

.tryon-results__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  padding: var(--space-3);
}

.tryon-results__badge {
  padding: 3px var(--space-2);
  border: 1px solid var(--color-border-input);
  border-radius: var(--radius-badge);
  background: transparent;
  color: var(--color-text-muted);
  font-size: 10px;
  font-weight: 400;
  line-height: 16px;
}

.tryon-results__date {
  color: var(--color-text-muted);
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.02em;
  font-variant-numeric: tabular-nums;
}

.tryon-results__empty {
  padding: var(--space-8);
  margin-top: var(--space-5);
  border: 1px dashed var(--color-border-strong);
  border-radius: var(--radius-card);
  color: var(--color-text-secondary);
  text-align: center;
}

.tryon-results__empty--first {
  display: grid;
  gap: var(--space-2);
  justify-items: center;
  padding: var(--space-10);
}

.tryon-results__empty-hint {
  color: var(--color-text-muted);
  font-size: 13px;
}

.tryon-results__empty-cta {
  margin-top: var(--space-3);
  padding: var(--space-3) var(--space-5);
  border: 0;
  border-radius: var(--radius-control);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-weight: 500;
  transition:
    background-color 160ms ease,
    color 160ms ease;
}

.tryon-results__empty-cta:hover {
  background: var(--color-primary-hover);
  color: var(--color-primary-strong);
}

.tryon-results__overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(4, 4, 4, 0.92);
  backdrop-filter: blur(4px);
}

.tryon-results__detail {
  display: grid;
  position: relative;
  width: min(880px, calc(100vw - 48px));
  max-height: calc(100vh - 48px);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-card);
  background: var(--color-surface);
  grid-template-columns: minmax(0, 1fr);
  overflow-x: hidden;
  overflow-y: auto;
}

.tryon-results__detail-close {
  position: absolute;
  top: var(--space-3);
  right: var(--space-3);
  display: grid;
  width: 36px;
  height: 36px;
  border: 1px solid var(--color-border);
  border-radius: 50%;
  background: rgba(10, 10, 10, 0.82);
  color: #fff;
  font-size: 24px;
  line-height: 1;
  place-items: center;
}

.tryon-results__detail-image {
  display: grid;
  min-height: 0;
  background: #050505;
  place-items: center;
}

.tryon-results__detail-image img {
  display: block;
  width: auto;
  max-width: 100%;
  height: auto;
  max-height: min(72vh, 760px);
  object-fit: contain;
}

.tryon-results__detail-info {
  display: flex;
  align-items: center;
  flex-direction: column;
  justify-content: center;
  padding: var(--space-6);
}

.tryon-results__detail-date {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--color-text-secondary);
  font-size: 14px;
  font-weight: 600;
}

.tryon-results__detail-actions {
  display: flex;
  width: min(520px, 100%);
  gap: var(--space-3);
  margin-top: var(--space-4);
}

.tryon-results__detail-product,
.tryon-results__detail-delete {
  flex: 1;
  height: var(--button-height-standard);
  border-radius: var(--radius-control);
  font-weight: 600;
}

.tryon-results__detail-product {
  border: 1px solid var(--color-border-strong);
  background: var(--color-surface);
  color: var(--color-text-primary);
}

.tryon-results__detail-delete {
  border: 0;
  background: var(--color-error-soft);
  color: var(--color-error);
}

@media (max-width: 720px) {
  .tryon-results__detail {
    width: min(100%, calc(100vw - 24px));
    max-height: calc(100vh - 24px);
  }

  .tryon-results__detail-image img {
    max-height: min(68vh, 640px);
  }

  .tryon-results__detail-info {
    padding: var(--space-4);
  }
}
</style>
