<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import {
  LIVE_TRY_ON_GENERATION_DELAY_MS,
  LIVE_TRY_ON_MOCK_RESULT,
  LIVE_TRY_ON_REGISTERED_PHOTO_URL,
} from '@/domains/tryon/constants/liveTryOnMockData'
import { useAuthStore } from '@/domains/auth/stores/authStore'
import { getMyTryOnProfile, saveMyTryOnProfile } from '@/domains/tryon/api/tryOnProfileApi'
import {
  createTryOnResult,
  getTryOnResultDetail,
  isTryOnResultApiEnabled,
  saveTryOnResult,
} from '@/domains/tryon/api/tryOnResultApi'
import { normalizeApiError } from '@/shared/api/http'
import AppInlineNotice from '@/shared/components/AppInlineNotice.vue'

import type { LiveWatchProduct } from '@/domains/live/types/liveWatch.types'
import type {
  LiveTryOnMockScenario,
  LiveTryOnPanelState,
} from '@/domains/tryon/types/liveTryOn.types'
import type { TryOnProfile } from '@/domains/tryon/types/tryOnProfile.types'
import type { TryOnResult } from '@/domains/tryon/types/tryOnResult.types'

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

const authStore = useAuthStore()
const fileInputElement = ref<HTMLInputElement | null>(null)
const tryOnProfile = ref<TryOnProfile | null>(null)
const selectedPhotoUrl = ref<string | null>(
  props.mockScenario === 'empty' || authStore.user?.id ? null : LIVE_TRY_ON_REGISTERED_PHOTO_URL,
)
const generationPhotoUrl = ref<string | null>(null)
// 실 API 모드에서 생성이 끝나면 실제 결과(이미지·핏 문구)를 여기 담는다. mock 모드에서도
// 화면 렌더를 하나로 맞추려고 동일하게 채운다.
const generatedResult = ref<TryOnResult | null>(null)
// 실 API 폴링 간격/타임아웃. 워커가 job마다 VLM/FLUX/CatVTON을 순차로 새로 로드하는
// 구조라(6GB급 GPU 전제) 로컬 실측 기준 완료까지 4분 넘게 걸릴 수 있다 — 120s는 너무
// 짧아 완료 직전에 폴링이 멈추는 문제가 있었다(-517 로컬 테스트에서 확인).
const TRYON_POLL_INTERVAL_MS = 5_000
const TRYON_POLL_TIMEOUT_MS = 600_000
const panelState = ref<LiveTryOnPanelState>(
  props.mockScenario === 'empty' || authStore.user?.id ? 'EMPTY' : 'READY',
)
const isProfileLoading = ref(Boolean(authStore.user?.id))
const fileError = ref('')
const isResultSaved = ref(false)
const isSavingResult = ref(false)
const shouldFailNextGeneration = ref(props.mockScenario === 'error')
let previewObjectUrl: string | null = null
let generationTimer: number | null = null
let generationSequence = 0

const displayedSourcePhoto = computed(() => generationPhotoUrl.value ?? selectedPhotoUrl.value)

const clearGenerationTimer = () => {
  generationSequence += 1

  if (generationTimer === null) return

  window.clearTimeout(generationTimer)
  generationTimer = null
}

const preloadImage = (source: string) =>
  new Promise<void>((resolve, reject) => {
    const image = new Image()

    image.onload = () => resolve()
    image.onerror = () => reject(new Error('이미지를 불러오지 못했습니다.'))
    image.src = source

    if (image.complete && image.naturalWidth > 0) {
      resolve()
    }
  })

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
  isSavingResult.value = false
  panelState.value = selectedPhotoUrl.value ? 'READY' : 'EMPTY'
}

const resetMockScenario = (scenario: LiveTryOnMockScenario) => {
  clearGenerationTimer()
  releasePreviewObjectUrl()
  selectedPhotoUrl.value =
    scenario === 'empty'
      ? null
      : (tryOnProfile.value?.bodyPhotoUrl ?? LIVE_TRY_ON_REGISTERED_PHOTO_URL)
  generationPhotoUrl.value = null
  panelState.value = scenario === 'empty' ? 'EMPTY' : 'READY'
  shouldFailNextGeneration.value = scenario === 'error'
  fileError.value = ''
  isResultSaved.value = false
  isSavingResult.value = false
}

const openFilePicker = () => {
  if (panelState.value === 'GENERATING') return

  fileError.value = ''
  fileInputElement.value?.click()
}

const handleFileChange = async (event: Event) => {
  const inputElement = event.currentTarget as HTMLInputElement
  const selectedFile = inputElement.files?.[0]

  inputElement.value = ''

  if (!selectedFile) return

  if (!selectedFile.type.startsWith('image/')) {
    fileError.value = '이미지 파일만 등록할 수 있습니다.'
    return
  }

  const nextPreviewObjectUrl = URL.createObjectURL(selectedFile)

  try {
    await preloadImage(nextPreviewObjectUrl)
  } catch {
    URL.revokeObjectURL(nextPreviewObjectUrl)
    fileError.value = '선택한 이미지를 불러오지 못했습니다.'
    return
  }

  clearGenerationTimer()
  releasePreviewObjectUrl()
  previewObjectUrl = nextPreviewObjectUrl
  selectedPhotoUrl.value = nextPreviewObjectUrl
  generationPhotoUrl.value = null
  panelState.value = 'READY'
  fileError.value = ''
  isResultSaved.value = false
  isSavingResult.value = false

  if (!authStore.user?.id) {
    return
  }

  try {
    const nextProfile = await saveMyTryOnProfile(
      {
        bodyPhoto: selectedFile,
        heightCm: toOptionalString(tryOnProfile.value?.heightCm),
        weightKg: toOptionalString(tryOnProfile.value?.weightKg),
        chest: toOptionalString(tryOnProfile.value?.chest),
        waist: toOptionalString(tryOnProfile.value?.waist),
        hip: toOptionalString(tryOnProfile.value?.hip),
      },
      authStore.user.id,
    )

    tryOnProfile.value = nextProfile
  } catch (error) {
    fileError.value = normalizeApiError(error).message
  }
}

const sleep = (ms: number) => new Promise<void>((resolve) => window.setTimeout(resolve, ms))

// 실 API 모드: job을 접수하고, 완료(SUCCESS/FAILED)될 때까지 폴링한다. BE가 생성과 동시에
// 결과를 저장하므로(TryOnResult가 PENDING으로 바로 만들어짐) mock 모드와 달리 별도
// "저장하기" 단계가 필요 없다 — RESULT 상태에 도달하면 이미 저장이 끝난 상태다.
const startRealGeneration = async (currentGeneration: number) => {
  if (!authStore.user?.id) {
    fileError.value = '로그인 후 이용할 수 있습니다.'
    panelState.value = 'ERROR'
    return
  }

  try {
    const pending = await createTryOnResult(authStore.user.id, props.product.id)
    const deadline = Date.now() + TRYON_POLL_TIMEOUT_MS
    let latest = pending

    while (latest.status === 'PENDING' || latest.status === 'PROCESSING') {
      if (currentGeneration !== generationSequence) return
      if (Date.now() > deadline) {
        if (currentGeneration === generationSequence) {
          fileError.value = '시착 생성이 너무 오래 걸리고 있습니다. 잠시 후 다시 시도해 주세요.'
          panelState.value = 'ERROR'
        }
        return
      }
      await sleep(TRYON_POLL_INTERVAL_MS)
      if (currentGeneration !== generationSequence) return
      latest = await getTryOnResultDetail(authStore.user.id, pending.id)
    }

    if (currentGeneration !== generationSequence) return

    if (latest.status === 'FAILED' || !latest.imageUrl) {
      fileError.value = '시착 이미지를 생성하지 못했습니다.'
      panelState.value = 'ERROR'
      return
    }

    generatedResult.value = latest
    isResultSaved.value = true
    panelState.value = 'RESULT'
  } catch (error) {
    if (currentGeneration === generationSequence) {
      fileError.value = normalizeApiError(error).message
      panelState.value = 'ERROR'
    }
  }
}

const startMockGeneration = (currentGeneration: number) => {
  const shouldFail = shouldFailNextGeneration.value
  shouldFailNextGeneration.value = false

  generationTimer = window.setTimeout(async () => {
    generationTimer = null

    if (shouldFail) {
      if (currentGeneration === generationSequence) {
        panelState.value = 'ERROR'
      }
      return
    }

    try {
      await preloadImage(LIVE_TRY_ON_MOCK_RESULT.imageUrl)
    } catch {
      if (currentGeneration === generationSequence) {
        fileError.value = '시착 결과 이미지를 불러오지 못했습니다.'
        panelState.value = 'ERROR'
      }
      return
    }

    if (currentGeneration === generationSequence) {
      generatedResult.value = {
        id: Date.now(),
        productId: props.product.id,
        imageUrl: LIVE_TRY_ON_MOCK_RESULT.imageUrl,
        createdAt: new Date().toISOString(),
        category: null,
        fitTitle: LIVE_TRY_ON_MOCK_RESULT.fitTitle,
        fitDescription: LIVE_TRY_ON_MOCK_RESULT.fitDescription,
      }
      panelState.value = 'RESULT'
    }
  }, LIVE_TRY_ON_GENERATION_DELAY_MS)
}

const startGeneration = () => {
  if (!selectedPhotoUrl.value || panelState.value === 'GENERATING') return

  clearGenerationTimer()
  const currentGeneration = generationSequence
  generationPhotoUrl.value = selectedPhotoUrl.value
  panelState.value = 'GENERATING'
  fileError.value = ''
  isResultSaved.value = false
  isSavingResult.value = false
  generatedResult.value = null

  if (isTryOnResultApiEnabled()) {
    void startRealGeneration(currentGeneration)
    return
  }

  startMockGeneration(currentGeneration)
}

const saveResult = async () => {
  if (panelState.value !== 'RESULT' || isSavingResult.value || isResultSaved.value) return

  const result: TryOnResult = generatedResult.value ?? {
    id: Date.now(),
    productId: props.product.id,
    imageUrl: LIVE_TRY_ON_MOCK_RESULT.imageUrl,
    createdAt: new Date().toISOString(),
    category: null,
  }

  isSavingResult.value = true
  fileError.value = ''

  try {
    await saveTryOnResult(authStore.user?.id, result)
    isResultSaved.value = true
  } catch (error) {
    fileError.value = normalizeApiError(error).message
  } finally {
    isSavingResult.value = false
  }
}

const loadRegisteredTryOnProfile = async () => {
  if (!authStore.user?.id) {
    isProfileLoading.value = false
    return
  }

  try {
    const profile = await getMyTryOnProfile(authStore.user.id)
    tryOnProfile.value = profile

    if (profile.bodyPhotoUrl) {
      await preloadImage(profile.bodyPhotoUrl)
      clearGenerationTimer()
      releasePreviewObjectUrl()
      selectedPhotoUrl.value = profile.bodyPhotoUrl
      generationPhotoUrl.value = null
      panelState.value = 'READY'
      fileError.value = ''
      isResultSaved.value = false
    } else {
      selectedPhotoUrl.value = null
      panelState.value = 'EMPTY'
    }
  } catch (error) {
    fileError.value = normalizeApiError(error).message
  } finally {
    isProfileLoading.value = false
  }
}

const toOptionalString = (value: number | null | undefined) =>
  value === null || value === undefined ? undefined : String(value)

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

onMounted(() => {
  void loadRegisteredTryOnProfile()
})

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
        v-if="isProfileLoading"
        class="live-try-on-panel__state live-try-on-panel__state--loading"
        aria-live="polite"
      >
        <div class="live-try-on-panel__profile-loading" role="status">
          <span aria-hidden="true"></span>
          <p>등록 사진을 불러오는 중입니다</p>
        </div>
      </section>

      <section
        v-else-if="panelState === 'EMPTY'"
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

        <AppInlineNotice v-if="fileError" class="live-try-on-panel__notice" variant="error">
          {{ fileError }}
        </AppInlineNotice>

        <div class="live-try-on-panel__actions">
          <button
            type="button"
            class="live-try-on-panel__button--secondary"
            @click="openFilePicker"
          >
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

        <AppInlineNotice v-if="fileError" class="live-try-on-panel__notice" variant="error">
          {{ fileError }}
        </AppInlineNotice>

        <div class="live-try-on-panel__actions">
          <button
            type="button"
            class="live-try-on-panel__button--secondary"
            @click="openFilePicker"
          >
            이미지 변경
          </button>
          <button type="button" class="live-try-on-panel__button--primary" @click="startGeneration">
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
          <button type="button" class="live-try-on-panel__button--primary" disabled>생성 중</button>
        </div>
      </section>

      <section
        v-else-if="panelState === 'RESULT'"
        class="live-try-on-panel__state live-try-on-panel__state--result"
        aria-labelledby="live-try-on-result-title"
      >
        <figure class="live-try-on-panel__result-media">
          <img :src="generatedResult?.imageUrl ?? undefined" alt="AI 시착 결과 이미지" />
          <figcaption>AI 시착 결과</figcaption>
        </figure>

        <div class="live-try-on-panel__result-copy">
          <div>
            <h3 id="live-try-on-result-title">AI 시착 결과</h3>
          </div>
          <div v-if="generatedResult?.fitTitle" class="live-try-on-panel__fit">
            <strong>{{ generatedResult.fitTitle }}</strong>
            <p v-if="generatedResult.fitDescription">{{ generatedResult.fitDescription }}</p>
          </div>
          <AppInlineNotice v-if="isResultSaved" class="live-try-on-panel__notice" variant="success">
            시착 결과를 저장했습니다.
          </AppInlineNotice>
          <AppInlineNotice v-if="fileError" class="live-try-on-panel__notice" variant="error">
            {{ fileError }}
          </AppInlineNotice>
        </div>

        <div class="live-try-on-panel__actions">
          <button
            type="button"
            class="live-try-on-panel__button--secondary"
            :disabled="isSavingResult"
            @click="openFilePicker"
          >
            다른 사진 고르기
          </button>
          <button
            type="button"
            class="live-try-on-panel__button--primary"
            :disabled="isSavingResult || isResultSaved"
            @click="saveResult"
          >
            {{ isResultSaved ? '저장 완료' : isSavingResult ? '저장 중' : '저장하기' }}
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
          <button
            type="button"
            class="live-try-on-panel__button--secondary"
            @click="openFilePicker"
          >
            이미지 변경
          </button>
          <button type="button" class="live-try-on-panel__button--primary" @click="startGeneration">
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
  color: var(--color-accent);
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
  border-color: var(--color-accent);
  color: var(--color-accent-hover);
}

.live-try-on-panel__close:focus-visible,
.live-try-on-panel__actions button:focus-visible {
  outline: 1px solid #fff;
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

.live-try-on-panel__profile-loading {
  display: flex;
  min-height: 292px;
  height: 100%;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--color-live-border);
  border-radius: var(--radius-media);
  background: #090c0b;
  color: var(--color-live-text-secondary);
  flex-direction: column;
}

.live-try-on-panel__profile-loading > span {
  width: 34px;
  height: 34px;
  border: 3px solid rgba(255, 255, 255, 0.24);
  border-top-color: var(--color-accent);
  border-radius: 50%;
  animation: live-try-on-spin 800ms linear infinite;
}

.live-try-on-panel__profile-loading p {
  margin-top: var(--space-4);
  font-size: 12px;
  line-height: 18px;
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
  border: 1px solid rgba(242, 240, 237, 0.12);
  border-radius: var(--radius-badge);
  background: rgba(10, 10, 10, 0.78);
  color: var(--color-live-text-secondary);
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 500;
  letter-spacing: 0.12em;
  line-height: 15px;
  text-transform: uppercase;
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
  background: rgba(196, 61, 70, 0.16);
  color: var(--color-accent);
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
  border: 1px solid var(--color-border-input);
  background: transparent;
  color: var(--color-live-text-secondary);
}

.live-try-on-panel__button--secondary:hover:not(:disabled) {
  border-color: var(--color-live-text-primary);
  color: var(--color-live-text-primary);
}

.live-try-on-panel__button--primary {
  border: 1px solid var(--color-accent);
  background: var(--color-accent);
  color: var(--color-primary-strong);
}

.live-try-on-panel__button--primary:hover:not(:disabled) {
  background: var(--color-accent-hover);
  border-color: var(--color-accent-hover);
}

.live-try-on-panel__actions button:disabled {
  cursor: not-allowed;
  border-color: var(--color-live-border);
  background: var(--color-live-surface-raised);
  box-shadow: none;
  color: var(--color-live-text-secondary);
  opacity: 0.72;
}

.live-try-on-panel__notice {
  margin-top: var(--space-3);
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
  border-top-color: var(--color-accent);
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
  border: 1px solid rgba(196, 61, 70, 0.25);
  border-radius: var(--radius-control);
  margin-top: var(--space-4);
  background: rgba(196, 61, 70, 0.1);
}

.live-try-on-panel__fit strong {
  color: var(--color-accent-hover);
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
  .live-try-on-panel__profile-loading > span,
  .live-try-on-panel__processing > span {
    animation: none;
  }
}
</style>
