<script setup lang="ts">
import { computed } from 'vue'

import type {
  AiQualityAnalysis,
  ProductDetailImage,
} from '@/domains/product/types/productDetail.types'

const props = defineProps<{
  analysis: AiQualityAnalysis
  selectedImage: ProductDetailImage | undefined
}>()

const selectedImageIndex = computed(() => {
  const imageOrder = ['front', 'front-detail', 'hem-detail', 'cuff-detail']
  const selectedIndex = imageOrder.indexOf(props.selectedImage?.id ?? 'front')
  return selectedIndex >= 0 ? selectedIndex : 0
})

const comparisonImageStyle = computed(() => {
  const detailStyles = [
    { transform: 'scale(1)', transformOrigin: '50% 50%' },
    { transform: 'scale(1.35)', transformOrigin: '50% 26%' },
    { transform: 'scale(1.45)', transformOrigin: '45% 78%' },
    { transform: 'scale(1.45)', transformOrigin: '90% 78%' },
  ]

  return detailStyles[selectedImageIndex.value] ?? detailStyles[0]
})
</script>

<template>
  <section class="ai-analysis" aria-labelledby="ai-analysis-title">
    <div class="ai-analysis__tab-heading">
      <h2 id="ai-analysis-title">AI 분석</h2>
      <span>분석 완료</span>
    </div>

    <p class="ai-analysis__intro">
      원본 상품 이미지와 AI가 표시한 검수 이미지를 비교해 보세요.
    </p>

    <div class="ai-analysis__comparison" aria-live="polite">
      <figure>
        <figcaption>{{ selectedImage?.label ?? '대표' }} 원본 이미지</figcaption>
        <div class="ai-analysis__image-frame">
          <img
            :src="analysis.originalImageUrl"
            :alt="`${selectedImage?.label ?? '대표'} ${analysis.originalImageAlt}`"
            :style="comparisonImageStyle"
          />
        </div>
      </figure>

      <figure>
        <figcaption>
          <span>{{ selectedImage?.label ?? '대표' }} AI 검수 이미지</span>
          <span class="ai-analysis__reference-label">탐지 위치 표시</span>
        </figcaption>
        <div class="ai-analysis__image-frame">
          <img
            :src="analysis.analyzedImageUrl"
            :alt="`${selectedImage?.label ?? '대표'} ${analysis.analyzedImageAlt}`"
            :style="comparisonImageStyle"
          />
        </div>
      </figure>
    </div>

    <div class="ai-analysis__description">
      <h3>AI 분석 설명</h3>
      <p>{{ analysis.summary }}</p>

      <ul>
        <li v-for="(finding, index) in analysis.findings" :key="finding.id">
          <span>{{ index + 1 }}</span>
          <div>
            <strong>{{ finding.type }} · {{ finding.location }}</strong>
            <p>{{ finding.description }}</p>
          </div>
        </li>
      </ul>

      <p class="ai-analysis__disclaimer">
        <span aria-hidden="true">i</span>
        {{ analysis.disclaimer }}
      </p>
    </div>
  </section>
</template>

<style scoped lang="scss">
.ai-analysis {
  margin-top: var(--space-8);
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
}

.ai-analysis__tab-heading {
  display: flex;
  min-height: 58px;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: 0 var(--space-6);
  border-bottom: 1px solid var(--color-border);
}

.ai-analysis__tab-heading h2 {
  display: flex;
  align-self: stretch;
  align-items: center;
  border-bottom: 2px solid var(--color-primary);
  color: var(--color-primary);
  font-size: 26px;
  font-weight: 700;
  line-height: 36px;
}

.ai-analysis__tab-heading > span {
  padding: 3px var(--space-3);
  border-radius: var(--radius-badge);
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-size: 12px;
  font-weight: 600;
  line-height: 16px;
}

.ai-analysis__intro {
  padding: var(--space-5) var(--space-6) 0;
  color: var(--color-text-secondary);
  font-size: 15px;
  font-weight: 400;
  line-height: 24px;
}

.ai-analysis__comparison {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-6);
  padding: var(--space-6);
}

.ai-analysis__comparison figure {
  min-width: 0;
}

.ai-analysis__comparison figcaption {
  display: flex;
  min-height: 24px;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
  font-size: 17px;
  font-weight: 600;
  line-height: 24px;
}

.ai-analysis__reference-label {
  color: var(--color-text-muted);
  font-size: 12px;
  font-weight: 600;
  line-height: 16px;
}

.ai-analysis__image-frame {
  overflow: hidden;
  aspect-ratio: 4 / 5;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-media);
  background: var(--color-surface-secondary);
}

.ai-analysis__image-frame img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 180ms ease;
}

.ai-analysis__description {
  padding: var(--space-6);
  border-top: 1px solid var(--color-border);
}

.ai-analysis__description h3 {
  font-size: 17px;
  font-weight: 600;
  line-height: 24px;
}

.ai-analysis__description > p {
  margin-top: var(--space-2);
  color: var(--color-text-secondary);
  font-size: 15px;
  font-weight: 400;
  line-height: 24px;
}

.ai-analysis__description ul {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-3);
  margin-top: var(--space-5);
  list-style: none;
}

.ai-analysis__description li {
  display: flex;
  gap: var(--space-3);
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
}

.ai-analysis__description li > span {
  display: grid;
  flex: 0 0 auto;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--color-error);
  color: var(--color-text-inverse);
  font-size: 13px;
  font-weight: 800;
  line-height: 18px;
  place-items: center;
}

.ai-analysis__description li strong {
  font-size: 15px;
  font-weight: 600;
  line-height: 24px;
}

.ai-analysis__description li p {
  margin-top: 2px;
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: 400;
  line-height: 18px;
}

.ai-analysis__description .ai-analysis__disclaimer {
  display: flex;
  gap: var(--space-3);
  margin-top: var(--space-5);
  padding: var(--space-4);
  border-radius: var(--radius-control);
  background: var(--color-surface-secondary);
  font-size: 13px;
  font-weight: 400;
  line-height: 18px;
}

.ai-analysis__disclaimer > span {
  display: grid;
  flex: 0 0 auto;
  width: 20px;
  height: 20px;
  border: 1px solid var(--color-text-muted);
  border-radius: 50%;
  font-family: serif;
  font-weight: 700;
  place-items: center;
}

@media (max-width: 760px) {
  .ai-analysis__comparison,
  .ai-analysis__description ul {
    grid-template-columns: 1fr;
  }
}
</style>
