<script setup lang="ts">
import { computed } from 'vue'

import type { ProductDetailViewData } from '@/domains/product/types/productDetail.types'

const props = defineProps<{
  product: ProductDetailViewData
}>()

// 실측(measurements)은 BE 상세 계약(010)이 { 라벨: 값(cm) } 형태로 준다.
// 키가 라벨, 값이 cm 수치. 값이 없으면 실측 섹션 자체를 숨긴다.
const measurementEntries = computed(() => Object.entries(props.product.measurements ?? {}))
</script>

<template>
  <section class="detail-information" aria-labelledby="detail-information-title">
    <h2 id="detail-information-title">상품 상세 정보</h2>

    <p class="detail-information__description">{{ product.description }}</p>

    <dl class="detail-information__specs">
      <div>
        <dt>표기 사이즈</dt>
        <dd>{{ product.sizeLabel }}</dd>
      </div>
      <div>
        <dt>색상</dt>
        <dd>{{ product.color }}</dd>
      </div>
      <div>
        <dt>소재</dt>
        <dd>{{ product.material }}</dd>
      </div>
      <div>
        <dt>상품 상태</dt>
        <dd>{{ product.conditionLabel }}</dd>
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

    <aside class="detail-information__seller-note" aria-label="판매자 고지">
      <strong>판매자 고지</strong>
      <p>
        판매자가 직접 입력한 상품 정보입니다. 아래 AI 분석 결과와 구분해서 확인해 주세요.
      </p>
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

.detail-information__seller-note p {
  color: var(--color-text-secondary);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-regular);
  line-height: var(--line-height-snug);
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

  .detail-information__seller-note p {
    margin-top: var(--space-1);
  }
}
</style>
