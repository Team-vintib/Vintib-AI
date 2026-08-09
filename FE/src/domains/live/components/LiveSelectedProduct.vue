<script setup lang="ts">
import { computed } from 'vue'

import AppInlineNotice from '@/shared/components/AppInlineNotice.vue'

import type { LiveWatchProduct } from '@/domains/live/types/liveWatch.types'
import type { ProductDetailViewData } from '@/domains/product/types/productDetail.types'

// detail: 선택 상품의 상품 상세(GET /products/{id}) 결과. 라이브 응답에는 사이즈·색상이 없어서
// 부족한 항목을 이걸로 채운다. 아직 안 왔거나 조회에 실패하면 null이고, 그 경우 라이브 값만 쓴다.
const props = defineProps<{
  product: LiveWatchProduct | null
  detail: ProductDetailViewData | null
  isWished: boolean
  isWishPending: boolean
  wishMessage: string
}>()

const formatMeasurements = (measurements: Record<string, number> | undefined) => {
  const entries = Object.entries(measurements ?? {}).filter(
    ([label, value]) => label.trim() && Number.isFinite(value) && value > 0,
  )

  return entries.map(([label, value]) => `${label} ${value}cm`).join(' · ')
}

// 값이 빈 항목은 행 자체를 만들지 않는다(상품 상세 화면의 specItems와 같은 규칙).
// '정보 준비 중'처럼 아직 안 나온 정보인 척하는 문구는 쓰지 않는다.
const specItems = computed(() => {
  const live = props.product
  if (!live) return []

  const detail = props.detail

  return [
    { label: '브랜드', value: detail?.brand ?? '' },
    { label: '사이즈', value: detail?.sizeLabel ?? '' },
    { label: '색상', value: detail?.color ?? '' },
    { label: '소재', value: detail?.material || live.material || '' },
    { label: '상태', value: detail?.conditionLabel || live.condition || '' },
    {
      label: '실측',
      value: formatMeasurements(detail?.measurements) || live.measurements || '',
    },
  ]
    .map((item) => ({ ...item, value: item.value.trim() }))
    .filter((item) => item.value)
})

// 하자는 개수로만 보여준다 — 다른 항목과 같은 좁은 칸에 들어가야 하고, 판매자가 쓴 문장 전체는
// 상품 상세에서 읽으면 된다. 0건이면 "없음"을 명시한다: BE 계약상 하자 목록이 비어 있는 건
// "등록된 하자가 없다"는 뜻이고, 중고 거래에서 이건 구매자에게 의미 있는 정보다.
// 다만 상세를 아직 못 받았고 라이브 값도 없으면 단정하지 않고 숨긴다 — BE가 상품 행을 못 찾은
// 경우에도 모든 필드가 null로 오기 때문에 "없음"이 거짓이 될 수 있다.
const defectLabel = computed(() => {
  const detail = props.detail

  if (detail) {
    const count = detail.sellerDisclosedDefects.filter((defect) => defect.title.trim()).length

    return count > 0 ? `${count}개` : '없음'
  }

  // 라이브 응답의 defectSummary는 하자 항목을 쉼표로 이어 붙인 한 줄이라 쉼표로 나눠 센다.
  const summary = props.product?.defectSummary?.trim()
  if (!summary) return ''

  return `${summary.split(',').filter((item) => item.trim()).length}개`
})

defineEmits<{
  viewProduct: [productId: number]
  toggleWish: []
}>()
</script>

<template>
  <section class="live-selected-product" aria-labelledby="selected-product-title">
    <div class="live-selected-product__heading">
      <h2 id="selected-product-title">선택한 상품 정보</h2>
      <slot name="actions"></slot>
    </div>

    <div v-if="product" class="live-selected-product__body">
      <div class="live-selected-product__image">
        <img
          v-if="product.thumbnailUrl"
          :src="product.thumbnailUrl"
          :alt="`${product.title} 상품 이미지`"
        />
        <span v-else aria-hidden="true">상품</span>
      </div>

      <div class="live-selected-product__content">
        <div class="live-selected-product__identity">
          <strong>{{ product.title }}</strong>
        </div>

        <dl v-if="specItems.length || defectLabel" class="live-selected-product__details">
          <div v-for="item in specItems" :key="item.label">
            <dt>{{ item.label }}</dt>
            <dd>{{ item.value }}</dd>
          </div>
          <div v-if="defectLabel">
            <dt>하자</dt>
            <dd>{{ defectLabel }}</dd>
          </div>
        </dl>

        <div class="live-selected-product__actions">
          <button
            class="live-selected-product__wish"
            :class="{ 'live-selected-product__wish--active': isWished }"
            type="button"
            :aria-pressed="isWished"
            :disabled="isWishPending"
            @click="$emit('toggleWish')"
          >
            <svg v-if="!isWishPending" viewBox="0 0 24 24" aria-hidden="true">
              <path
                d="M20.3 5.7a5.1 5.1 0 0 0-7.2 0L12 6.8l-1.1-1.1a5.1 5.1 0 0 0-7.2 7.2L12 21l8.3-8.1a5.1 5.1 0 0 0 0-7.2Z"
              />
            </svg>
            {{ isWishPending ? '처리 중' : isWished ? '찜함' : '찜' }}
          </button>
        </div>
        <AppInlineNotice v-if="wishMessage" class="live-selected-product__wish-message">
          {{ wishMessage }}
        </AppInlineNotice>
      </div>
    </div>

    <div v-else class="live-selected-product__empty" role="status">
      상품이 연결되면 상세 정보가 이곳에 표시됩니다.
    </div>
  </section>
</template>

<style scoped lang="scss">
.live-selected-product {
  padding: 15px;
  border-top: 1px solid var(--color-live-border);
  background: var(--color-live-background);
}

.live-selected-product__heading {
  display: flex;
  min-height: 15px;
  align-items: center;
  margin-bottom: 10px;
}

.live-selected-product__heading h2 {
  color: var(--color-live-text-secondary);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-demibold);
  line-height: var(--line-height-tight);
}

.live-selected-product__body {
  display: grid;
  align-items: center;
  grid-template-columns: 180px minmax(0, 1fr);
  gap: 16px;
}

.live-selected-product__identity {
  min-width: 0;
}

.live-selected-product__content {
  min-width: 0;
}

.live-selected-product__image {
  display: grid;
  width: 180px;
  height: 180px;
  overflow: hidden;
  border-radius: var(--radius-control);
  background: var(--color-live-surface-raised);
  color: var(--color-live-text-secondary);
  font-size: var(--font-size-badge);
  place-items: center;
}

.live-selected-product__image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.live-selected-product__identity strong {
  display: -webkit-box;
  overflow: hidden;
  font-size: var(--font-size-2xl);
  line-height: 30px;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.live-selected-product__details {
  display: grid;
  margin-top: 3px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 2px 12px;
}

.live-selected-product__details > div {
  display: grid;
  /* '브랜드:'·'사이즈:'처럼 3글자 라벨이 들어와 46px로는 잘린다. */
  grid-template-columns: 58px minmax(0, 1fr);
  gap: 4px;
}

.live-selected-product__details dt,
.live-selected-product__details dd {
  overflow: hidden;
  font-size: var(--font-size-md);
  line-height: 22px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.live-selected-product__details dt {
  color: var(--color-live-text-secondary);
}

.live-selected-product__details dt::after {
  content: ':';
}

.live-selected-product__details dd {
  color: var(--color-live-text-primary);
}


.live-selected-product__actions {
  display: flex;
  align-items: center;
  margin-top: 7px;
  gap: var(--space-2);
}

.live-selected-product__actions button {
  display: inline-flex;
  height: 40px;
  min-height: 0;
  align-items: center;
  justify-content: center;
  padding: 0;
  border: 1px solid var(--color-live-border);
  border-radius: var(--radius-control);
  background: var(--color-live-surface-raised);
  color: var(--color-live-text-primary);
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-demibold);
  line-height: 1;
  white-space: nowrap;
}

.live-selected-product__actions button:hover {
  border-color: var(--color-live-text-secondary);
}

.live-selected-product__actions .live-selected-product__wish {
  width: auto;
  min-width: 37px;
  padding: 0 18px;
  gap: 8px;
  background: transparent;
}

.live-selected-product__actions .live-selected-product__wish:disabled {
  cursor: wait;
  opacity: 0.65;
}

.live-selected-product__wish-message {
  margin-top: 5px;
}

.live-selected-product__wish svg {
  width: 20px;
  height: 20px;
  fill: none;
  stroke: currentColor;
  stroke-linejoin: round;
  stroke-width: 1.7;
}

.live-selected-product__actions .live-selected-product__wish--active {
  border-color: var(--color-live);
  color: #f06a73;
}

.live-selected-product__wish--active svg {
  fill: currentColor;
}

.live-selected-product__actions button:focus-visible {
  outline: var(--focus-ring-width) solid var(--color-ai);
  outline-offset: 2px;
}

.live-selected-product__empty {
  display: grid;
  min-height: 68px;
  border: 1px dashed var(--color-live-border);
  border-radius: var(--radius-control);
  color: var(--color-live-text-secondary);
  font-size: var(--font-size-2xs);
  place-items: center;
}

@media (max-width: 1180px) {
  .live-selected-product__details {
    column-gap: var(--space-2);
  }
}

@media (max-width: 720px) {
  .live-selected-product__body {
    grid-template-columns: 1fr;
  }
}
</style>
