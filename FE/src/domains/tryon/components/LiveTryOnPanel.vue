<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'

import {
  LIVE_TRY_ON_GENERATION_DELAY_MS,
  LIVE_TRY_ON_MOCK_RESULT,
  LIVE_TRY_ON_REGISTERED_PHOTO_URL,
} from '@/domains/tryon/constants/liveTryOnMockData'

import type { LiveWatchProduct } from '@/domains/live/types/liveWatch.types'
import type {
  LiveTryOnMockScenario,
  LiveTryOnPanelState,
} from '@/domains/tryon/types/liveTryOn.types'

const props = withDefaults(
  defineProps<{
    product: LiveWatchProduct
    mockScenario?: LiveTryOnMockScenario
  }>(),
  {
    mockScenario: 'ready',
  },
)

const emit = defineEmits<{
  close: []
}>()

const fileInputElement = ref<HTMLInputElement | null>(null)
const selectedPhotoUrl = ref<string | null>(
  props.mockScenario === 'empty' ? null : LIVE_TRY_ON_REGISTERED_PHOTO_URL,
)
const generationPhotoUrl = ref<string | null>(null)
const panelState = ref<LiveTryOnPanelState>(
  props.mockScenario === 'empty' ? 'EMPTY' : 'READY',
)
const fileError = ref('')
const isResultSaved = ref(false)
const shouldFailNextGeneration = ref(props.mockScenario === 'error')
let previewObjectUrl: string | null = null
let generationTimer: number | null = null

const displayedSourcePhoto = computed(
  () => generationPhotoUrl.value ?? selectedPhotoUrl.value,
)

const clearGenerationTimer = () => {
  if (generationTimer === null) return

  window.clearTimeout(generationTimer)
  generationTimer = null
}

const releasePreviewObjectUrl = () => {
  if (!previewObjectUrl) return

  URL.revokeObjectURL(previewObjectUrl)
  previewObjectUrl = null
}

const resetResultForCurrentPhoto = () => {
  clearGenerationTimer()
  generationPhotoUrl.value = null
  fileError.value = ''
  isResultSaved.value = false
  panelState.value = selectedPhotoUrl.value ? 'READY' : 'EMPTY'
}

const resetMockScenario = (scenario: LiveTryOnMockScenario) => {
  clearGenerationTimer()
  releasePreviewObjectUrl()
  selectedPhotoUrl.value =
    scenario === 'empty' ? null : LIVE_TRY_ON_REGISTERED_PHOTO_URL
  generationPhotoUrl.value = null
  panelState.value = scenario === 'empty' ? 'EMPTY' : 'READY'
  shouldFailNextGeneration.value = scenario === 'error'
  fileError.value = ''
  isResultSaved.value = false
}

const openFilePicker = () => {
  if (panelState.value === 'GENERATING') return

  fileError.value = ''
  fileInputElement.value?.click()
}

const handleFileChange = (event: Event) => {
  const inputElement = event.currentTarget as HTMLInputElement
  const selectedFile = inputElement.files?.[0]

  inputElement.value = ''

  if (!selectedFile) return

  if (!selectedFile.type.startsWith('image/')) {
    fileError.value = '이미지 파일만 등록할 수 있습니다.'
    return
  }

  clearGenerationTimer()
  releasePreviewObjectUrl()
  previewObjectUrl = URL.createObjectURL(selectedFile)
  selectedPhotoUrl.value = previewObjectUrl
  generationPhotoUrl.value = null
  panelState.value = 'READY'
  fileError.value = ''
  isResultSaved.value = false
}

const startGeneration = () => {
  if (!selectedPhotoUrl.value || panelState.value === 'GENERATING') return

  clearGenerationTimer()
  generationPhotoUrl.value = selectedPhotoUrl.value
  panelState.value = 'GENERATING'
  fileError.value = ''
  isResultSaved.value = false

  const shouldFail = shouldFailNextGeneration.value
  shouldFailNextGeneration.value = false

  generationTimer = window.setTimeout(() => {
    panelState.value = shouldFail ? 'ERROR' : 'RESULT'
    generationTimer = null
  }, LIVE_TRY_ON_GENERATION_DELAY_MS)
}

const saveMockResult = () => {
  if (panelState.value !== 'RESULT') return

  isResultSaved.value = true
}

const returnToReady = () => {
  clearGenerationTimer()
  generationPhotoUrl.value = null
  isResultSaved.value = false
  panelState.value = selectedPhotoUrl.value ? 'READY' : 'EMPTY'
}

watch(
  () => props.product.id,
  () => {
    resetResultForCurrentPhoto()
    shouldFailNextGeneration.value = props.mockScenario === 'error'
  },
)

watch(
  () => props.mockScenario,
  (scenario) => {
    resetMockScenario(scenario)
  },
)

onBeforeUnmount(() => {
  clearGenerationTimer()
  releasePreviewObjectUrl()
})
</script>

<template>
  <aside class="live-try-on-panel" aria-labelledby="live-try-on-title">
    <header class="live-try-on-panel__header">
      <div>
        <h2 id="live-try-on-title">AI 시착</h2>
        <p><span>시착 상품</span><b aria-hidden="true">·</b>{{ product.title }}</p>
      </div>

      <button
        class="live-try-on-panel__close"
        type="button"
        aria-label="AI 시착 패널 닫기"
        @click="emit('close')"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="m6 6 12 12M18 6 6 18" />
        </svg>
      </button>
    </header>

    <div class="live-try-on-panel__body">
      <input
        ref="fileInputElement"
        class="live-try-on-panel__file-input"
        type="file"
        accept="image/*"
        aria-label="AI 시착 전신 이미지 선택"
        @change="handleFileChange"
      />

      <section
        v-if="panelState === 'EMPTY'"
        class="live-try-on-panel__state live-try-on-panel__state--empty"
        aria-labelledby="live-try-on-empty-title"
      >
        <div class="live-try-on-panel__empty-media">
          <span aria-hidden="true">
            <svg viewBox="0 0 24 24">
              <path
                d="M4 5.75A1.75 1.75 0 0 1 5.75 4h12.5A1.75 1.75 0 0 1 20 5.75v12.5A1.75 1.75 0 0 1 18.25 20H5.75A1.75 1.75 0 0 1 4 18.25V5.75Z"
              />
              <path d="m6.5 17 3.2-3.8 2.25 2.35 1.85-2.15L17.5 17" />
              <circle cx="15.75" cy="8.25" r="1.25" />
            </svg>
          </span>
          <h3 id="live-try-on-empty-title">이미지를 등록해 주세요</h3>
          <p>AI 시착에 사용할 정면 전신 이미지 한 장이 필요합니다.</p>
        </div>

        <p v-if="fileError" class="live-try-on-panel__error" role="alert">
          {{ fileError }}
        </p>

        <div class="live-try-on-panel__actions">
          <button type="button" class="live-try-on-panel__button--secondary" @click="openFilePicker">
            이미지 등록
          </button>
          <button type="button" class="live-try-on-panel__button--primary" disabled>
            AI 시착 시작
          </button>
        </div>
      </section>

      <section
        v-else-if="panelState === 'READY'"
        class="live-try-on-panel__state"
        aria-labelledby="live-try-on-ready-title"
      >
        <h3 id="live-try-on-ready-title" class="sr-only">AI 시착 준비 완료</h3>

        <figure class="live-try-on-panel__photo">
          <img
            v-if="selectedPhotoUrl"
            :src="selectedPhotoUrl"
            alt="AI 시착에 사용할 등록 전신 이미지"
          />
          <figcaption>등록 이미지</figcaption>
        </figure>

        <p v-if="fileError" class="live-try-on-panel__error" role="alert">
          {{ fileError }}
        </p>

        <div class="live-try-on-panel__actions">
          <button type="button" class="live-try-on-panel__button--secondary" @click="openFilePicker">
            이미지 변경
          </button>
          <button
            type="button"
            class="live-try-on-panel__button--primary"
            @click="startGeneration"
          >
            AI 시착 시작
          </button>
        </div>
      </section>

      <section
        v-else-if="panelState === 'GENERATING'"
        class="live-try-on-panel__state"
        aria-labelledby="live-try-on-generating-title"
        aria-live="polite"
      >
        <div class="live-try-on-panel__photo live-try-on-panel__photo--processing">
          <img
            v-if="displayedSourcePhoto"
            :src="displayedSourcePhoto"
            alt="AI 시착 생성에 사용 중인 전신 이미지"
          />
          <div class="live-try-on-panel__processing">
            <span aria-hidden="true"></span>
            <h3 id="live-try-on-generating-title">AI 시착 이미지를 생성하고 있습니다</h3>
            <p>라이브를 계속 보면서 잠시만 기다려 주세요.</p>
          </div>
        </div>

        <div class="live-try-on-panel__actions">
          <button type="button" class="live-try-on-panel__button--secondary" disabled>
            이미지 변경
          </button>
          <button type="button" class="live-try-on-panel__button--primary" disabled>
            생성 중
          </button>
        </div>
      </section>

      <section
        v-else-if="panelState === 'RESULT'"
        class="live-try-on-panel__state live-try-on-panel__state--result"
        aria-labelledby="live-try-on-result-title"
      >
        <figure class="live-try-on-panel__result-media">
          <img :src="LIVE_TRY_ON_MOCK_RESULT.imageUrl" alt="AI 시착 mock 결과 이미지" />
          <figcaption>AI 시착 결과</figcaption>
        </figure>

        <div class="live-try-on-panel__result-copy">
          <div>
            <h3 id="live-try-on-result-title">AI 시착 결과</h3>
          </div>
          <div class="live-try-on-panel__fit">
            <strong>{{ LIVE_TRY_ON_MOCK_RESULT.fitTitle }}</strong>
            <p>{{ LIVE_TRY_ON_MOCK_RESULT.fitDescription }}</p>
          </div>
          <p v-if="isResultSaved" class="live-try-on-panel__saved" role="status">
            결과를 저장했습니다. 실제 저장 API는 연결 전입니다.
          </p>
        </div>

        <div class="live-try-on-panel__actions">
          <button
            type="button"
            class="live-try-on-panel__button--secondary"
            @click="returnToReady"
          >
            다시 시착하기
          </button>
          <button
            type="button"
            class="live-try-on-panel__button--primary"
            :disabled="isResultSaved"
            @click="saveMockResult"
          >
            {{ isResultSaved ? '저장 완료' : '결과 저장' }}
          </button>
        </div>
      </section>

      <section
        v-else
        class="live-try-on-panel__state live-try-on-panel__state--failure"
        aria-labelledby="live-try-on-error-title"
      >
        <div class="live-try-on-panel__failure-media">
          <img
            v-if="displayedSourcePhoto"
            :src="displayedSourcePhoto"
            alt="AI 시착 생성에 사용한 전신 이미지"
          />
          <div>
            <span aria-hidden="true">!</span>
            <h3 id="live-try-on-error-title">시착 이미지를 생성하지 못했습니다</h3>
            <p>잠시 후 같은 이미지로 다시 시도해 주세요.</p>
          </div>
        </div>

        <div class="live-try-on-panel__actions">
          <button type="button" class="live-try-on-panel__button--secondary" @click="openFilePicker">
            이미지 변경
          </button>
          <button
            type="button"
            class="live-try-on-panel__button--primary"
            @click="startGeneration"
          >
            다시 시도
          </button>
        </div>
      </section>
    </div>
  </aside>
</template>

<style scoped lang="scss">
.live-try-on-panel {
  display: flex;
  min-width: 0;
  min-height: 0;
  height: 100%;
  overflow: hidden;
  border-left: 1px solid var(--color-live-border);
  background: #111514;
  color: var(--color-live-text-primary);
  flex-direction: column;
}

.live-try-on-panel__header {
  display: flex;
  min-height: 70px;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
  padding: 13px var(--space-4) 12px;
  border-bottom: 1px solid var(--color-live-border);
  background: var(--color-live-surface);
}

.live-try-on-panel__header h2 {
  font-size: 16px;
  font-weight: 750;
  line-height: 22px;
}

.live-try-on-panel__header p {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 5px;
  margin-top: 4px;
  color: var(--color-live-text-secondary);
  font-size: 11px;
  line-height: 17px;
}

.live-try-on-panel__header p span {
  color: #b69ad7;
  font-weight: 700;
  white-space: nowrap;
}

.live-try-on-panel__header p b {
  font-weight: 400;
}

.live-try-on-panel__close {
  display: grid;
  flex: 0 0 auto;
  width: 30px;
  height: 30px;
  padding: 0;
  border: 1px solid var(--color-live-border);
  border-radius: var(--radius-control);
  background: var(--color-live-surface-raised);
  color: var(--color-live-text-secondary);
  place-items: center;
}

.live-try-on-panel__close:hover {
  border-color: #b69ad7;
  color: #d3b9ef;
}

.live-try-on-panel__close:focus-visible,
.live-try-on-panel__actions button:focus-visible {
  outline: 2px solid #fff;
  outline-offset: 2px;
}

.live-try-on-panel__close svg {
  width: 16px;
  height: 16px;
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-width: 1.8;
}

.live-try-on-panel__body {
  min-height: 0;
  box-sizing: border-box;
  padding: var(--space-4);
  overflow-y: auto;
  flex: 1;
}

.live-try-on-panel__file-input {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  overflow: hidden;
  border: 0;
  margin: -1px;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
}

.live-try-on-panel__state {
  display: flex;
  min-height: 100%;
  height: 100%;
  flex-direction: column;
}

.live-try-on-panel__photo,
.live-try-on-panel__result-media,
.live-try-on-panel__failure-media,
.live-try-on-panel__empty-media {
  position: relative;
  min-height: 292px;
  overflow: hidden;
  border: 1px solid var(--color-live-border);
  border-radius: var(--radius-media);
  background: #090c0b;
}

.live-try-on-panel__photo,
.live-try-on-panel__result-media {
  flex: 1;
}

.live-try-on-panel__photo img,
.live-try-on-panel__result-media img,
.live-try-on-panel__failure-media > img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.live-try-on-panel__result-media img {
  object-fit: cover;
}

.live-try-on-panel__photo figcaption,
.live-try-on-panel__result-media figcaption {
  position: absolute;
  top: var(--space-3);
  left: var(--space-3);
  padding: 4px 8px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 999px;
  background: rgba(13, 16, 15, 0.78);
  color: #d3b9ef;
  font-size: 10px;
  font-weight: 700;
  line-height: 15px;
  backdrop-filter: blur(8px);
}

.live-try-on-panel__empty-media {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-6);
  border-style: dashed;
  flex: 1;
  flex-direction: column;
  text-align: center;
}

.live-try-on-panel__empty-media > span {
  display: grid;
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: rgba(126, 87, 194, 0.16);
  color: #b69ad7;
  place-items: center;
}

.live-try-on-panel__empty-media svg {
  width: 30px;
  height: 30px;
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.6;
}

.live-try-on-panel__empty-media h3,
.live-try-on-panel__failure-media h3 {
  margin-top: var(--space-4);
  font-size: 16px;
  line-height: 23px;
}

.live-try-on-panel__empty-media p,
.live-try-on-panel__failure-media p {
  max-width: 300px;
  margin-top: var(--space-1);
  color: var(--color-live-text-secondary);
  font-size: 12px;
  line-height: 18px;
}

.live-try-on-panel__actions {
  display: grid;
  gap: var(--space-3);
  margin-top: var(--space-4);
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.live-try-on-panel__actions button {
  min-width: 0;
  height: 44px;
  padding: 0 var(--space-4);
  border-radius: var(--radius-control);
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
}

.live-try-on-panel__button--secondary {
  border: 1px solid #72539a;
  background: rgba(126, 87, 194, 0.1);
  color: #d3b9ef;
}

.live-try-on-panel__button--secondary:hover:not(:disabled) {
  background: rgba(126, 87, 194, 0.2);
}

.live-try-on-panel__button--primary {
  border: 1px solid #8560b2;
  background: #76539f;
  box-shadow: 0 6px 18px rgba(118, 83, 159, 0.22);
  color: #fff;
}

.live-try-on-panel__button--primary:hover:not(:disabled) {
  background: var(--color-ai);
}

.live-try-on-panel__actions button:disabled {
  cursor: not-allowed;
  border-color: var(--color-live-border);
  background: var(--color-live-surface-raised);
  box-shadow: none;
  color: var(--color-live-text-secondary);
  opacity: 0.72;
}

.live-try-on-panel__error,
.live-try-on-panel__saved {
  padding: 8px 10px;
  border-radius: var(--radius-control);
  margin-top: var(--space-3);
  font-size: 11px;
  line-height: 17px;
}

.live-try-on-panel__error {
  background: rgba(196, 61, 70, 0.14);
  color: #f0a2a8;
}

.live-try-on-panel__saved {
  background: rgba(77, 139, 98, 0.17);
  color: #9bd0ac;
}

.live-try-on-panel__photo--processing::after {
  position: absolute;
  background: rgba(4, 6, 5, 0.58);
  content: '';
  inset: 0;
}

.live-try-on-panel__processing {
  display: flex;
  position: absolute;
  z-index: 1;
  align-items: center;
  justify-content: center;
  padding: var(--space-6);
  text-align: center;
  flex-direction: column;
  inset: 0;
}

.live-try-on-panel__processing > span {
  width: 34px;
  height: 34px;
  border: 3px solid rgba(255, 255, 255, 0.24);
  border-top-color: #c9a8ed;
  border-radius: 50%;
  animation: live-try-on-spin 800ms linear infinite;
}

.live-try-on-panel__processing h3 {
  margin-top: var(--space-4);
  font-size: 15px;
  line-height: 22px;
}

.live-try-on-panel__processing p {
  margin-top: var(--space-1);
  color: var(--color-live-text-secondary);
  font-size: 11px;
  line-height: 17px;
}

.live-try-on-panel__state--result {
  display: flex;
  min-height: 100%;
  gap: var(--space-3);
  flex-direction: column;
}

.live-try-on-panel__result-media {
  min-height: 288px;
  flex: 1;
}

.live-try-on-panel__result-copy {
  min-width: 0;
  flex: 0 0 auto;
}

.live-try-on-panel__result-copy h3 {
  font-size: 15px;
  line-height: 22px;
}

.live-try-on-panel__fit {
  padding: var(--space-3);
  border: 1px solid rgba(126, 87, 194, 0.25);
  border-radius: var(--radius-control);
  margin-top: var(--space-4);
  background: rgba(126, 87, 194, 0.1);
}

.live-try-on-panel__fit strong {
  color: #d3b9ef;
  font-size: 12px;
  line-height: 18px;
}

.live-try-on-panel__fit p {
  margin-top: 4px;
  color: var(--color-live-text-secondary);
  font-size: 11px;
  line-height: 17px;
}

.live-try-on-panel__state--result .live-try-on-panel__actions {
  margin-top: 0;
}

.live-try-on-panel__failure-media {
  flex: 1;
}

.live-try-on-panel__failure-media::after {
  position: absolute;
  background: rgba(5, 7, 6, 0.72);
  content: '';
  inset: 0;
}

.live-try-on-panel__failure-media > div {
  display: flex;
  position: absolute;
  z-index: 1;
  align-items: center;
  justify-content: center;
  padding: var(--space-6);
  text-align: center;
  flex-direction: column;
  inset: 0;
}

.live-try-on-panel__failure-media > div > span {
  display: grid;
  width: 42px;
  height: 42px;
  border: 1px solid rgba(240, 162, 168, 0.45);
  border-radius: 50%;
  background: rgba(196, 61, 70, 0.18);
  color: #f0a2a8;
  font-size: 20px;
  font-weight: 800;
  place-items: center;
}

@keyframes live-try-on-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 1100px) {
  .live-try-on-panel__result-media {
    min-height: 230px;
  }
}

@media (max-width: 720px) {
  .live-try-on-panel {
    border-left: 0;
  }

  .live-try-on-panel__header {
    min-height: 62px;
    padding-top: 9px;
    padding-bottom: 8px;
  }

  .live-try-on-panel__body {
    padding: var(--space-3);
  }

  .live-try-on-panel__photo,
  .live-try-on-panel__result-media,
  .live-try-on-panel__failure-media,
  .live-try-on-panel__empty-media {
    min-height: 170px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .live-try-on-panel__processing > span {
    animation: none;
  }
}
</style>
