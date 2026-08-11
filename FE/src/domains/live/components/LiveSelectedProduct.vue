<script setup lang="ts">
import { computed } from 'vue'

import AppInlineNotice from '@/shared/components/AppInlineNotice.vue'

import type { LiveWatchProduct } from '@/domains/live/types/liveWatch.types'
import type { ProductDetailViewData } from '@/domains/product/types/productDetail.types'

// detail: 선택 상품의 상품 상세(GET /products/{id}) 결과. 라이브 응답에는 사이즈·색상이 없어서
// 부족한 항목을 이걸로 채운다. 아직 안 왔거나 조회에 실패하면 null이고, 그 경우 라이브 값만 쓴다.
// compact: 사진과 제목만 남긴다(스펙 목록 숨김). 경매 탭처럼 아래에 들어갈 내용이 많아
// 스크롤 없이 한 화면에 담아야 할 때 쓴다.
const props = withDefaults(
  defineProps<{
    product: LiveWatchProduct | null
    detail: ProductDetailViewData | null
    isWished: boolean
    isWishPending: boolean
    wishMessage: string
    compact?: boolean
  }>(),
  { compact: false },
)

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

// 판매자가 직접 고지한 하자와 AI 검수가 찾은 하자는 출처가 다르다 — 둘 다 실제 하자라 합쳐 센다.
// AI 쪽은 판매자가 "하자 아님"으로 뒤집은 항목(isExcluded)을 뺀다. BE가 그 항목까지 응답에 담는 건
// 번호를 등록 화면과 맞추기 위해서일 뿐이라(요청 043 §2), 개수에는 넣으면 안 된다.
const defectCount = computed(() => {
  const detail = props.detail
  if (!detail) return null

  const disclosed = detail.sellerDisclosedDefects.filter((defect) => defect.title.trim()).length
  const aiDetected = (detail.aiQualityAnalysis?.images ?? []).reduce(
    (total, image) => total + image.findings.filter((finding) => !finding.isExcluded).length,
    0,
  )

  return disclosed + aiDetected
})

// 하자는 개수로만 보여준다 — 다른 항목과 같은 좁은 칸에 들어가야 하고, 자세한 내용은 상품 상세에서
// 읽으면 된다. 0건이면 "없음"을 명시한다: 중고 거래에서 하자가 없다는 건 구매자에게 의미 있는 정보다.
// 다만 상세를 아직 못 받았고 라이브 값도 없으면 단정하지 않고 숨긴다 — BE가 상품 행을 못 찾은
// 경우에도 모든 필드가 null로 오기 때문에 "없음"이 거짓이 될 수 있다.
const defectLabel = computed(() => {
  const count = defectCount.value
  if (count !== null) {
    return count > 0 ? `${count}개` : '없음'
  }

  // 상세를 아직 못 받았을 때의 임시 표시. 라이브 응답의 defectSummary는 판매자 고지 하자를
  // 쉼표로 이어 붙인 한 줄이라 쉼표로 나눠 센다(AI 하자는 여기에 없다).
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

        <!-- 찜은 사진 위 아이콘 하나로 끝낸다 — 좁은 사이드바에서 버튼 한 줄을 따로 쓰지 않는다.
             글자가 없어지므로 상태는 aria-label/title로 전한다. -->
        <button
          class="live-selected-product__wish"
          :class="{ 'live-selected-product__wish--active': isWished }"
          type="button"
          :aria-pressed="isWished"
          :aria-label="isWished ? '찜 해제' : '찜하기'"
          :title="isWishPending ? '처리 중' : isWished ? '찜 해제' : '찜하기'"
          :disabled="isWishPending"
          @click="$emit('toggleWish')"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path
              d="M20.3 5.7a5.1 5.1 0 0 0-7.2 0L12 6.8l-1.1-1.1a5.1 5.1 0 0 0-7.2 7.2L12 21l8.3-8.1a5.1 5.1 0 0 0 0-7.2Z"
            />
          </svg>
        </button>
      </div>

      <div class="live-selected-product__content">
        <div class="live-selected-product__identity">
          <strong>{{ product.title }}</strong>
        </div>

        <dl
          v-if="!compact && (specItems.length || defectLabel)"
          class="live-selected-product__details"
        >
          <div v-for="item in specItems" :key="item.label">
            <dt>{{ item.label }}</dt>
            <dd>{{ item.value }}</dd>
          </div>
          <div v-if="defectLabel">
            <dt>하자</dt>
            <dd>{{ defectLabel }}</dd>
          </div>
        </dl>

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
  display: flex;
  min-height: 0;
  flex-direction: column;
  padding: 14px 16px;
  background: var(--color-live-background);
}

/* 제목("선택한 상품 정보")은 패널 제목 줄과 겹쳐 군더더기라 숨긴다. 스크린리더에는 남는다. */
.live-selected-product__heading {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}

/* 우측 패널(440px) 위쪽 칸 — 사진이 폭을 가득 쓰고, 남는 세로 공간도 사진이 흡수한다.
   사진 높이를 고정하면 구매/경매 버튼과 하단 버튼 사이에 큰 빈 칸이 남는다. */
.live-selected-product__body {
  display: flex;
  min-height: 0;
  flex: 1 1 auto;
  flex-direction: column;
  gap: 12px;
}

.live-selected-product__content {
  flex: 0 0 auto;
}

.live-selected-product__identity {
  min-width: 0;
}

.live-selected-product__content {
  min-width: 0;
}

.live-selected-product__image {
  display: grid;
  position: relative;
  width: 100%;
  min-height: 120px;
  flex: 1 1 auto;
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
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  line-height: 24px;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

/* 사이드바 폭에서는 2열이 안 들어간다 — 라벨:값 한 줄씩 쌓는다. */
.live-selected-product__details {
  display: grid;
  margin-top: 6px;
  grid-template-columns: minmax(0, 1fr);
  gap: 1px;
}

.live-selected-product__details > div {
  display: grid;
  /* '브랜드:'·'사이즈:'처럼 3글자 라벨이 들어와 52px 아래로는 잘린다. */
  grid-template-columns: 52px minmax(0, 1fr);
  gap: 6px;
}

.live-selected-product__details dt,
.live-selected-product__details dd {
  overflow: hidden;
  font-size: var(--font-size-caption);
  line-height: 21px;
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


/* 찜: 사진 오른쪽 아래 하트 아이콘 하나. */
.live-selected-product__wish {
  display: grid;
  position: absolute;
  right: 6px;
  bottom: 6px;
  width: 28px;
  height: 28px;
  padding: 0;
  border: 0;
  border-radius: 50%;
  background: rgba(8, 8, 8, 0.62);
  color: var(--color-live-text-primary);
  place-items: center;
  backdrop-filter: blur(6px);
}

.live-selected-product__wish:hover {
  background: rgba(8, 8, 8, 0.8);
}

.live-selected-product__wish:disabled {
  cursor: wait;
  opacity: 0.6;
}

.live-selected-product__wish svg {
  width: 16px;
  height: 16px;
  fill: none;
  stroke: currentColor;
  stroke-linejoin: round;
  stroke-width: 1.7;
}

.live-selected-product__wish--active {
  color: #f06a73;
}

.live-selected-product__wish--active svg {
  fill: currentColor;
}

.live-selected-product__wish:focus-visible {
  outline: var(--focus-ring-width) solid var(--color-ai);
  outline-offset: 2px;
}

.live-selected-product__wish-message {
  margin-top: 5px;
}

.live-selected-product__empty {
  display: grid;
  min-height: 68px;
  padding: 0 var(--space-3);
  border: 1px dashed var(--color-live-border);
  border-radius: var(--radius-control);
  color: var(--color-live-text-secondary);
  font-size: var(--font-size-xs);
  line-height: var(--line-height-xs);
  text-align: center;
  place-items: center;
}
</style>
