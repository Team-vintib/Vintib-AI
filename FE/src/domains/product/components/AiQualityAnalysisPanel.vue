<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import type { AiQualityAnalysis } from '@/domains/product/types/productDetail.types'

const props = defineProps<{
  analysis: AiQualityAnalysis
}>()

const images = computed(() => props.analysis.images)
const total = computed(() => images.value.length)
const currentIndex = ref(0)

const currentImage = computed(() => images.value[currentIndex.value] ?? images.value[0])

// 상품(=분석 대상)이 바뀌면 첫 장으로 되돌린다.
watch(
  () => props.analysis,
  () => {
    currentIndex.value = 0
  },
)

const goPrev = () => {
  if (total.value <= 1) return
  currentIndex.value = (currentIndex.value - 1 + total.value) % total.value
}

const goNext = () => {
  if (total.value <= 1) return
  currentIndex.value = (currentIndex.value + 1) % total.value
}

const goTo = (index: number) => {
  currentIndex.value = index
}

const statusMeta = computed(() => {
  const statusMap = {
    NOT_REQUESTED: {
      label: '분석 전',
      intro: '상품 이미지의 AI 품질 분석 준비 상태입니다.',
      title: '아직 AI 분석 결과가 없습니다',
      description: '상품 이미지 분석이 시작되면 이 영역에서 진행 상태와 결과를 확인할 수 있습니다.',
    },
    ANALYZING: {
      label: '분석 중',
      intro: 'AI가 등록 이미지에서 눈에 보이는 하자 후보를 검토하고 있습니다.',
      title: '상품 이미지를 분석하고 있습니다',
      description: '이미지에서 눈에 보이는 하자 후보와 위치를 확인하고 있습니다.',
    },
    COMPLETED: {
      label: '분석 완료',
      intro: '원본 상품 이미지와 AI가 표시한 검수 이미지를 넘겨 가며 비교해 보세요.',
      title: '',
      description: '',
    },
    NO_FINDINGS: {
      label: '분석 결과 없음',
      intro: 'AI 품질 분석 결과와 참고 안내를 확인해 주세요.',
      title: '눈에 띄는 하자 후보를 찾지 못했습니다',
      description:
        '등록 이미지에서 분석 가능한 범위의 하자 후보가 확인되지 않았습니다. 실제 상품 상태는 상세 설명과 판매자 고지를 함께 확인해 주세요.',
    },
    FAILED: {
      label: '분석 실패',
      intro: '분석이 완료되지 않아 AI 검수 이미지를 표시할 수 없습니다.',
      title: 'AI 분석을 완료하지 못했습니다',
      description:
        '이미지 상태가 분석에 적합하지 않거나 일시적인 시스템 오류가 발생했습니다. 상품 상세 설명과 판매자 고지를 확인해 주세요.',
    },
  } as const

  return statusMap[props.analysis.status]
})

const statusClass = computed(() => props.analysis.status.toLowerCase().replace('_', '-'))
</script>

<template>
  <section class="ai-analysis" aria-labelledby="ai-analysis-title">
    <div class="ai-analysis__tab-heading">
      <h2 id="ai-analysis-title">AI 분석</h2>
      <span :class="`ai-analysis__status--${statusClass}`">{{ statusMeta.label }}</span>
    </div>

    <p class="ai-analysis__intro">{{ statusMeta.intro }}</p>

    <template v-if="analysis.status === 'COMPLETED' && currentImage">
      <div class="ai-analysis__carousel-nav">
        <button
          type="button"
          class="ai-analysis__nav-button"
          :disabled="total <= 1"
          aria-label="이전 검수 이미지"
          @click="goPrev"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m15 18-6-6 6-6" /></svg>
        </button>

        <div class="ai-analysis__carousel-meta">
          <span class="ai-analysis__carousel-label">{{ currentImage.label }}</span>
          <span class="ai-analysis__carousel-count">{{ currentIndex + 1 }} / {{ total }}</span>
        </div>

        <button
          type="button"
          class="ai-analysis__nav-button"
          :disabled="total <= 1"
          aria-label="다음 검수 이미지"
          @click="goNext"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m9 6 6 6-6 6" /></svg>
        </button>
      </div>

      <div class="ai-analysis__comparison" aria-live="polite">
        <figure>
          <figcaption>{{ currentImage.label }} 원본 이미지</figcaption>
          <div class="ai-analysis__image-frame">
            <img :src="currentImage.originalImageUrl" :alt="currentImage.originalImageAlt" />
          </div>
        </figure>

        <figure>
          <figcaption>
            <span>{{ currentImage.label }} AI 검수 이미지</span>
            <span class="ai-analysis__reference-label">탐지 위치 표시</span>
          </figcaption>
          <div class="ai-analysis__image-frame">
            <img :src="currentImage.analyzedImageUrl" :alt="currentImage.analyzedImageAlt" />
            <span
              v-for="finding in currentImage.findings"
              v-show="finding.box"
              :key="finding.key"
              class="ai-analysis__box"
              :class="{ 'ai-analysis__box--excluded': finding.isExcluded }"
              :style="
                finding.box && {
                  left: `${finding.box.x}%`,
                  top: `${finding.box.y}%`,
                  width: `${finding.box.width}%`,
                  height: `${finding.box.height}%`,
                }
              "
            >
              <span class="ai-analysis__box-badge">{{ finding.no }}</span>
            </span>
          </div>
        </figure>
      </div>

      <div
        v-if="total > 1"
        class="ai-analysis__dots"
        role="tablist"
        aria-label="검수 이미지 선택"
      >
        <button
          v-for="(image, dotIndex) in images"
          :key="image.label"
          type="button"
          class="ai-analysis__dot"
          :class="{ 'ai-analysis__dot--active': dotIndex === currentIndex }"
          :aria-label="`${image.label} 검수 이미지 보기`"
          :aria-current="dotIndex === currentIndex"
          @click="goTo(dotIndex)"
        />
      </div>

      <div class="ai-analysis__description">
        <h3>AI 분석 설명</h3>

        <ul v-if="currentImage.findings.length">
          <li
            v-for="finding in currentImage.findings"
            :key="finding.key"
            :class="{ 'ai-analysis__finding--excluded': finding.isExcluded }"
          >
            <div class="ai-analysis__finding-title">
              <span class="ai-analysis__box-badge">{{ finding.no }}</span>
              <strong>{{ finding.type }}</strong>
            </div>
            <span class="ai-analysis__finding-location">{{ finding.location }}</span>
            <!-- AI가 설명 문장을 못 만들면(신뢰도 낮은 '의심' 항목 등) 아예 그리지 않는다. -->
            <p v-if="finding.description">{{ finding.description }}</p>
            <span v-if="finding.isExcluded" class="ai-analysis__excluded-note">
              판매자가 하자가 아니라고 확인한 항목입니다
            </span>
          </li>
        </ul>

        <p class="ai-analysis__disclaimer">
          <span aria-hidden="true">i</span>
          {{ analysis.disclaimer }}
        </p>
      </div>
    </template>

    <div
      v-else
      class="ai-analysis__state"
      :class="`ai-analysis__state--${statusClass}`"
      :aria-live="analysis.status === 'ANALYZING' ? 'polite' : undefined"
      :role="analysis.status === 'FAILED' ? 'alert' : 'status'"
    >
      <div class="ai-analysis__state-icon" aria-hidden="true">
        <span v-if="analysis.status === 'ANALYZING'" class="ai-analysis__spinner" />
        <svg v-else-if="analysis.status === 'NO_FINDINGS'" viewBox="0 0 24 24">
          <path d="m7 12 3 3 7-7" />
          <circle cx="12" cy="12" r="9" />
        </svg>
        <svg v-else-if="analysis.status === 'FAILED'" viewBox="0 0 24 24">
          <path d="M12 8v5m0 3.5v.5M10.3 4.6 3.2 17a2 2 0 0 0 1.7 3h14.2a2 2 0 0 0 1.7-3L13.7 4.6a2 2 0 0 0-3.4 0Z" />
        </svg>
        <svg v-else viewBox="0 0 24 24">
          <path d="m12 3 1.3 4.2L17.5 9l-4.2 1.8L12 15l-1.3-4.2L6.5 9l4.2-1.8L12 3Z" />
        </svg>
      </div>

      <h3>{{ statusMeta.title }}</h3>
      <p>{{ statusMeta.description }}</p>

      <p v-if="analysis.status === 'ANALYZING'" class="ai-analysis__state-note">
        분석이 완료되면 원본 이미지와 검수 이미지를 함께 표시합니다.
      </p>

      <p
        v-if="analysis.status === 'NO_FINDINGS' || analysis.status === 'FAILED'"
        class="ai-analysis__state-disclaimer"
      >
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
  color: var(--color-text-primary);
  font-size: var(--font-size-2xl-plus);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-2xl-plus);
}

.ai-analysis__tab-heading > span {
  padding: 3px var(--space-3);
  border-radius: var(--radius-badge);
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-xs);
}

.ai-analysis__tab-heading .ai-analysis__status--not-requested {
  background: var(--color-surface-secondary);
  color: var(--color-text-secondary);
}

.ai-analysis__tab-heading .ai-analysis__status--analyzing {
  background: var(--color-ai-soft);
  color: var(--color-ai);
}

.ai-analysis__tab-heading .ai-analysis__status--no-findings {
  background: var(--color-primary-soft);
  color: var(--color-primary);
}

.ai-analysis__tab-heading .ai-analysis__status--failed {
  background: var(--color-error-soft);
  color: var(--color-error);
}

.ai-analysis__intro {
  padding: var(--space-5) var(--space-6) 0;
  color: var(--color-text-secondary);
  font-size: var(--font-size-body);
  font-weight: var(--font-weight-regular);
  line-height: var(--line-height-body);
}

.ai-analysis__carousel-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-5) var(--space-6) 0;
}

.ai-analysis__nav-button {
  display: grid;
  width: var(--button-height-sm);
  height: var(--button-height-sm);
  border: 1px solid var(--color-border-strong);
  border-radius: 50%;
  background: var(--color-surface);
  color: var(--color-text-secondary);
  place-items: center;
  transition:
    border-color var(--transition-base),
    color var(--transition-base),
    opacity var(--transition-base);
}

.ai-analysis__nav-button svg {
  width: var(--icon-size-md);
  height: var(--icon-size-md);
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.8;
}

.ai-analysis__nav-button:hover:not(:disabled) {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.ai-analysis__nav-button:disabled {
  cursor: not-allowed;
  opacity: 0.4;
}

.ai-analysis__nav-button:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

.ai-analysis__carousel-meta {
  display: flex;
  align-items: baseline;
  gap: var(--space-3);
}

.ai-analysis__carousel-label {
  font-size: var(--font-size-md-plus);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-body);
}

.ai-analysis__carousel-count {
  color: var(--color-text-secondary);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-control);
}

.ai-analysis__comparison {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-4);
  // 원본/검수 이미지가 패널 폭을 꽉 채워 과하게 커지지 않도록 폭을 제한하고 가운데 정렬한다.
  max-width: 680px;
  margin: 0 auto;
  padding: var(--space-5) var(--space-6) var(--space-4);
}

.ai-analysis__comparison figure {
  min-width: 0;
}

.ai-analysis__comparison figcaption {
  display: flex;
  min-height: var(--filter-option-min-height);
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
  font-size: var(--font-size-md-plus);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-body);
}

.ai-analysis__reference-label {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-xs);
}

.ai-analysis__image-frame {
  // bbox %가 원본 이미지 전체 기준이라, aspect-ratio 고정 + object-fit:cover로 잘라 보여주면
  // 잘리기 전 좌표와 화면에 보이는 이미지가 어긋난다(등록 화면과 동일하게 원본 비율 그대로
  // 표시해야 좌표가 맞는다).
  position: relative;
  overflow: visible;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-media);
  background: var(--color-surface-secondary);
}

.ai-analysis__image-frame img {
  display: block;
  width: 100%;
  height: auto;
  border-radius: var(--radius-media);
}

.ai-analysis__box {
  position: absolute;
  border: 2px solid var(--color-error);
  border-radius: 2px;
  background: rgb(196 61 70 / 12%);
  pointer-events: none;
}

.ai-analysis__box-badge {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 999px;
  background: var(--color-error);
  color: var(--color-primary);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-bold);
  line-height: 1;
}

// 검수 이미지 위 마커일 때만 네모 밖 좌상단 모서리에 겹쳐 띄운다(등록 화면과 동일한 배치).
.ai-analysis__box .ai-analysis__box-badge {
  position: absolute;
  right: 100%;
  bottom: 100%;
  margin-right: 1px;
  margin-bottom: 1px;
}

/* 판매자가 "하자 아님"으로 확인한 항목 — 등록 화면(--excluded)과 같은 톤으로 죽여서 보여준다.
   응답에서 빼지 않는 건 번호(no)가 등록 화면과 어긋나지 않게 하기 위해서다(요청 043 §2). */
.ai-analysis__box--excluded {
  border-color: var(--color-border-strong);
  background: transparent;
}

.ai-analysis__box--excluded .ai-analysis__box-badge,
.ai-analysis__finding--excluded .ai-analysis__box-badge {
  background: var(--color-text-muted);
}

.ai-analysis__description li.ai-analysis__finding--excluded {
  border-style: dashed;
  opacity: 0.6;
}

.ai-analysis__finding--excluded strong {
  color: var(--color-text-muted);
  text-decoration: line-through;
}

.ai-analysis__excluded-note {
  display: block;
  margin-top: 2px;
  margin-left: calc(22px + var(--space-2));
  color: var(--color-text-muted);
  font-size: var(--font-size-caption);
  line-height: var(--line-height-snug);
}

.ai-analysis__dots {
  display: flex;
  justify-content: center;
  gap: var(--space-2);
  padding: 0 var(--space-6) var(--space-2);
}

.ai-analysis__dot {
  width: 8px;
  height: 8px;
  padding: 0;
  border: 0;
  border-radius: 50%;
  background: var(--color-border-strong);
  transition:
    background-color var(--transition-base),
    transform var(--transition-base);
}

.ai-analysis__dot--active {
  background: var(--color-primary);
  transform: scale(1.25);
}

.ai-analysis__dot:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

.ai-analysis__description {
  padding: var(--space-6);
  border-top: 1px solid var(--color-border);
}

.ai-analysis__description h3 {
  font-size: var(--font-size-md-plus);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-body);
}

.ai-analysis__description > p {
  margin-top: var(--space-2);
  color: var(--color-text-secondary);
  font-size: var(--font-size-body);
  font-weight: var(--font-weight-regular);
  line-height: var(--line-height-body);
}

.ai-analysis__description ul {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-3);
  margin-top: var(--space-5);
  list-style: none;
}

.ai-analysis__description li {
  display: grid;
  gap: var(--space-1);
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
}

.ai-analysis__finding-title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.ai-analysis__finding-title strong {
  color: var(--color-text-primary);
  font-size: var(--font-size-body);
  font-weight: var(--font-weight-bold);
}

.ai-analysis__finding-location {
  justify-self: start;
  /* 태그 자체 좌측 padding(space-2)이 하자 유형/설명과 같은 시작 위치를 채워주므로,
     박스는 배지 너비만큼만 민다(22px + space-2 padding = 하자 유형 시작 위치). */
  margin-left: 22px;
  padding: 2px var(--space-2);
  border-radius: 999px;
  background: var(--color-surface-secondary);
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
  white-space: nowrap;
}

.ai-analysis__description li p {
  margin-top: 2px;
  margin-left: calc(22px + var(--space-2));
  color: var(--color-text-secondary);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-regular);
  line-height: var(--line-height-snug);
}

.ai-analysis__description .ai-analysis__disclaimer {
  display: flex;
  gap: var(--space-3);
  margin-top: var(--space-5);
  padding: var(--space-4);
  border-radius: var(--radius-control);
  background: var(--color-surface-secondary);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-regular);
  line-height: var(--line-height-snug);
}

.ai-analysis__disclaimer > span {
  display: grid;
  flex: 0 0 auto;
  width: var(--icon-size-md);
  height: var(--icon-size-md);
  border: 1px solid var(--color-text-muted);
  border-radius: 50%;
  font-family: serif;
  font-weight: var(--font-weight-bold);
  place-items: center;
}

.ai-analysis__state {
  display: grid;
  min-height: 340px;
  align-content: center;
  justify-items: center;
  margin: var(--space-6);
  padding: var(--space-10);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface-secondary);
  text-align: center;
}

.ai-analysis__state-icon {
  display: grid;
  width: var(--icon-size-lg);
  height: var(--icon-size-lg);
  border-radius: 50%;
  background: var(--color-surface);
  color: var(--color-text-secondary);
  place-items: center;
}

.ai-analysis__state--analyzing .ai-analysis__state-icon {
  background: var(--color-ai-soft);
  color: var(--color-ai);
}

.ai-analysis__state--no-findings .ai-analysis__state-icon {
  background: var(--color-primary-soft);
  color: var(--color-primary);
}

.ai-analysis__state--failed .ai-analysis__state-icon {
  background: var(--color-error-soft);
  color: var(--color-error);
}

.ai-analysis__state-icon svg {
  width: var(--badge-height-md);
  height: var(--badge-height-md);
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.7;
}

.ai-analysis__spinner {
  width: var(--badge-height-md);
  height: var(--badge-height-md);
  border: 3px solid var(--color-ai-soft);
  border-top-color: var(--color-ai);
  border-radius: 50%;
  animation: ai-analysis-spin 900ms linear infinite;
}

.ai-analysis__state h3 {
  margin-top: var(--space-5);
  font-size: var(--font-size-md-plus);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-body);
}

.ai-analysis__state > p {
  max-width: 620px;
  margin-top: var(--space-2);
  color: var(--color-text-secondary);
  font-size: var(--font-size-body);
  line-height: var(--line-height-body);
}

.ai-analysis__state .ai-analysis__state-note {
  margin-top: var(--space-4);
  color: var(--color-ai);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-snug);
}

.ai-analysis__state .ai-analysis__state-disclaimer {
  display: flex;
  gap: var(--space-3);
  margin-top: var(--space-6);
  padding: var(--space-4);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  text-align: left;
}

.ai-analysis__state-disclaimer > span {
  display: grid;
  flex: 0 0 auto;
  width: var(--icon-size-md);
  height: var(--icon-size-md);
  border: 1px solid var(--color-text-muted);
  border-radius: 50%;
  font-family: serif;
  font-weight: var(--font-weight-bold);
  place-items: center;
}

@keyframes ai-analysis-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 760px) {
  .ai-analysis__comparison,
  .ai-analysis__description ul {
    grid-template-columns: 1fr;
  }
}

@media (prefers-reduced-motion: reduce) {
  .ai-analysis__spinner {
    animation: none;
  }
}
</style>
