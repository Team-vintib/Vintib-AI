<script setup lang="ts">
import { computed, reactive, ref } from 'vue'

import {
  LIVE_CREATE_BASE_STEPS,
  LIVE_CREATE_COMPLETE_STEP,
  LIVE_CREATE_DEVICE_STEP,
  LIVE_CREATE_METHOD_OPTIONS,
  LIVE_CREATE_MOCK_PRODUCTS,
  LIVE_CREATE_SCHEDULE_STEP,
} from '@/domains/live/constants/liveCreateMockData'
import type {
  LiveCreateFormState,
  LiveCreateMode,
  LiveCreateStep,
} from '@/domains/live/types/liveCreate.types'
import DefaultLayout from '@/shared/layouts/DefaultLayout.vue'

const form = reactive<LiveCreateFormState>({
  mode: '',
  title: '',
  description: '',
  mainBrand: '',
  productKeyword: '',
  selectedProductIds: [],
  scheduledDate: '',
  scheduledTime: '',
})

const currentStepIndex = ref(0)

const liveCreateSteps = computed<LiveCreateStep[]>(() => {
  const modeStep =
    form.mode === 'SCHEDULED'
      ? LIVE_CREATE_SCHEDULE_STEP
      : form.mode === 'IMMEDIATE'
        ? LIVE_CREATE_DEVICE_STEP
        : LIVE_CREATE_SCHEDULE_STEP

  return [...LIVE_CREATE_BASE_STEPS, modeStep, LIVE_CREATE_COMPLETE_STEP]
})

const currentStep = computed(() => liveCreateSteps.value[currentStepIndex.value])
const selectedMethod = computed(() =>
  LIVE_CREATE_METHOD_OPTIONS.find((option) => option.id === form.mode),
)
const isFirstStep = computed(() => currentStepIndex.value === 0)
const isLastStep = computed(() => currentStepIndex.value === liveCreateSteps.value.length - 1)
const canMoveNext = computed(() => currentStep.value.id !== 'method' || Boolean(form.mode))
const selectedProductCountLabel = computed(() =>
  form.selectedProductIds.length > 0 ? `${form.selectedProductIds.length}개` : '',
)
const scheduleSummary = computed(() => {
  if (!form.scheduledDate && !form.scheduledTime) {
    return ''
  }

  return [form.scheduledDate, form.scheduledTime].filter(Boolean).join(' ')
})
const selectedProducts = computed(() =>
  LIVE_CREATE_MOCK_PRODUCTS.filter((product) => form.selectedProductIds.includes(product.id)),
)

const selectMode = (mode: LiveCreateMode) => {
  form.mode = mode
}

const moveToPreviousStep = () => {
  if (isFirstStep.value) {
    return
  }

  currentStepIndex.value -= 1
}

const moveToNextStep = () => {
  if (isLastStep.value || !canMoveNext.value) {
    return
  }

  currentStepIndex.value += 1
}
</script>

<template>
  <DefaultLayout content-max-width="1120px">
    <section class="live-create" aria-labelledby="live-create-title">
      <header class="live-create__header">
        <h1 id="live-create-title">라이브 시작</h1>
        <p>방송 방식과 기본 정보를 정리한 뒤 라이브를 개설합니다.</p>
      </header>

      <nav class="live-create__steps" aria-label="라이브 개설 단계">
        <ol>
          <li
            v-for="(step, index) in liveCreateSteps"
            :key="step.id"
            :class="{
              'live-create__step--current': index === currentStepIndex,
              'live-create__step--complete': index < currentStepIndex,
            }"
            :aria-current="index === currentStepIndex ? 'step' : undefined"
          >
            <span>{{ index + 1 }}</span>
            <strong>{{ step.label }}</strong>
          </li>
        </ol>
      </nav>

      <div class="live-create__body">
        <section class="live-create__panel" :aria-labelledby="`${currentStep.id}-title`">
          <h2 :id="`${currentStep.id}-title`">{{ currentStep.label }}</h2>
          <p>{{ currentStep.description }}</p>

          <div class="live-create__method-grid" aria-label="라이브 유형 선택">
            <button
              v-for="method in LIVE_CREATE_METHOD_OPTIONS"
              :key="method.id"
              class="live-create__method"
              :class="{ 'live-create__method--selected': form.mode === method.id }"
              type="button"
              :aria-pressed="form.mode === method.id"
              @click="selectMode(method.id)"
            >
              <strong>{{ method.title }}</strong>
              <span>{{ method.description }}</span>
            </button>
          </div>

        </section>

        <aside class="live-create__side" aria-label="방송 정보와 단계 이동">
          <section class="live-create__summary" aria-label="방송 정보">
            <h2>방송 정보</h2>
            <dl>
              <div>
                <dt>라이브 유형</dt>
                <dd>{{ selectedMethod?.title || '' }}</dd>
              </div>
              <div>
                <dt>방송 제목</dt>
                <dd>{{ form.title.trim() }}</dd>
              </div>
              <div>
                <dt>한 줄 소개</dt>
                <dd>{{ form.description.trim() }}</dd>
              </div>
              <div>
                <dt>선택 상품</dt>
                <dd>{{ selectedProductCountLabel }}</dd>
              </div>
              <div>
                <dt>일정</dt>
                <dd>{{ scheduleSummary }}</dd>
              </div>
            </dl>

            <div v-if="selectedProducts.length" class="live-create__products">
              <h3>상품 선택 미리보기</h3>
              <article v-for="product in selectedProducts" :key="product.id">
                <img :src="product.thumbnailUrl" :alt="product.name" />
                <div>
                  <strong>{{ product.name }}</strong>
                  <span>{{ product.brand }} · {{ product.condition }}</span>
                </div>
              </article>
            </div>
          </section>

          <div class="live-create__actions">
            <button
              class="live-create__button live-create__button--secondary"
              type="button"
              :disabled="isFirstStep"
              @click="moveToPreviousStep"
            >
              이전
            </button>
            <button
              class="live-create__button live-create__button--primary"
              type="button"
              :disabled="isLastStep || !canMoveNext"
              @click="moveToNextStep"
            >
              {{ isLastStep ? '완료' : '다음' }}
            </button>
          </div>
        </aside>
      </div>
    </section>
  </DefaultLayout>
</template>

<style scoped lang="scss">
.live-create {
  display: grid;
  gap: var(--space-8);
  padding-bottom: var(--space-16);
}

.live-create__header {
  display: grid;
  gap: var(--space-2);
  padding-top: var(--space-6);
}

.live-create__eyebrow,
.live-create__section-label {
  color: var(--color-live);
  font-size: 13px;
  font-weight: var(--font-weight-bold);
  line-height: 18px;
}

.live-create__header h1 {
  color: var(--color-text-primary);
  font-size: 36px;
  font-weight: var(--font-weight-extrabold);
  line-height: 48px;
}

.live-create__header p:last-child,
.live-create__panel > p:last-child {
  color: var(--color-text-secondary);
}

.live-create__steps ol {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  list-style: none;
}

.live-create__steps li {
  position: relative;
  display: flex;
  align-items: center;
  flex-direction: column;
  min-width: 0;
  gap: var(--space-2);
  color: var(--color-text-secondary);
  text-align: center;
}

.live-create__steps li:not(:last-child)::after {
  position: absolute;
  top: 15px;
  left: calc(50% + 22px);
  width: calc(100% - 44px);
  height: 2px;
  background: var(--color-border-strong);
  content: '';
}

.live-create__step--complete:not(:last-child)::after {
  background: var(--color-live);
}

.live-create__steps span {
  position: relative;
  z-index: 1;
  display: grid;
  width: 32px;
  height: 32px;
  border: 1px solid var(--color-border-strong);
  border-radius: 50%;
  background: var(--color-surface);
  color: var(--color-text-secondary);
  flex: 0 0 auto;
  font-size: 12px;
  font-weight: var(--font-weight-bold);
  place-items: center;
}

.live-create__steps strong {
  overflow: hidden;
  font-size: 13px;
  font-weight: var(--font-weight-semibold);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.live-create__step--current {
  color: var(--color-text-primary);
}

.live-create__step--current span,
.live-create__step--complete span {
  border-color: var(--color-live);
  background: var(--color-live);
  color: var(--color-text-inverse);
}

.live-create__step--current strong,
.live-create__step--complete strong {
  color: var(--color-text-primary);
}

.live-create__body {
  display: grid;
  align-items: start;
  gap: var(--space-6);
  grid-template-columns: minmax(0, 1fr) 320px;
}

.live-create__panel,
.live-create__summary {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
}

.live-create__panel {
  display: grid;
  gap: var(--space-0);
  min-height: 320px;
  padding: var(--space-8);
}

.live-create__panel h2,
.live-create__summary h2 {
  color: var(--color-text-primary);
  font-size: 24px;
  font-weight: var(--font-weight-extrabold);
  line-height: 32px;
}

.live-create__method-grid {
  display: grid;
  gap: var(--space-4);
  grid-template-columns: repeat(2, minmax(0, 1fr));
  margin-top: var(--space-8);
}

.live-create__method {
  display: grid;
  min-height: 132px;
  align-content: start;
  gap: var(--space-3);
  padding: var(--space-5);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  text-align: left;
}

.live-create__method strong {
  color: var(--color-text-primary);
  font-size: 18px;
  line-height: 26px;
}

.live-create__method--selected {
  border-color: var(--color-live);
  box-shadow: 0 0 0 3px var(--color-auction-soft);
}

.live-create__actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
}

.live-create__button {
  flex: 1;
  min-width: 96px;
  height: var(--button-height-standard);
  padding: 0 var(--space-5);
  border-radius: var(--radius-control);
  font-weight: var(--font-weight-bold);
}

.live-create__button--secondary {
  border: 1px solid var(--color-border-strong);
  background: var(--color-surface);
  color: var(--color-text-primary);
}

.live-create__button--primary {
  border: 1px solid var(--color-primary);
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

.live-create__button:hover:not(:disabled) {
  transform: translateY(-1px);
}

.live-create__button:disabled {
  border-color: var(--color-border);
  background: var(--color-surface-secondary);
  color: var(--color-text-muted);
}

.live-create__side {
  display: grid;
  gap: var(--space-4);
}

.live-create__summary {
  display: grid;
  gap: var(--space-6);
  padding: var(--space-6);
}

.live-create__summary dl {
  display: grid;
  gap: var(--space-3);
}

.live-create__summary dl div {
  display: flex;
  justify-content: space-between;
  gap: var(--space-4);
}

.live-create__summary dt {
  color: var(--color-text-muted);
  font-size: 13px;
}

.live-create__summary dd {
  color: var(--color-text-primary);
  font-weight: var(--font-weight-bold);
}

.live-create__products {
  display: grid;
  gap: var(--space-3);
}

.live-create__products h3 {
  font-size: 15px;
  font-weight: var(--font-weight-bold);
}

.live-create__products article {
  display: grid;
  align-items: center;
  gap: var(--space-3);
  grid-template-columns: 56px minmax(0, 1fr);
}

.live-create__products img {
  width: 56px;
  height: 56px;
  border-radius: var(--radius-control);
  object-fit: cover;
}

.live-create__products article div {
  display: grid;
  min-width: 0;
  gap: var(--space-1);
}

.live-create__products strong,
.live-create__products span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.live-create__products span {
  color: var(--color-text-secondary);
  font-size: 13px;
}

@media (max-width: 960px) {
  .live-create__steps ol,
  .live-create__body,
  .live-create__method-grid {
    grid-template-columns: 1fr;
  }
}
</style>
