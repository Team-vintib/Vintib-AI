<script setup lang="ts">
import { computed, onBeforeUnmount, reactive, ref } from 'vue'

import {
  LIVE_CREATE_BASE_STEPS,
  LIVE_CREATE_COMPLETE_STEP,
  LIVE_CREATE_DEVICE_STEP,
  LIVE_CREATE_METHOD_OPTIONS,
  LIVE_CREATE_MOCK_PRODUCTS,
  LIVE_CREATE_SCHEDULE_STEP,
} from '@/domains/live/constants/liveCreateMockData'
import type {
  LiveDeviceState,
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
const cameraPreviewElement = ref<HTMLVideoElement | null>(null)
const cameraPreviewStream = ref<MediaStream | null>(null)
const microphonePreviewStream = ref<MediaStream | null>(null)
const deviceState = reactive<LiveDeviceState>({
  camera: 'idle',
  microphone: 'idle',
})

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
const isDeviceTesting = computed(
  () => deviceState.camera === 'testing' || deviceState.microphone === 'testing',
)
const isDeviceReady = computed(
  () => deviceState.camera === 'success' && deviceState.microphone === 'success',
)
const canMoveNext = computed(() => {
  if (currentStep.value.id === 'method') {
    return Boolean(form.mode)
  }

  if (currentStep.value.id === 'device') {
    return isDeviceReady.value
  }

  return true
})
const selectedProductCountLabel = computed(() =>
  form.selectedProductIds.length > 0 ? `${form.selectedProductIds.length}개` : '',
)
const scheduleSummary = computed(() => {
  if (!form.scheduledDate && !form.scheduledTime) {
    return ''
  }

  return [form.scheduledDate, form.scheduledTime].filter(Boolean).join(' ')
})
const filteredProducts = computed(() => {
  const keyword = form.productKeyword.trim().toLowerCase()

  if (!keyword) {
    return LIVE_CREATE_MOCK_PRODUCTS
  }

  return LIVE_CREATE_MOCK_PRODUCTS.filter((product) =>
    [product.name, product.brand, product.category, product.condition].some((value) =>
      value.toLowerCase().includes(keyword),
    ),
  )
})
const selectedProducts = computed(() =>
  LIVE_CREATE_MOCK_PRODUCTS.filter((product) => form.selectedProductIds.includes(product.id)),
)

const selectMode = (mode: LiveCreateMode) => {
  form.mode = mode
}

const isProductSelected = (productId: number) => form.selectedProductIds.includes(productId)

const toggleProductSelection = (productId: number) => {
  if (isProductSelected(productId)) {
    form.selectedProductIds = form.selectedProductIds.filter((selectedId) => selectedId !== productId)
    return
  }

  form.selectedProductIds = [...form.selectedProductIds, productId]
}

const getDeviceStatusLabel = (status: LiveDeviceState[keyof LiveDeviceState]) => {
  if (status === 'testing') {
    return '테스트 중'
  }

  if (status === 'success') {
    return '정상'
  }

  if (status === 'failed') {
    return '확인 실패'
  }

  return '확인 필요'
}

const stopCameraPreview = () => {
  cameraPreviewStream.value?.getTracks().forEach((track) => {
    track.stop()
  })
  cameraPreviewStream.value = null

  microphonePreviewStream.value?.getTracks().forEach((track) => {
    track.stop()
  })
  microphonePreviewStream.value = null

  if (cameraPreviewElement.value) {
    cameraPreviewElement.value.srcObject = null
  }
}

const runDeviceTest = async () => {
  if (isDeviceTesting.value) {
    return
  }

  if (!navigator.mediaDevices?.getUserMedia) {
    deviceState.camera = 'failed'
    deviceState.microphone = 'failed'
    return
  }

  deviceState.camera = 'testing'
  deviceState.microphone = 'idle'

  try {
    stopCameraPreview()

    const cameraStream = await navigator.mediaDevices.getUserMedia({
      video: true,
      audio: false,
    })

    cameraPreviewStream.value = cameraStream

    if (cameraPreviewElement.value) {
      cameraPreviewElement.value.srcObject = cameraStream
    }

    deviceState.camera = cameraStream.getVideoTracks().length > 0 ? 'success' : 'failed'

    if (deviceState.camera !== 'success') {
      return
    }

    deviceState.microphone = 'testing'

    const microphoneStream = await navigator.mediaDevices.getUserMedia({
      video: false,
      audio: true,
    })

    microphonePreviewStream.value = microphoneStream
    deviceState.microphone = microphoneStream.getAudioTracks().length > 0 ? 'success' : 'failed'
  } catch {
    if (deviceState.camera === 'testing') {
      stopCameraPreview()
      deviceState.camera = 'failed'
      deviceState.microphone = 'idle'
      return
    }

    deviceState.microphone = 'failed'
  }
}

const resetDeviceTest = () => {
  stopCameraPreview()
  deviceState.camera = 'idle'
  deviceState.microphone = 'idle'
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

onBeforeUnmount(() => {
  stopCameraPreview()
})
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

          <div
            v-if="currentStep.id === 'method'"
            class="live-create__method-grid"
            aria-label="라이브 유형 선택"
          >
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

          <form
            v-else-if="currentStep.id === 'info'"
            class="live-create__info-form"
            aria-label="방송 정보 입력"
          >
            <label class="live-create__field" for="live-create-title-input">
              <span>방송 제목</span>
              <input
                id="live-create-title-input"
                v-model="form.title"
                type="text"
                maxlength="60"
                placeholder="예: 빈티지 레더 특집 경매"
              />
            </label>

            <label class="live-create__field" for="live-create-description-input">
              <span>한 줄 소개</span>
              <textarea
                id="live-create-description-input"
                v-model="form.description"
                maxlength="120"
                rows="3"
                placeholder="시청자에게 보여질 소개 문구를 입력해 주세요"
              />
            </label>

            <label class="live-create__field" for="live-create-brand-input">
              <span>대표 브랜드</span>
              <input
                id="live-create-brand-input"
                v-model="form.mainBrand"
                type="text"
                maxlength="40"
                placeholder="예: Burberry, Levi's"
              />
            </label>
          </form>

          <section
            v-else-if="currentStep.id === 'products'"
            class="live-create__product-panel"
            aria-label="판매 상품 선택"
          >
            <label class="live-create__field" for="live-create-product-search">
              <span>상품 검색</span>
              <input
                id="live-create-product-search"
                v-model="form.productKeyword"
                class="live-create__product-search-input"
                type="search"
                placeholder="상품명, 브랜드, 카테고리를 검색해 주세요"
              />
            </label>

            <div v-if="filteredProducts.length" class="live-create__product-list">
              <article
                v-for="product in filteredProducts"
                :key="product.id"
                class="live-create__product"
                :class="{ 'live-create__product--selected': isProductSelected(product.id) }"
              >
                <img :src="product.thumbnailUrl" :alt="product.name" />
                <div class="live-create__product-info">
                  <strong>{{ product.name }}</strong>
                  <dl class="live-create__product-meta">
                    <div>
                      <dt>브랜드</dt>
                      <dd>{{ product.brand }}</dd>
                    </div>
                    <div>
                      <dt>카테고리</dt>
                      <dd>{{ product.category }}</dd>
                    </div>
                  </dl>
                  <em>{{ product.price.toLocaleString() }}원</em>
                </div>
                <button type="button" @click="toggleProductSelection(product.id)">
                  {{ isProductSelected(product.id) ? '선택 해제' : '선택' }}
                </button>
              </article>
            </div>

            <div v-else class="live-create__empty" role="status">
              <strong>검색 결과가 없습니다.</strong>
              <p>다른 상품명이나 브랜드로 다시 검색해 주세요.</p>
            </div>
          </section>

          <section
            v-else-if="currentStep.id === 'schedule'"
            class="live-create__schedule-panel"
            aria-label="예약 일정 설정"
          >
            <div class="live-create__schedule-grid">
              <label class="live-create__field" for="live-create-scheduled-date">
                <span>방송 날짜</span>
                <input id="live-create-scheduled-date" v-model="form.scheduledDate" type="date" />
              </label>

              <label class="live-create__field" for="live-create-scheduled-time">
                <span>시작 시간</span>
                <input id="live-create-scheduled-time" v-model="form.scheduledTime" type="time" />
              </label>
            </div>

          </section>

          <section
            v-else-if="currentStep.id === 'device'"
            class="live-create__device-panel"
            aria-label="방송 장비 확인"
          >
            <div class="live-create__camera-preview">
              <video
                ref="cameraPreviewElement"
                autoplay
                muted
                playsinline
                aria-label="카메라 미리보기"
              />
              <div v-if="!cameraPreviewStream" class="live-create__camera-placeholder">
                <strong>카메라 미리보기</strong>
                <p>장비 테스트를 시작하면 현재 카메라 화면이 표시됩니다.</p>
              </div>
            </div>

            <div class="live-create__device-grid">
              <article
                class="live-create__device-card"
                :class="`live-create__device-card--${deviceState.camera}`"
              >
                <div>
                  <strong>카메라</strong>
                  <span>기본 카메라</span>
                </div>
                <em>{{ getDeviceStatusLabel(deviceState.camera) }}</em>
              </article>

              <article
                class="live-create__device-card"
                :class="`live-create__device-card--${deviceState.microphone}`"
              >
                <div>
                  <strong>마이크</strong>
                  <span>기본 마이크</span>
                </div>
                <em>{{ getDeviceStatusLabel(deviceState.microphone) }}</em>
              </article>
            </div>

            <p class="live-create__device-message" role="status">
              <span v-if="deviceState.camera === 'testing'">카메라 화면을 확인하고 있습니다.</span>
              <span v-else-if="deviceState.microphone === 'testing'">마이크 입력을 확인하고 있습니다.</span>
              <span v-else-if="isDeviceReady">장비 확인이 완료되었습니다. 다음 단계로 이동할 수 있습니다.</span>
              <span v-else-if="deviceState.camera === 'failed' || deviceState.microphone === 'failed'">
                장비 권한 또는 연결 상태를 확인한 뒤 다시 시도해 주세요.
              </span>
              <span v-else>방송 시작 전 카메라와 마이크 테스트를 진행해 주세요.</span>
            </p>

            <div class="live-create__device-actions">
              <button
                class="live-create__button live-create__button--primary"
                type="button"
                :disabled="isDeviceTesting"
                @click="runDeviceTest"
              >
                {{ isDeviceReady ? '다시 테스트' : '장비 테스트' }}
              </button>
              <button
                class="live-create__button live-create__button--secondary"
                type="button"
                :disabled="isDeviceTesting"
                @click="resetDeviceTest"
              >
                초기화
              </button>
            </div>
          </section>

          <div v-else class="live-create__placeholder" role="status">
            <strong>{{ currentStep.label }}</strong>
            <p>이 단계의 세부 UI는 다음 작업에서 이어서 구현합니다.</p>
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
                  <dl class="live-create__summary-product-meta">
                    <div>
                      <dt>브랜드</dt>
                      <dd>{{ product.brand }}</dd>
                    </div>
                    <div>
                      <dt>카테고리</dt>
                      <dd>{{ product.category }}</dd>
                    </div>
                  </dl>
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
  align-content: start;
  gap: var(--space-4);
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

.live-create__info-form {
  display: grid;
  gap: var(--space-5);
  margin-top: var(--space-8);
}

.live-create__field {
  display: grid;
  gap: var(--space-2);
}

.live-create__field span {
  color: var(--color-text-primary);
  font-size: 14px;
  font-weight: var(--font-weight-bold);
  line-height: 20px;
}

.live-create__field input,
.live-create__field textarea {
  width: 100%;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-primary);
  font: inherit;
  transition:
    border-color 160ms ease,
    box-shadow 160ms ease;
}

.live-create__field input {
  height: var(--button-height-standard);
  padding: 0 var(--space-4);
}

.live-create__field .live-create__product-search-input {
  height: var(--button-height-small);
}

.live-create__field textarea {
  min-height: 96px;
  padding: var(--space-3) var(--space-4);
  resize: vertical;
}

.live-create__field input::placeholder,
.live-create__field textarea::placeholder {
  color: var(--color-text-muted);
}

.live-create__field input:focus,
.live-create__field textarea:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
  outline: none;
}

.live-create__schedule-panel {
  display: grid;
  gap: var(--space-5);
  margin-top: var(--space-8);
}

.live-create__schedule-grid {
  display: grid;
  gap: var(--space-5);
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.live-create__device-panel {
  display: grid;
  gap: var(--space-5);
  margin-top: var(--space-8);
}

.live-create__camera-preview {
  position: relative;
  overflow: hidden;
  min-height: 300px;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-control);
  background: var(--color-live-background);
}

.live-create__camera-preview video {
  width: 100%;
  height: 100%;
  min-height: 300px;
  object-fit: cover;
  transform: scaleX(-1);
}

.live-create__camera-placeholder {
  position: absolute;
  inset: 0;
  display: grid;
  gap: var(--space-2);
  place-content: center;
  padding: var(--space-6);
  color: var(--color-live-text-secondary);
  text-align: center;
}

.live-create__camera-placeholder strong {
  color: var(--color-live-text-primary);
  font-size: 18px;
  font-weight: var(--font-weight-bold);
}

.live-create__camera-placeholder p {
  max-width: 320px;
  line-height: var(--line-height-body);
}

.live-create__device-grid {
  display: grid;
  gap: var(--space-4);
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.live-create__device-card {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
  min-height: 116px;
  padding: var(--space-5);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-control);
  background: var(--color-surface);
}

.live-create__device-card div {
  display: grid;
  gap: var(--space-2);
}

.live-create__device-card strong {
  color: var(--color-text-primary);
  font-size: 18px;
  font-weight: var(--font-weight-bold);
  line-height: 26px;
}

.live-create__device-card span {
  color: var(--color-text-secondary);
  font-size: 14px;
  line-height: 20px;
}

.live-create__device-card em {
  flex: 0 0 auto;
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-badge);
  background: var(--color-surface-secondary);
  color: var(--color-text-secondary);
  font-size: 12px;
  font-style: normal;
  font-weight: var(--font-weight-bold);
  line-height: 16px;
}

.live-create__device-card--testing {
  border-color: var(--color-timer);
}

.live-create__device-card--testing em {
  background: var(--color-surface-secondary);
  color: var(--color-timer);
}

.live-create__device-card--success {
  border-color: var(--color-primary);
}

.live-create__device-card--success em {
  background: var(--color-primary-soft);
  color: var(--color-primary);
}

.live-create__device-card--failed {
  border-color: var(--color-error);
}

.live-create__device-card--failed em {
  background: var(--color-error-soft);
  color: var(--color-error);
}

.live-create__device-message {
  min-height: 24px;
  color: var(--color-text-secondary);
  line-height: var(--line-height-body);
}

.live-create__device-actions {
  display: flex;
  gap: var(--space-3);
}

.live-create__product-panel {
  display: grid;
  gap: var(--space-5);
  margin-top: var(--space-8);
}

.live-create__product-list {
  display: grid;
  gap: var(--space-4);
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.live-create__product {
  display: grid;
  overflow: hidden;
  gap: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
}

.live-create__product--selected {
  border-color: var(--color-live);
  box-shadow: 0 0 0 3px var(--color-auction-soft);
}

.live-create__product img {
  width: 100%;
  aspect-ratio: 4 / 3;
  object-fit: cover;
}

.live-create__product-info {
  display: grid;
  min-width: 0;
  gap: var(--space-1);
  padding: 0 var(--space-4);
}

.live-create__product-info strong,
.live-create__product-info em {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.live-create__product-info strong {
  color: var(--color-text-primary);
  font-size: 15px;
  font-style: normal;
  font-weight: var(--font-weight-bold);
}

.live-create__product-info em {
  color: var(--color-text-primary);
  font-size: 13px;
  font-style: normal;
  font-weight: var(--font-weight-bold);
}

.live-create__product-meta,
.live-create__summary-product-meta {
  display: grid;
  gap: var(--space-1);
}

.live-create__product-meta div,
.live-create__summary-product-meta div {
  display: flex;
  align-items: center;
  min-width: 0;
  gap: var(--space-2);
}

.live-create__product-meta dt,
.live-create__summary-product-meta dt {
  flex: 0 0 auto;
  color: var(--color-text-muted);
  font-size: 12px;
  font-weight: var(--font-weight-semibold);
  line-height: 16px;
}

.live-create__product-meta dd,
.live-create__summary-product-meta dd {
  overflow: hidden;
  color: var(--color-text-secondary);
  font-size: 13px;
  line-height: 18px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.live-create__product button {
  width: calc(100% - var(--space-8));
  height: var(--button-height-small);
  margin: 0 var(--space-4) var(--space-4);
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-size: 13px;
  font-weight: var(--font-weight-bold);
}

.live-create__product--selected button {
  border-color: var(--color-live);
  background: var(--color-auction-soft);
  color: var(--color-live);
}

.live-create__empty {
  display: grid;
  gap: var(--space-2);
  min-height: 160px;
  place-content: center;
  padding: var(--space-6);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface-secondary);
  color: var(--color-text-secondary);
  text-align: center;
}

.live-create__empty strong {
  color: var(--color-text-primary);
}

.live-create__placeholder {
  display: grid;
  gap: var(--space-2);
  margin-top: var(--space-8);
  padding: var(--space-6);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface-secondary);
  color: var(--color-text-secondary);
}

.live-create__placeholder strong {
  color: var(--color-text-primary);
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

.live-create__products strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 960px) {
  .live-create__steps ol,
  .live-create__body,
  .live-create__method-grid {
    grid-template-columns: 1fr;
  }

  .live-create__product-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .live-create__schedule-grid {
    grid-template-columns: 1fr;
  }

  .live-create__device-grid {
    grid-template-columns: 1fr;
  }

  .live-create__device-actions {
    flex-direction: column;
  }
}

@media (max-width: 640px) {
  .live-create__product-list {
    grid-template-columns: 1fr;
  }
}
</style>
