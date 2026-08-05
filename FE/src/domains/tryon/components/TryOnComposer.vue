<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/domains/auth/stores/authStore'
import { getMyWishList } from '@/domains/my/api/myApi'
import { getMyTryOnProfile } from '@/domains/tryon/api/tryOnProfileApi'
import { buildMockTryOnResultImage } from '@/domains/tryon/constants/tryOnResultMockData'
import { ROUTE_PATHS } from '@/shared/constants/routes'

import type { ProductListItem } from '@/domains/product/types/productList.types'
import type { TryOnResult } from '@/domains/tryon/types/tryOnResult.types'

const emit = defineEmits<{
  generated: [result: TryOnResult]
}>()

const authStore = useAuthStore()
const router = useRouter()

interface PreviewResult {
  result: TryOnResult
  productName: string
  saved: boolean
}

const bodyPhotoUrl = ref<string | null>(null)
const wishItems = ref<ProductListItem[]>([])
const selectedProductIds = ref<number[]>([])
const isLoading = ref(true)
const isGenerating = ref(false)
const generatedResults = ref<PreviewResult[]>([])
const carouselTrack = ref<HTMLElement | null>(null)

const userId = computed(() => authStore.user?.id ?? null)
const selectedProducts = computed(() =>
  wishItems.value.filter((item) => selectedProductIds.value.includes(item.id)),
)
const canTryOn = computed(
  () => Boolean(bodyPhotoUrl.value) && selectedProducts.value.length > 0 && !isGenerating.value,
)

const load = async () => {
  isLoading.value = true

  const currentUserId = userId.value

  try {
    const profile = await getMyTryOnProfile(currentUserId)
    bodyPhotoUrl.value = profile.bodyPhotoUrl

    // 찜 목록 조회는 회원 ID가 있어야 한다(getMyWishList는 number만 받음).
    wishItems.value =
      currentUserId != null
        ? (await getMyWishList(currentUserId)).items.map((wish) => wish.product)
        : []
  } catch {
    wishItems.value = []
  } finally {
    isLoading.value = false
  }
}

// AI 시착 페이지에서만 여러 옷을 동시에 고를 수 있다(라이브·상품 상세 시착은 단일 선택).
// 단 카테고리당 1개만 유지한다.
const selectProduct = (productId: number) => {
  const target = wishItems.value.find((item) => item.id === productId)
  if (!target) return

  if (selectedProductIds.value.includes(productId)) {
    selectedProductIds.value = selectedProductIds.value.filter((id) => id !== productId)
    return
  }

  // 같은 카테고리로 이미 고른 옷은 교체한다(카테고리 없으면 교체하지 않음).
  const sameCategoryIds = target.categoryName
    ? wishItems.value
        .filter((item) => item.categoryName === target.categoryName)
        .map((item) => item.id)
    : []
  selectedProductIds.value = [
    ...selectedProductIds.value.filter((id) => !sameCategoryIds.includes(id)),
    productId,
  ]
}

const scrollCarousel = (direction: 1 | -1) => {
  carouselTrack.value?.scrollBy({ left: direction * 240, behavior: 'smooth' })
}

const nowWallClock = () => {
  const now = new Date()
  const pad = (value: number) => String(value).padStart(2, '0')

  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}T${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`
}

const tryOn = () => {
  const products = selectedProducts.value

  if (!canTryOn.value || products.length === 0) {
    return
  }

  isGenerating.value = true
  // 새로 입어보면 이전 미리보기는 버린다(저장 안 한 결과는 남기지 않는다).
  generatedResults.value = []

  // 실제 AI 합성(POST /users/{id}/tryons)이 미구현이라 선택한 옷마다 mock 결과를 만든다.
  // 합성 API가 붙으면 이 자리에서 실제 결과들을 받아 미리보기에 채운다.
  window.setTimeout(() => {
    const createdAt = nowWallClock()
    generatedResults.value = products.map((product, index) => ({
      result: {
        id: Date.now() + index,
        productId: product.id,
        imageUrl: buildMockTryOnResultImage(`${product.name} 시착`),
        createdAt,
        category: product.categoryName ?? null,
      },
      productName: product.name,
      saved: false,
    }))
    isGenerating.value = false
  }, 700)
}

// 각 미리보기가 맘에 들 때만 저장 → 이때 갤러리에 추가된다(입어보기만으로 자동 저장하지 않는다).
const saveResult = (resultId: number) => {
  const preview = generatedResults.value.find((item) => item.result.id === resultId)
  if (!preview || preview.saved) {
    return
  }

  emit('generated', preview.result)
  preview.saved = true
}

// 저장하지 않은 것까지 미리보기 전체를 버린다.
const discardResults = () => {
  generatedResults.value = []
}

const goToProfile = () => {
  void router.push({ path: ROUTE_PATHS.MY, query: { section: 'tryon' } })
}

onMounted(load)
</script>

<template>
  <section class="tryon-composer" aria-label="AI 입어보기">
    <div class="tryon-composer__body">
      <div class="tryon-composer__photo">
        <img v-if="bodyPhotoUrl" :src="bodyPhotoUrl" alt="등록한 전신 사진" />
        <div v-else class="tryon-composer__photo-empty">
          <p>등록된 전신 사진이 없습니다.</p>
          <button type="button" class="tryon-composer__photo-link" @click="goToProfile">
            전신 사진 등록하기
          </button>
        </div>

        <span v-if="isGenerating" class="tryon-composer__photo-loading" role="status">
          AI 시착 이미지를 생성하고 있습니다…
        </span>
      </div>

      <div v-if="generatedResults.length && !isGenerating" class="tryon-composer__results">
        <div class="tryon-composer__results-head">
          <span>입어본 결과 · 맘에 드는 것만 저장하세요</span>
          <button type="button" class="tryon-composer__results-clear" @click="discardResults">
            다시 입어보기
          </button>
        </div>
        <ul class="tryon-composer__results-list">
          <li
            v-for="preview in generatedResults"
            :key="preview.result.id"
            class="tryon-composer__result-card"
          >
            <span class="tryon-composer__result-thumb">
              <img :src="preview.result.imageUrl" :alt="`${preview.productName} 시착 결과 미리보기`" />
              <span class="tryon-composer__result-mock">mock</span>
            </span>
            <span class="tryon-composer__result-name">{{ preview.productName }}</span>
            <button
              v-if="!preview.saved"
              type="button"
              class="tryon-composer__result-save"
              @click="saveResult(preview.result.id)"
            >
              저장
            </button>
            <span v-else class="tryon-composer__result-saved" role="status">저장됨</span>
          </li>
        </ul>
      </div>

      <div class="tryon-composer__picker">
        <div class="tryon-composer__picker-head">
          <span>찜한 옷</span>
          <div class="tryon-composer__nav">
            <button type="button" aria-label="이전 옷 보기" @click="scrollCarousel(-1)">‹</button>
            <button type="button" aria-label="다음 옷 보기" @click="scrollCarousel(1)">›</button>
          </div>
        </div>

        <p v-if="isLoading" class="tryon-composer__picker-state">찜한 옷을 불러오는 중…</p>
        <p v-else-if="!wishItems.length" class="tryon-composer__picker-state">
          찜한 옷이 없습니다. 상품을 찜하면 여기서 바로 입어볼 수 있어요.
        </p>

        <ul v-else ref="carouselTrack" class="tryon-composer__track">
          <li v-for="item in wishItems" :key="item.id">
            <button
              type="button"
              class="tryon-composer__item"
              :class="{ 'tryon-composer__item--selected': selectedProductIds.includes(item.id) }"
              :aria-pressed="selectedProductIds.includes(item.id)"
              @click="selectProduct(item.id)"
            >
              <span class="tryon-composer__item-thumb">
                <img :src="item.imageUrl" :alt="item.imageAlt || item.name" />
              </span>
              <span class="tryon-composer__item-name">{{ item.name }}</span>
            </button>
          </li>
        </ul>

        <button type="button" class="tryon-composer__cta" :disabled="!canTryOn" @click="tryOn">
          {{
            isGenerating
              ? '생성 중…'
              : selectedProducts.length
                ? `입어보기 (${selectedProducts.length})`
                : '입어보기'
          }}
        </button>
        <p class="tryon-composer__hint">
          카테고리별로 하나씩 여러 옷을 골라 함께 입어볼 수 있어요. 실제 합성 전까지는 미리보기(mock)입니다.
        </p>
      </div>
    </div>
  </section>
</template>

<style scoped lang="scss">
.tryon-composer__body {
  display: grid;
  gap: var(--space-6);
}

.tryon-composer__photo {
  position: relative;
  display: grid;
  width: 100%;
  max-width: 320px;
  margin: 0 auto;
  overflow: hidden;
  aspect-ratio: 3 / 5;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-image-frame);
  place-items: center;
}

.tryon-composer__photo img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  filter: saturate(0.86) contrast(1.04);
}

.tryon-composer__photo-empty {
  display: grid;
  gap: var(--space-3);
  justify-items: center;
  padding: var(--space-6);
  color: var(--color-text-secondary);
  text-align: center;
}

.tryon-composer__photo-link {
  padding: var(--space-2) var(--space-4);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-weight: 600;
}

.tryon-composer__photo-loading,
.tryon-composer__photo-tag {
  position: absolute;
  left: var(--space-3);
  bottom: var(--space-3);
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-badge);
  background: rgba(10, 10, 10, 0.82);
  color: var(--color-text-primary);
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.08em;
}

.tryon-composer__picker {
  display: flex;
  min-width: 0;
  flex-direction: column;
}

.tryon-composer__picker-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 15px;
  font-weight: 600;
}

.tryon-composer__nav {
  display: flex;
  gap: var(--space-2);
}

.tryon-composer__nav button {
  display: grid;
  width: 32px;
  height: 32px;
  border: 1px solid var(--color-border-strong);
  border-radius: 50%;
  background: var(--color-surface);
  color: var(--color-text-secondary);
  font-size: 18px;
  line-height: 1;
  place-items: center;
  transition:
    border-color 160ms ease,
    color 160ms ease;
}

.tryon-composer__nav button:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.tryon-composer__picker-state {
  padding: var(--space-8) 0;
  color: var(--color-text-muted);
  font-size: 14px;
  text-align: center;
}

.tryon-composer__track {
  display: flex;
  gap: var(--space-3);
  margin-top: var(--space-4);
  padding-bottom: var(--space-2);
  list-style: none;
  overflow-x: auto;
  scroll-snap-type: x mandatory;
}

.tryon-composer__item {
  display: grid;
  width: 132px;
  padding: 0;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
  overflow: hidden;
  scroll-snap-align: start;
  transition:
    border-color 160ms ease,
    transform 160ms ease;
}

.tryon-composer__item:hover {
  border-color: var(--color-border-strong);
  transform: translateY(-3px);
}

.tryon-composer__item:hover .tryon-composer__item-thumb img {
  transform: scale(1.045);
}

.tryon-composer__item--selected {
  border: 2px solid var(--color-primary);
}

.tryon-composer__item:focus-visible {
  outline: 1px solid var(--color-primary);
  outline-offset: 2px;
}

.tryon-composer__item-thumb {
  display: block;
  overflow: hidden;
  aspect-ratio: 4 / 5;
  background: var(--color-image-frame);
}

.tryon-composer__item-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  filter: saturate(0.88) contrast(1.04) brightness(0.95);
  transition: transform 620ms cubic-bezier(0.22, 1, 0.36, 1);
}

.tryon-composer__item-name {
  display: block;
  padding: var(--space-2) var(--space-3);
  color: var(--color-text-primary);
  font-size: 12px;
  font-weight: 600;
  line-height: 16px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tryon-composer__cta {
  height: var(--button-height-major);
  margin-top: var(--space-5);
  border: 0;
  border-radius: var(--radius-control);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-size: 14px;
  font-weight: 500;
  transition:
    background-color 160ms ease,
    color 160ms ease;
}

.tryon-composer__cta:hover:not(:disabled) {
  background: var(--color-primary-hover);
  color: var(--color-primary-strong);
}

.tryon-composer__cta:disabled {
  background: var(--color-border-grid);
  color: var(--color-text-disabled);
  cursor: not-allowed;
}

.tryon-composer__hint {
  margin-top: var(--space-2);
  color: var(--color-text-muted);
  font-size: 12px;
  text-align: center;
}

.tryon-composer__results {
  margin-top: var(--space-6);
  padding-top: var(--space-5);
  border-top: 1px solid var(--color-border);
}

.tryon-composer__results-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  color: var(--color-text-secondary);
  font-size: 13px;
}

.tryon-composer__results-clear {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  font-size: 12px;
  font-weight: 500;
  transition:
    border-color 160ms ease,
    color 160ms ease;
}

.tryon-composer__results-clear:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.tryon-composer__results-list {
  display: flex;
  gap: var(--space-3);
  margin-top: var(--space-4);
  padding-bottom: var(--space-2);
  list-style: none;
  overflow-x: auto;
}

.tryon-composer__result-card {
  display: flex;
  width: 148px;
  flex: 0 0 auto;
  flex-direction: column;
  gap: var(--space-2);
}

.tryon-composer__result-thumb {
  position: relative;
  display: block;
  overflow: hidden;
  aspect-ratio: 3 / 5;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-image-frame);
}

.tryon-composer__result-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  filter: saturate(0.86) contrast(1.04);
}

.tryon-composer__result-mock {
  position: absolute;
  left: var(--space-2);
  bottom: var(--space-2);
  padding: 2px var(--space-2);
  border-radius: var(--radius-badge);
  background: rgba(10, 10, 10, 0.82);
  color: var(--color-text-primary);
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.08em;
}

.tryon-composer__result-name {
  overflow: hidden;
  color: var(--color-text-primary);
  font-size: 12px;
  font-weight: 600;
  line-height: 16px;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.tryon-composer__result-save {
  height: 34px;
  border: 0;
  border-radius: var(--radius-control);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-size: 13px;
  font-weight: 500;
  transition:
    background-color 160ms ease,
    color 160ms ease;
}

.tryon-composer__result-save:hover {
  background: var(--color-primary-hover);
  color: var(--color-primary-strong);
}

.tryon-composer__result-saved {
  display: grid;
  height: 34px;
  border-radius: var(--radius-control);
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-size: 13px;
  font-weight: 600;
  place-items: center;
}
</style>
