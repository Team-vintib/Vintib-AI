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

const bodyPhotoUrl = ref<string | null>(null)
const wishItems = ref<ProductListItem[]>([])
const selectedProductId = ref<number | null>(null)
const isLoading = ref(true)
const isGenerating = ref(false)
const generatedResult = ref<TryOnResult | null>(null)
const carouselTrack = ref<HTMLElement | null>(null)

const userId = computed(() => authStore.user?.id ?? null)
const selectedProduct = computed(
  () => wishItems.value.find((item) => item.id === selectedProductId.value) ?? null,
)
const canTryOn = computed(() => Boolean(bodyPhotoUrl.value) && selectedProduct.value !== null && !isGenerating.value)

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

const selectProduct = (productId: number) => {
  selectedProductId.value = productId
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
  const product = selectedProduct.value

  if (!canTryOn.value || !product) {
    return
  }

  isGenerating.value = true

  // 실제 AI 합성(POST /users/{id}/tryons)이 미구현이라 mock 결과를 만든다.
  // 합성 API가 붙으면 이 자리에서 실제 결과를 받아 emit 한다.
  window.setTimeout(() => {
    const result: TryOnResult = {
      id: Date.now(),
      productId: product.id,
      imageUrl: buildMockTryOnResultImage(`${product.name} 시착`),
      createdAt: nowWallClock(),
      category: product.categoryName ?? null,
    }

    generatedResult.value = result
    isGenerating.value = false
    emit('generated', result)
  }, 700)
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
        <img
          v-if="generatedResult"
          :src="generatedResult.imageUrl"
          alt="AI 입어보기 결과 미리보기"
        />
        <img v-else-if="bodyPhotoUrl" :src="bodyPhotoUrl" alt="등록한 전신 사진" />
        <div v-else class="tryon-composer__photo-empty">
          <p>등록된 전신 사진이 없습니다.</p>
          <button type="button" class="tryon-composer__photo-link" @click="goToProfile">
            전신 사진 등록하기
          </button>
        </div>

        <span v-if="isGenerating" class="tryon-composer__photo-loading" role="status">
          AI 시착 이미지를 생성하고 있습니다…
        </span>
        <span v-else-if="generatedResult" class="tryon-composer__photo-tag">미리보기 · mock</span>
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
              :class="{ 'tryon-composer__item--selected': selectedProductId === item.id }"
              :aria-pressed="selectedProductId === item.id"
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
          {{ isGenerating ? '생성 중…' : '입어보기' }}
        </button>
        <p class="tryon-composer__hint">
          실제 AI 합성 연결 전까지는 미리보기(mock)로 동작합니다.
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
</style>
