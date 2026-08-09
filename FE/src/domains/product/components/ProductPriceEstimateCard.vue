<script setup lang="ts">
import { computed } from 'vue'

import type { ProductPriceEstimate } from '@/domains/product/types/productDetail.types'

const props = defineProps<{
  estimate: ProductPriceEstimate | null
}>()

const CONFIDENCE_LABEL: Record<string, string> = {
  HIGH: '확신도 높음',
  MEDIUM: '확신도 보통',
  LOW: '확신도 낮음',
}

const confidenceLabel = computed(
  () => CONFIDENCE_LABEL[props.estimate?.confidenceLevel ?? ''] ?? null,
)

const formatPrice = (price: number) => `${price.toLocaleString('ko-KR')}원`

const visibleComps = computed(() => props.estimate?.compsUsed.slice(0, 3) ?? [])
</script>

<template>
  <section
    v-if="estimate?.priced && estimate.priceRange"
    class="price-estimate"
    aria-labelledby="price-estimate-title"
  >
    <div class="price-estimate__heading">
      <div>
        <h2 id="price-estimate-title">AI 시세 추천</h2>
        <p>등록 시 AI가 비교 매물을 조회해 산정한 추천가입니다.</p>
      </div>
      <span v-if="confidenceLabel" class="price-estimate__confidence">{{ confidenceLabel }}</span>
    </div>

    <div class="price-estimate__range">
      <span class="price-estimate__range-value">{{ formatPrice(estimate.priceRange.mid) }}</span>
      <span class="price-estimate__range-bounds">
        {{ formatPrice(estimate.priceRange.min) }} ~ {{ formatPrice(estimate.priceRange.max) }}
      </span>
    </div>

    <p v-if="estimate.rationale" class="price-estimate__rationale">{{ estimate.rationale }}</p>

    <ul v-if="visibleComps.length > 0" class="price-estimate__comps">
      <li v-for="(comp, index) in visibleComps" :key="`${comp.title}-${index}`">
        <span>{{ comp.title }}</span>
        <strong>{{ formatPrice(comp.price) }}</strong>
      </li>
    </ul>
  </section>
</template>

<style scoped lang="scss">
.price-estimate {
  margin-top: var(--space-10);
  padding: var(--space-6);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface-secondary);
}

.price-estimate__heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
}

.price-estimate__heading h2 {
  color: var(--color-text-primary);
  font-size: var(--font-size-md-plus);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-body);
}

.price-estimate__heading p {
  margin-top: var(--space-1);
  color: var(--color-text-muted);
  font-size: var(--font-size-caption);
  line-height: var(--line-height-snug);
}

.price-estimate__confidence {
  flex: 0 0 auto;
  padding: 5px var(--space-3);
  border: 1px solid var(--color-border-input);
  border-radius: var(--radius-badge);
  color: var(--color-text-secondary);
  font-size: var(--font-size-2xs);
  font-weight: var(--font-weight-regular);
  white-space: nowrap;
}

.price-estimate__range {
  display: flex;
  align-items: baseline;
  gap: var(--space-3);
  margin-top: var(--space-5);
}

.price-estimate__range-value {
  color: var(--color-primary);
  font-family: var(--font-mono);
  font-size: var(--font-size-lg);
  font-variant-numeric: tabular-nums;
  font-weight: var(--font-weight-bold);
}

.price-estimate__range-bounds {
  color: var(--color-text-muted);
  font-family: var(--font-mono);
  font-size: var(--font-size-caption);
  font-variant-numeric: tabular-nums;
}

.price-estimate__rationale {
  margin-top: var(--space-3);
  color: var(--color-text-secondary);
  font-size: var(--font-size-caption);
  line-height: var(--line-height-snug);
}

.price-estimate__comps {
  margin-top: var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.price-estimate__comps li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
}

.price-estimate__comps li > span {
  overflow: hidden;
  color: var(--color-text-primary);
  font-size: var(--font-size-caption);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.price-estimate__comps li > strong {
  flex: 0 0 auto;
  color: var(--color-text-secondary);
  font-family: var(--font-mono);
  font-size: var(--font-size-caption);
  font-variant-numeric: tabular-nums;
}
</style>
