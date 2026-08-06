<script setup lang="ts">
import { computed } from 'vue'

import type { ProductDetailViewData } from '@/domains/product/types/productDetail.types'

const props = defineProps<{
  product: ProductDetailViewData
}>()

const description = computed(() => props.product.description.trim())

const specItems = computed(() =>
  [
    { label: '표기 사이즈', value: props.product.sizeLabel },
    { label: '색상', value: props.product.color },
    { label: '소재', value: props.product.material },
    { label: '상품 상태', value: props.product.conditionLabel },
  ]
    .map((item) => ({ ...item, value: item.value.trim() }))
    .filter((item) => item.value),
)

// 실측(measurements)은 BE 상세 계약(010)이 { 라벨: 값(cm) } 형태로 준다.
// 키가 라벨, 값이 cm 수치. 값이 없으면 실측 섹션 자체를 숨긴다.
const measurementEntries = computed(() =>
  Object.entries(props.product.measurements ?? {}).filter(
    ([label, value]) => label.trim() && Number.isFinite(value) && value > 0,
  ),
)

const disclosedDefects = computed(() =>
  props.product.sellerDisclosedDefects
    .map((defect) => ({
      title: defect.title.trim(),
      description: defect.description.trim(),
    }))
    .filter((defect) => defect.title || defect.description),
)

const hasInformation = computed(
  () =>
    Boolean(description.value) ||
    specItems.value.length > 0 ||
    measurementEntries.value.length > 0 ||
    disclosedDefects.value.length > 0,
)
</script>

<template>
  <section
    v-if="hasInformation"
    class="detail-information"
    aria-labelledby="detail-information-title"
  >
    <h2 id="detail-information-title">상품 상세 정보</h2>

    <p v-if="description" class="detail-information__description">{{ description }}</p>

    <dl v-if="specItems.length" class="detail-information__specs">
      <div v-for="item in specItems" :key="item.label">
        <dt>{{ item.label }}</dt>
        <dd>{{ item.value }}</dd>
      </div>
    </dl>

    <div v-if="measurementEntries.length" class="detail-information__sizes">
      <h3>실측</h3>
      <dl>
        <div v-for="[label, value] in measurementEntries" :key="label">
          <dt>{{ label }}</dt>
          <dd>{{ value }}cm</dd>
        </div>
      </dl>
    </div>

    <aside
      v-if="disclosedDefects.length"
      class="detail-information__seller-note"
      aria-label="상품 하자"
    >
      <strong>상품 하자</strong>
      <ul>
        <li v-for="(defect, index) in disclosedDefects" :key="`${defect.title}-${index}`">
          <p v-if="defect.title">{{ defect.title }}</p>
          <span v-if="defect.description">{{ defect.description }}</span>
        </li>
      </ul>
    </aside>
  </section>
</template>

<style scoped lang="scss">
.detail-information {
  margin-top: var(--space-12);
}

.detail-information > h2 {
  color: var(--color-text-primary);
  font-family: var(--font-display);
  font-size: var(--font-size-2xl-plus);
  font-weight: var(--font-weight-semibold);
  letter-spacing: -0.03em;
  line-height: 1.05;
}

.detail-information__description {
  margin-top: var(--space-4);
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  font-size: var(--font-size-body);
  font-weight: var(--font-weight-regular);
  line-height: var(--line-height-body);
}

.detail-information__specs {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1px;
  margin-top: var(--space-4);
  border: 1px solid var(--color-border-grid);
  border-radius: var(--radius-card);
  background: var(--color-border-grid);
  overflow: hidden;
}

.detail-information__specs div {
  display: grid;
  grid-template-columns: 180px 1fr;
  padding: var(--space-4) var(--space-5);
  background: var(--color-surface);
}

.detail-information__specs dt {
  color: var(--color-text-muted);
  font-family: var(--font-mono);
  font-size: var(--font-size-2xs);
  font-weight: var(--font-weight-regular);
  letter-spacing: 0.04em;
  line-height: var(--line-height-control);
}

.detail-information__specs dd {
  color: var(--color-text-primary);
  font-size: var(--font-size-md-plus);
  font-weight: var(--font-weight-medium);
  line-height: var(--line-height-body);
}

.detail-information__sizes {
  margin-top: var(--space-8);
}

.detail-information__sizes h3 {
  font-size: var(--font-size-md-plus);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-body);
}

.detail-information__sizes dl {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1px;
  margin-top: var(--space-3);
  border: 1px solid var(--color-border-grid);
  border-radius: var(--radius-card);
  background: var(--color-border-grid);
  overflow: hidden;
}

.detail-information__sizes div {
  padding: var(--space-4);
  background: var(--color-surface);
  text-align: center;
}

.detail-information__sizes dt {
  color: var(--color-text-muted);
  font-family: var(--font-mono);
  font-size: var(--font-size-badge);
  font-weight: var(--font-weight-regular);
  letter-spacing: 0.08em;
  line-height: var(--line-height-xs);
  text-transform: uppercase;
}

.detail-information__sizes dd {
  margin-top: var(--space-1);
  color: var(--color-text-primary);
  font-family: var(--font-mono);
  font-size: var(--font-size-md-plus);
  font-weight: var(--font-weight-medium);
  letter-spacing: -0.02em;
  line-height: var(--line-height-relaxed);
  font-variant-numeric: tabular-nums;
}

.detail-information__seller-note {
  display: flex;
  gap: var(--space-4);
  margin-top: var(--space-8);
  padding: var(--space-4) var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface-secondary);
}

.detail-information__seller-note strong {
  flex: 0 0 auto;
  font-size: var(--font-size-body);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-body);
}

.detail-information__seller-note ul {
  display: grid;
  min-width: 0;
  gap: var(--space-2);
  list-style: none;
}

.detail-information__seller-note li {
  min-width: 0;
}

.detail-information__seller-note p,
.detail-information__seller-note span {
  color: var(--color-text-secondary);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-regular);
  line-height: var(--line-height-snug);
}

.detail-information__seller-note span {
  display: block;
  margin-top: 2px;
  color: var(--color-text-muted);
}

@media (max-width: 720px) {
  .detail-information__sizes dl {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 480px) {
  .detail-information__specs div {
    grid-template-columns: 112px 1fr;
  }

  .detail-information__seller-note {
    display: block;
  }

  .detail-information__seller-note ul {
    margin-top: var(--space-1);
  }
}
</style>
