<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { PRODUCT_REGISTRATION_STEPS } from '@/domains/product/constants/productRegistrationOptions'
import type { ProductRegistrationDraft } from '@/domains/product/types/productRegistration.types'
import { ROUTE_NAMES, ROUTE_PATHS } from '@/shared/constants/routes'
import DefaultLayout from '@/shared/layouts/DefaultLayout.vue'

const router = useRouter()
const currentStepIndex = ref(0)
const draftSaveMessage = ref('')

const draft = reactive<ProductRegistrationDraft>({
  photos: [],
  representativePhotoId: '',
  name: '',
  brand: '',
  color: '',
  categoryId: '',
  description: '',
  purchasedAt: '',
  purchasedCountry: '',
  size: '',
  material: '',
  measurements: {
    shoulder: '',
    chest: '',
    sleeve: '',
    length: '',
  },
  conditionGrade: '',
  hasDefect: null,
  sellerDefectDescription: '',
  aiCheckPhotoIds: [],
  aiPhotoResults: [],
  saleType: '',
  directSalePrice: '',
  auctionStartPrice: '',
  linkedLiveId: '',
})

const currentStep = computed(() => PRODUCT_REGISTRATION_STEPS[currentStepIndex.value])
const isFirstStep = computed(() => currentStepIndex.value === 0)
const isReviewStep = computed(() => currentStep.value.id === 'review')
const isCompleteStep = computed(() => currentStep.value.id === 'complete')
const nextActionLabel = computed(() => (isReviewStep.value ? '등록 완료' : '다음'))
const selectedStepLabel = computed(() => `${currentStepIndex.value + 1}. ${currentStep.value.label}`)

const moveToPreviousStep = () => {
  if (isFirstStep.value || isCompleteStep.value) {
    return
  }

  currentStepIndex.value -= 1
}

const moveToNextStep = () => {
  if (isCompleteStep.value) {
    return
  }

  currentStepIndex.value += 1
}

const saveDraft = () => {
  draftSaveMessage.value = '임시저장은 실제 API 확정 전까지 화면 상태로만 표시합니다.'
}

const cancelRegistration = () => {
  router.push(ROUTE_PATHS.PRODUCT_LIST)
}

const continueRegistration = () => {
  currentStepIndex.value = 0
  draftSaveMessage.value = ''
}

const moveToRegisteredProduct = () => {
  router.push({ name: ROUTE_NAMES.PRODUCT_DETAIL, params: { productId: 'preview' } })
}
</script>

<template>
  <DefaultLayout content-max-width="1120px">
    <section class="product-registration" aria-labelledby="product-registration-title">
      <header class="product-registration__header">
        <span class="product-registration__eyebrow">PROD-001</span>
        <h1 id="product-registration-title">상품 등록</h1>
        <p>사진과 상품 정보를 단계별로 입력해 판매 상품을 등록합니다.</p>
      </header>

      <nav class="product-registration__steps" aria-label="상품 등록 단계">
        <ol>
          <li
            v-for="(step, index) in PRODUCT_REGISTRATION_STEPS"
            :key="step.id"
            :class="{
              'product-registration__step--current': index === currentStepIndex,
              'product-registration__step--complete': index < currentStepIndex,
            }"
            :aria-current="index === currentStepIndex ? 'step' : undefined"
          >
            <span>{{ index + 1 }}</span>
            <strong>{{ step.label }}</strong>
          </li>
        </ol>
      </nav>

      <div class="product-registration__body">
        <section class="product-registration__panel" :aria-labelledby="`${currentStep.id}-title`">
          <h2 :id="`${currentStep.id}-title`">{{ currentStep.label }}</h2>
          <p>{{ currentStep.description }}</p>

          <div
            v-if="!isCompleteStep"
            class="product-registration__placeholder"
            role="status"
          >
            <strong>{{ selectedStepLabel }} 입력 UI를 연결할 영역입니다.</strong>
            <p>현재 작업은 단계 이동, 공통 액션과 화면 골격 연결 범위입니다.</p>
          </div>

          <div v-else class="product-registration__complete" role="status">
            <span class="product-registration__complete-icon" aria-hidden="true">✓</span>
            <h3>상품 등록이 완료되었습니다.</h3>
            <p>실제 등록 API가 확정되면 등록된 상품 ID로 상세 화면에 이동합니다.</p>
            <div class="product-registration__complete-actions">
              <button
                class="product-registration__button product-registration__button--primary"
                type="button"
                @click="moveToRegisteredProduct"
              >
                상품 보기
              </button>
              <button
                class="product-registration__button product-registration__button--secondary"
                type="button"
                @click="continueRegistration"
              >
                계속 등록
              </button>
            </div>
          </div>

          <p v-if="draftSaveMessage" class="product-registration__notice" role="status">
            {{ draftSaveMessage }}
          </p>

          <div v-if="!isCompleteStep" class="product-registration__actions">
            <button
              class="product-registration__button product-registration__button--ghost"
              type="button"
              @click="cancelRegistration"
            >
              취소
            </button>
            <button
              class="product-registration__button product-registration__button--secondary"
              type="button"
              @click="saveDraft"
            >
              임시저장
            </button>
            <button
              class="product-registration__button product-registration__button--secondary"
              type="button"
              :disabled="isFirstStep"
              @click="moveToPreviousStep"
            >
              이전
            </button>
            <button
              class="product-registration__button product-registration__button--primary"
              type="button"
              @click="moveToNextStep"
            >
              {{ nextActionLabel }}
            </button>
          </div>
        </section>

        <aside class="product-registration__summary" aria-labelledby="registration-summary-title">
          <h2 id="registration-summary-title">등록 요약</h2>
          <dl>
            <div>
              <dt>대표 이미지</dt>
              <dd>{{ draft.representativePhotoId ? '선택됨' : '미선택' }}</dd>
            </div>
            <div>
              <dt>상품명</dt>
              <dd>{{ draft.name || '미입력' }}</dd>
            </div>
            <div>
              <dt>브랜드</dt>
              <dd>{{ draft.brand || '미입력' }}</dd>
            </div>
            <div>
              <dt>판매 방식</dt>
              <dd>{{ draft.saleType || '미선택' }}</dd>
            </div>
          </dl>
        </aside>
      </div>
    </section>
  </DefaultLayout>
</template>

<style scoped lang="scss">
.product-registration {
  display: grid;
  gap: var(--space-8);
  padding-bottom: var(--space-16);
}

.product-registration__header {
  display: grid;
  gap: var(--space-2);
  padding-top: var(--space-6);
}

.product-registration__eyebrow {
  color: var(--color-primary);
  font-size: 13px;
  font-weight: var(--font-weight-bold);
  line-height: 18px;
}

.product-registration__header h1 {
  color: var(--color-text-primary);
  font-size: 36px;
  font-weight: var(--font-weight-extrabold);
  line-height: 48px;
}

.product-registration__header p,
.product-registration__panel > p {
  color: var(--color-text-secondary);
}

.product-registration__steps ol {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  list-style: none;
}

.product-registration__steps li {
  position: relative;
  display: flex;
  align-items: center;
  flex-direction: column;
  min-width: 0;
  gap: var(--space-2);
  color: var(--color-text-secondary);
  text-align: center;
}

.product-registration__steps li:not(:last-child)::after {
  position: absolute;
  top: 15px;
  left: calc(50% + 22px);
  width: calc(100% - 44px);
  height: 2px;
  background: var(--color-border-strong);
  content: '';
}

.product-registration__step--complete:not(:last-child)::after {
  background: var(--color-primary);
}

.product-registration__steps span {
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

.product-registration__steps strong {
  overflow: hidden;
  font-size: 13px;
  font-weight: var(--font-weight-semibold);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.product-registration__step--current span,
.product-registration__step--complete span {
  border-color: var(--color-primary);
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

.product-registration__step--current strong,
.product-registration__step--complete strong {
  color: var(--color-text-primary);
}

.product-registration__body {
  display: grid;
  align-items: start;
  gap: var(--space-6);
  grid-template-columns: minmax(0, 1fr) 320px;
}

.product-registration__panel,
.product-registration__summary {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
}

.product-registration__panel {
  display: grid;
  align-content: start;
  min-height: 320px;
  gap: var(--space-4);
  padding: var(--space-8);
}

.product-registration__panel h2,
.product-registration__summary h2 {
  color: var(--color-text-primary);
  font-size: 24px;
  font-weight: var(--font-weight-extrabold);
  line-height: 32px;
}

.product-registration__placeholder {
  display: grid;
  gap: var(--space-2);
  margin-top: var(--space-4);
  padding: var(--space-6);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface-secondary);
  color: var(--color-text-secondary);
}

.product-registration__placeholder strong {
  color: var(--color-text-primary);
}

.product-registration__complete {
  display: grid;
  justify-items: center;
  gap: var(--space-5);
  margin-top: var(--space-4);
  padding: var(--space-8);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface-secondary);
  text-align: center;
}

.product-registration__complete-icon {
  display: grid;
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-size: 24px;
  font-weight: var(--font-weight-bold);
  place-items: center;
}

.product-registration__complete h3 {
  color: var(--color-text-primary);
  font-size: 22px;
  font-weight: var(--font-weight-extrabold);
  line-height: 30px;
}

.product-registration__complete p {
  max-width: 520px;
  color: var(--color-text-secondary);
  line-height: var(--line-height-body);
}

.product-registration__complete-actions,
.product-registration__actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
}

.product-registration__complete-actions {
  justify-content: center;
}

.product-registration__notice {
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-control);
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-size: 14px;
  font-weight: var(--font-weight-semibold);
  line-height: 20px;
}

.product-registration__button {
  min-width: 104px;
  height: var(--button-height-standard);
  padding: 0 var(--space-5);
  border-radius: var(--radius-control);
  font-weight: var(--font-weight-bold);
}

.product-registration__button--ghost,
.product-registration__button--secondary {
  border: 1px solid var(--color-border-strong);
  background: var(--color-surface);
  color: var(--color-text-primary);
}

.product-registration__button--primary {
  border: 1px solid var(--color-primary);
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

.product-registration__button:disabled {
  border-color: var(--color-border);
  background: var(--color-surface-secondary);
  color: var(--color-text-muted);
}

.product-registration__summary {
  display: grid;
  gap: var(--space-6);
  padding: var(--space-6);
}

.product-registration__summary dl {
  display: grid;
  gap: var(--space-3);
}

.product-registration__summary dl div {
  display: flex;
  justify-content: space-between;
  gap: var(--space-4);
}

.product-registration__summary dt {
  color: var(--color-text-muted);
  font-size: 13px;
}

.product-registration__summary dd {
  color: var(--color-text-primary);
  font-weight: var(--font-weight-bold);
  text-align: right;
}

@media (max-width: 960px) {
  .product-registration__steps ol,
  .product-registration__body {
    grid-template-columns: 1fr;
  }

  .product-registration__actions {
    flex-wrap: wrap;
  }
}

@media (max-width: 640px) {
  .product-registration__button {
    width: 100%;
  }

  .product-registration__complete-actions,
  .product-registration__actions {
    flex-direction: column;
  }
}
</style>
