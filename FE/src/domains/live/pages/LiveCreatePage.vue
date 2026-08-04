<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'

import {
  createLiveNow,
  getLiveCreateProducts,
  scheduleLive,
  uploadLiveThumbnail,
} from '@/domains/live/api/liveCreateApi'
import {
  LIVE_CREATE_BASE_STEPS,
  LIVE_CREATE_COMPLETE_STEP,
  LIVE_CREATE_DEVICE_STEP,
  LIVE_CREATE_METHOD_OPTIONS,
  LIVE_CREATE_SCHEDULE_STEP,
  LIVE_CREATE_VALIDATION_MESSAGES,
} from '@/domains/live/constants/liveCreateMockData'
import { useAuthStore } from '@/domains/auth/stores/authStore'
import type {
  LiveDeviceState,
  LiveCreateFormState,
  LiveCreateMode,
  LiveCreateProduct,
  LiveCreateStep,
} from '@/domains/live/types/liveCreate.types'
import { readImageFileAsDataUrl } from '@/shared/api/mockProfileMediaStorage'
import { ROUTE_NAMES, ROUTE_PATHS } from '@/shared/constants/routes'
import DefaultLayout from '@/shared/layouts/DefaultLayout.vue'
import fallbackProductThumbnail from '@/assets/images/products/product-denim-jacket.webp'

type LiveCreateField = 'mode' | 'title' | 'description' | 'mainBrand' | 'products' | 'scheduledDate' | 'scheduledTime'

const authStore = useAuthStore()
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
const createdLiveId = ref<number | null>(null)
const isSubmittingLive = ref(false)
const isLoadingProducts = ref(false)
const submitError = ref('')
const productLoadError = ref('')
const thumbnailInput = ref<HTMLInputElement | null>(null)
const thumbnailFile = ref<File | null>(null)
const thumbnailPreviewUrl = ref('')
const thumbnailFileName = ref('')
const thumbnailError = ref('')
const liveCreateProducts = ref<LiveCreateProduct[]>([])
const cameraPreviewElement = ref<HTMLVideoElement | null>(null)
const cameraPreviewStream = ref<MediaStream | null>(null)
const microphonePreviewStream = ref<MediaStream | null>(null)
const deviceState = reactive<LiveDeviceState>({
  camera: 'idle',
  microphone: 'idle',
})
const touched = reactive<Record<LiveCreateField, boolean>>({
  mode: false,
  title: false,
  description: false,
  mainBrand: false,
  products: false,
  scheduledDate: false,
  scheduledTime: false,
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
const completeTitle = computed(() =>
  form.mode === 'IMMEDIATE'
    ? '라이브를 시작할 수 있습니다.'
    : '예약 라이브 정보가 준비되었습니다.',
)
const completeDescription = computed(() =>
  form.mode === 'IMMEDIATE'
    ? ''
    : '입력한 일정과 상품 정보로 예약 라이브를 확인할 수 있습니다.',
)
const completeActionLabel = computed(() =>
  form.mode === 'IMMEDIATE' ? '라이브 시작' : '라이브 목록',
)
const completeActionTo = computed(() =>
  form.mode === 'IMMEDIATE'
    ? { name: ROUTE_NAMES.LIVE_BROADCAST, params: { liveId: createdLiveId.value ?? 'preview' } }
    : ROUTE_PATHS.LIVE_LIST,
)
const isFirstStep = computed(() => currentStepIndex.value === 0)
const isLastStep = computed(() => currentStepIndex.value === liveCreateSteps.value.length - 1)
const isDeviceTesting = computed(
  () => deviceState.camera === 'testing' || deviceState.microphone === 'testing',
)
const isDeviceReady = computed(
  () => deviceState.camera === 'success' && deviceState.microphone === 'success',
)
const isInfoStepValid = computed(
  () => Boolean(form.title.trim()) && Boolean(form.description.trim()) && Boolean(form.mainBrand.trim()),
)
const isProductsStepValid = computed(() => form.selectedProductIds.length > 0)
const scheduledDateTime = computed(() => {
  if (!form.scheduledDate || !form.scheduledTime) {
    return null
  }

  const date = new Date(`${form.scheduledDate}T${form.scheduledTime}`)

  return Number.isNaN(date.getTime()) ? null : date
})
const isScheduleStepValid = computed(() => {
  if (form.mode !== 'SCHEDULED') {
    return true
  }

  return scheduledDateTime.value !== null && scheduledDateTime.value.getTime() > Date.now()
})
const canMoveNext = computed(() => {
  if (currentStep.value.id === 'method') {
    return Boolean(form.mode)
  }

  if (currentStep.value.id === 'info') {
    return isInfoStepValid.value
  }

  if (currentStep.value.id === 'products') {
    return isProductsStepValid.value
  }

  if (currentStep.value.id === 'schedule') {
    return isScheduleStepValid.value
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
    return liveCreateProducts.value
  }

  return liveCreateProducts.value.filter((product) =>
    [product.name, product.brand, product.category, product.condition].some((value) =>
      value.toLowerCase().includes(keyword),
    ),
  )
})
const selectedProducts = computed(() =>
  liveCreateProducts.value.filter((product) => form.selectedProductIds.includes(product.id)),
)
const fieldErrors = computed<Record<LiveCreateField, string>>(() => ({
  mode: touched.mode && !form.mode ? LIVE_CREATE_VALIDATION_MESSAGES.modeRequired : '',
  title:
    touched.title && !form.title.trim() ? LIVE_CREATE_VALIDATION_MESSAGES.titleRequired : '',
  description:
    touched.description && !form.description.trim()
      ? LIVE_CREATE_VALIDATION_MESSAGES.descriptionRequired
      : '',
  mainBrand:
    touched.mainBrand && !form.mainBrand.trim()
      ? LIVE_CREATE_VALIDATION_MESSAGES.mainBrandRequired
      : '',
  products:
    touched.products && form.selectedProductIds.length === 0
      ? LIVE_CREATE_VALIDATION_MESSAGES.productRequired
      : '',
  scheduledDate:
    touched.scheduledDate && !form.scheduledDate
      ? LIVE_CREATE_VALIDATION_MESSAGES.scheduledDateRequired
      : '',
  scheduledTime:
    touched.scheduledTime && !form.scheduledTime
      ? LIVE_CREATE_VALIDATION_MESSAGES.scheduledTimeRequired
      : touched.scheduledTime && scheduledDateTime.value !== null && scheduledDateTime.value.getTime() <= Date.now()
        ? LIVE_CREATE_VALIDATION_MESSAGES.scheduledDateTimePast
        : '',
}))

const selectMode = (mode: LiveCreateMode) => {
  form.mode = mode
  touched.mode = true
}

const isProductSelected = (productId: number) => form.selectedProductIds.includes(productId)

const toggleProductSelection = (productId: number) => {
  touched.products = true

  if (isProductSelected(productId)) {
    form.selectedProductIds = form.selectedProductIds.filter(
      (selectedId) => selectedId !== productId,
    )
    return
  }

  form.selectedProductIds = [...form.selectedProductIds, productId]
}

const markCurrentStepTouched = () => {
  if (currentStep.value.id === 'method') {
    touched.mode = true
    return
  }

  if (currentStep.value.id === 'info') {
    touched.title = true
    touched.description = true
    touched.mainBrand = true
    return
  }

  if (currentStep.value.id === 'products') {
    touched.products = true
    return
  }

  if (currentStep.value.id === 'schedule') {
    touched.scheduledDate = true
    touched.scheduledTime = true
  }
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

const loadLiveCreateProducts = async () => {
  authStore.hydrateSession()

  if (!authStore.user?.id) {
    productLoadError.value = '로그인 사용자 정보를 확인하지 못했습니다. 다시 로그인해 주세요.'
    return
  }

  isLoadingProducts.value = true
  productLoadError.value = ''

  try {
    liveCreateProducts.value = await getLiveCreateProducts(authStore.user.id)
    form.selectedProductIds = form.selectedProductIds.filter((productId) =>
      liveCreateProducts.value.some((product) => product.id === productId),
    )
  } catch (error) {
    productLoadError.value =
      error instanceof Error ? error.message : '라이브에 연결할 상품을 불러오지 못했습니다.'
    liveCreateProducts.value = []
    form.selectedProductIds = []
  } finally {
    isLoadingProducts.value = false
  }
}

const getScheduledAt = () => {
  if (!form.scheduledDate || !form.scheduledTime) {
    return ''
  }

  return `${form.scheduledDate}T${form.scheduledTime}:00`
}

const getLiveThumbnailUrl = () =>
  selectedProducts.value.find((product) => product.thumbnailUrl)?.thumbnailUrl || null

const getProductThumbnail = (thumbnailUrl: string) => thumbnailUrl || fallbackProductThumbnail

const handleProductImageError = (event: Event) => {
  const target = event.target

  if (target instanceof HTMLImageElement) {
    target.onerror = null
    target.src = fallbackProductThumbnail
  }
}

const openThumbnailPicker = () => {
  thumbnailInput.value?.click()
}

const handleThumbnailChange = async (event: Event) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]

  if (!file) {
    return
  }

  if (!file.type.startsWith('image/')) {
    thumbnailError.value = '이미지 파일만 업로드할 수 있습니다.'
    input.value = ''
    return
  }

  if (file.size > 5 * 1024 * 1024) {
    thumbnailError.value = '썸네일 사진은 5MB 이하로 선택해 주세요.'
    input.value = ''
    return
  }

  try {
    thumbnailPreviewUrl.value = await readImageFileAsDataUrl(file, '썸네일 사진을 읽지 못했습니다.')
    thumbnailFile.value = file
    thumbnailFileName.value = file.name
    thumbnailError.value = ''
  } catch (error) {
    thumbnailError.value = error instanceof Error ? error.message : '썸네일 사진을 읽지 못했습니다.'
  }
}

const removeThumbnail = () => {
  thumbnailFile.value = null
  thumbnailPreviewUrl.value = ''
  thumbnailFileName.value = ''
  thumbnailError.value = ''

  if (thumbnailInput.value) {
    thumbnailInput.value.value = ''
  }
}

const resolveThumbnailUrl = async () => {
  if (!thumbnailFile.value || !authStore.user?.id) {
    return getLiveThumbnailUrl()
  }

  try {
    return await uploadLiveThumbnail(authStore.user.id, thumbnailFile.value)
  } catch (error) {
    thumbnailError.value =
      error instanceof Error ? error.message : '썸네일 사진을 업로드하지 못했습니다.'
    return getLiveThumbnailUrl()
  }
}

const submitLiveCreate = async () => {
  if (createdLiveId.value) {
    return true
  }

  isSubmittingLive.value = true
  submitError.value = ''

  try {
    const baseRequest = {
      title: form.title.trim(),
      thumbnailUrl: await resolveThumbnailUrl(),
      productIds: form.selectedProductIds,
    }
    const response =
      form.mode === 'SCHEDULED'
        ? await scheduleLive({
            ...baseRequest,
            scheduledAt: getScheduledAt(),
          })
        : await createLiveNow(baseRequest)

    createdLiveId.value = response.id
    return true
  } catch (error) {
    submitError.value =
      error instanceof Error ? error.message : '라이브를 생성하지 못했습니다.'
    return false
  } finally {
    isSubmittingLive.value = false
  }
}

const moveToPreviousStep = () => {
  if (isFirstStep.value) {
    return
  }

  currentStepIndex.value -= 1
}

const moveToNextStep = async () => {
  markCurrentStepTouched()

  if (isLastStep.value || !canMoveNext.value) {
    return
  }

  if (currentStep.value.id === 'schedule' || currentStep.value.id === 'device') {
    const isSubmitted = await submitLiveCreate()

    if (!isSubmitted) {
      return
    }
  }

  if (currentStep.value.id === 'device') {
    stopCameraPreview()
  }

  currentStepIndex.value += 1
}

onBeforeUnmount(() => {
  stopCameraPreview()
})

onMounted(() => {
  void loadLiveCreateProducts()
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

      <div
        class="live-create__body"
        :class="{ 'live-create__body--complete': currentStep.id === 'complete' }"
      >
        <section class="live-create__panel" :aria-labelledby="`${currentStep.id}-title`">
          <h2 :id="`${currentStep.id}-title`">{{ currentStep.label }}</h2>
          <p>{{ currentStep.description }}</p>

          <template v-if="currentStep.id === 'method'">
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
            <p v-if="fieldErrors.mode" class="live-create__field-error" role="alert">
              {{ fieldErrors.mode }}
            </p>
          </template>

          <form
            v-else-if="currentStep.id === 'info'"
            class="live-create__info-form"
            aria-label="방송 정보 입력"
          >
            <div class="live-create__thumbnail">
              <div class="live-create__thumbnail-preview" aria-hidden="true">
                <img
                  v-if="thumbnailPreviewUrl"
                  :src="thumbnailPreviewUrl"
                  alt="방송 썸네일 미리보기"
                />
                <span v-else>썸네일</span>
              </div>
              <div class="live-create__thumbnail-body">
                <strong>썸네일 사진</strong>
                <p>등록하지 않으면 선택한 상품 사진이 자동으로 쓰입니다.</p>
                <p v-if="thumbnailFileName" class="live-create__thumbnail-file">
                  {{ thumbnailFileName }}
                </p>
                <div class="live-create__thumbnail-actions">
                  <button type="button" @click="openThumbnailPicker">사진 선택</button>
                  <button v-if="thumbnailPreviewUrl" type="button" @click="removeThumbnail">
                    사진 삭제
                  </button>
                </div>
                <span v-if="thumbnailError" class="live-create__field-error" role="alert">
                  {{ thumbnailError }}
                </span>
              </div>
              <input
                ref="thumbnailInput"
                type="file"
                accept="image/jpeg,image/png,image/webp"
                class="live-create__thumbnail-input"
                aria-label="방송 썸네일 사진 선택"
                @change="handleThumbnailChange"
              />
            </div>

            <label class="live-create__field" for="live-create-title-input">
              <span>방송 제목</span>
              <input
                id="live-create-title-input"
                v-model="form.title"
                type="text"
                maxlength="60"
                placeholder="예: 빈티지 레더 특집 경매"
                :aria-invalid="fieldErrors.title ? 'true' : 'false'"
                aria-describedby="live-create-title-error"
                @blur="touched.title = true"
              />
              <span
                v-if="fieldErrors.title"
                id="live-create-title-error"
                class="live-create__field-error"
                role="alert"
              >
                {{ fieldErrors.title }}
              </span>
            </label>

            <label class="live-create__field" for="live-create-description-input">
              <span>한 줄 소개</span>
              <textarea
                id="live-create-description-input"
                v-model="form.description"
                maxlength="120"
                rows="3"
                placeholder="시청자에게 보여질 소개 문구를 입력해 주세요"
                :aria-invalid="fieldErrors.description ? 'true' : 'false'"
                aria-describedby="live-create-description-error"
                @blur="touched.description = true"
              />
              <span
                v-if="fieldErrors.description"
                id="live-create-description-error"
                class="live-create__field-error"
                role="alert"
              >
                {{ fieldErrors.description }}
              </span>
            </label>

            <label class="live-create__field" for="live-create-brand-input">
              <span>대표 브랜드</span>
              <input
                id="live-create-brand-input"
                v-model="form.mainBrand"
                type="text"
                maxlength="40"
                placeholder="예: Burberry, Levi's"
                :aria-invalid="fieldErrors.mainBrand ? 'true' : 'false'"
                aria-describedby="live-create-brand-error"
                @blur="touched.mainBrand = true"
              />
              <span
                v-if="fieldErrors.mainBrand"
                id="live-create-brand-error"
                class="live-create__field-error"
                role="alert"
              >
                {{ fieldErrors.mainBrand }}
              </span>
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

            <div v-if="isLoadingProducts" class="live-create__empty" role="status">
              <strong>상품을 불러오는 중입니다.</strong>
              <p>라이브에 연결할 수 있는 내 판매 상품을 확인하고 있습니다.</p>
            </div>

            <div v-else-if="productLoadError" class="live-create__empty" role="alert">
              <strong>상품을 불러오지 못했습니다.</strong>
              <p>{{ productLoadError }}</p>
              <button type="button" @click="loadLiveCreateProducts">다시 시도</button>
            </div>

            <div v-else-if="filteredProducts.length" class="live-create__product-list">
              <article
                v-for="product in filteredProducts"
                :key="product.id"
                class="live-create__product"
                :class="{ 'live-create__product--selected': isProductSelected(product.id) }"
              >
                <img
                  :src="getProductThumbnail(product.thumbnailUrl)"
                  :alt="product.name"
                  @error="handleProductImageError"
                />
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
              <p>
                {{
                  liveCreateProducts.length
                    ? '다른 상품명이나 브랜드로 다시 검색해 주세요.'
                    : '먼저 판매 상품을 등록하고 판매 상태로 전환해 주세요.'
                }}
              </p>
            </div>

            <p v-if="fieldErrors.products" class="live-create__field-error" role="alert">
              {{ fieldErrors.products }}
            </p>
          </section>

          <section
            v-else-if="currentStep.id === 'schedule'"
            class="live-create__schedule-panel"
            aria-label="예약 일정 설정"
          >
            <div class="live-create__schedule-grid">
              <label class="live-create__field" for="live-create-scheduled-date">
                <span>방송 날짜</span>
                <input
                  id="live-create-scheduled-date"
                  v-model="form.scheduledDate"
                  type="date"
                  :aria-invalid="fieldErrors.scheduledDate ? 'true' : 'false'"
                  aria-describedby="live-create-scheduled-date-error"
                  @blur="touched.scheduledDate = true"
                />
                <span
                  v-if="fieldErrors.scheduledDate"
                  id="live-create-scheduled-date-error"
                  class="live-create__field-error"
                  role="alert"
                >
                  {{ fieldErrors.scheduledDate }}
                </span>
              </label>

              <label class="live-create__field" for="live-create-scheduled-time">
                <span>시작 시간</span>
                <input
                  id="live-create-scheduled-time"
                  v-model="form.scheduledTime"
                  type="time"
                  :aria-invalid="fieldErrors.scheduledTime ? 'true' : 'false'"
                  aria-describedby="live-create-scheduled-time-error"
                  @blur="touched.scheduledTime = true"
                />
                <span
                  v-if="fieldErrors.scheduledTime"
                  id="live-create-scheduled-time-error"
                  class="live-create__field-error"
                  role="alert"
                >
                  {{ fieldErrors.scheduledTime }}
                </span>
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
              <span v-else-if="deviceState.microphone === 'testing'"
                >마이크 입력을 확인하고 있습니다.</span
              >
              <span v-else-if="isDeviceReady">장비 확인이 완료되었습니다. 다음 단계로 이동할 수 있습니다.</span>
              <span
                v-else-if="deviceState.camera === 'failed' || deviceState.microphone === 'failed'"
              >
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

          <section
            v-else-if="currentStep.id === 'complete'"
            class="live-create__complete"
            aria-label="라이브 개설 완료"
          >
            <div class="live-create__complete-icon" aria-hidden="true">✓</div>
            <h3>{{ completeTitle }}</h3>
            <p v-if="completeDescription">{{ completeDescription }}</p>

            <dl class="live-create__complete-list">
              <div>
                <dt>라이브 유형</dt>
                <dd>{{ selectedMethod?.title || '' }}</dd>
              </div>
              <div>
                <dt>방송 제목</dt>
                <dd>{{ form.title.trim() || '제목 미입력' }}</dd>
              </div>
              <div>
                <dt>한 줄 소개</dt>
                <dd>{{ form.description.trim() || '소개 미입력' }}</dd>
              </div>
              <div v-if="form.mode === 'SCHEDULED'">
                <dt>예약 일정</dt>
                <dd>{{ scheduleSummary || '일정 미입력' }}</dd>
              </div>
              <div>
                <dt>선택 상품</dt>
                <dd>{{ selectedProductCountLabel || '선택 없음' }}</dd>
              </div>
            </dl>

            <div v-if="selectedProducts.length" class="live-create__complete-products">
              <h4>판매 상품</h4>
              <div class="live-create__complete-product-list">
                <article v-for="product in selectedProducts" :key="product.id">
                  <img
                    :src="getProductThumbnail(product.thumbnailUrl)"
                    :alt="product.name"
                    @error="handleProductImageError"
                  />
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
            </div>

            <div class="live-create__complete-actions">
              <RouterLink class="live-create__complete-link" :to="completeActionTo">
                {{ completeActionLabel }}
              </RouterLink>
            </div>
          </section>

          <div v-else class="live-create__placeholder" role="status">
            <strong>{{ currentStep.label }}</strong>
            <p>이 단계의 세부 UI는 다음 작업에서 이어서 구현합니다.</p>
          </div>
        </section>

        <aside
          v-if="currentStep.id !== 'complete'"
          class="live-create__side"
          aria-label="방송 정보와 단계 이동"
        >
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
                <img
                  :src="getProductThumbnail(product.thumbnailUrl)"
                  :alt="product.name"
                  @error="handleProductImageError"
                />
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

          <p v-if="submitError" class="live-create__field-error" role="alert">
            {{ submitError }}
          </p>

          <div class="live-create__actions">
            <button
              class="live-create__button live-create__button--secondary"
              type="button"
              :disabled="isFirstStep || isSubmittingLive"
              @click="moveToPreviousStep"
            >
              이전
            </button>
            <button
              class="live-create__button live-create__button--primary"
              type="button"
              :disabled="isLastStep || !canMoveNext || isSubmittingLive"
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

.live-create__body--complete {
  grid-template-columns: 1fr;
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

.live-create__thumbnail {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.live-create__thumbnail-preview {
  display: grid;
  width: 100%;
  aspect-ratio: 16 / 9;
  place-items: center;
  overflow: hidden;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-media);
  background: var(--color-surface-secondary);
  color: var(--color-text-muted);
  font-size: 14px;
  font-weight: var(--font-weight-bold);
}

.live-create__thumbnail-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.live-create__thumbnail-body {
  display: grid;
  gap: var(--space-1);
}

.live-create__thumbnail-body strong {
  color: var(--color-text-primary);
  font-size: 14px;
  font-weight: var(--font-weight-bold);
  line-height: 20px;
}

.live-create__thumbnail-body p {
  color: var(--color-text-secondary);
  font-size: 13px;
  line-height: 20px;
}

.live-create__thumbnail-file {
  color: var(--color-primary) !important;
  font-weight: var(--font-weight-semibold);
}

.live-create__thumbnail-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: var(--space-1);
}

.live-create__thumbnail-actions button {
  height: var(--button-height-small);
  padding: 0 var(--space-4);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-bold);
}

.live-create__thumbnail-actions button:first-child {
  border-color: var(--color-primary);
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

.live-create__thumbnail-input {
  display: none;
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

.live-create__field input[aria-invalid='true'],
.live-create__field textarea[aria-invalid='true'] {
  border-color: var(--color-error);
}

.live-create__field-error {
  color: var(--color-error);
  font-size: 13px;
  line-height: 20px;
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

.live-create__complete {
  display: grid;
  justify-items: center;
  gap: var(--space-5);
  margin-top: var(--space-8);
  padding: var(--space-8);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface-secondary);
  text-align: center;
}

.live-create__complete-icon {
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

.live-create__complete h3 {
  color: var(--color-text-primary);
  font-size: 22px;
  font-weight: var(--font-weight-extrabold);
  line-height: 30px;
}

.live-create__complete p {
  max-width: 520px;
  color: var(--color-text-secondary);
  line-height: var(--line-height-body);
}

.live-create__complete-list {
  display: grid;
  width: 100%;
  max-width: 640px;
  gap: var(--space-3);
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  text-align: left;
}

.live-create__complete-list div {
  display: flex;
  justify-content: space-between;
  gap: var(--space-4);
}

.live-create__complete-list dt {
  color: var(--color-text-muted);
  font-size: 13px;
}

.live-create__complete-list dd {
  color: var(--color-text-primary);
  font-weight: var(--font-weight-bold);
  text-align: right;
}

.live-create__complete-products {
  display: grid;
  width: 100%;
  gap: var(--space-4);
}

.live-create__complete-products h4 {
  color: var(--color-text-primary);
  font-size: 16px;
  font-weight: var(--font-weight-bold);
  line-height: 24px;
}

.live-create__complete-product-list {
  display: grid;
  gap: var(--space-4);
  grid-template-columns: repeat(3, minmax(0, 1fr));
  text-align: left;
}

.live-create__complete-product-list article {
  display: grid;
  overflow: hidden;
  gap: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
}

.live-create__complete-product-list img {
  width: 100%;
  aspect-ratio: 4 / 3;
  object-fit: cover;
}

.live-create__complete-product-list article > div {
  display: grid;
  gap: var(--space-2);
  padding: 0 var(--space-4) var(--space-4);
}

.live-create__complete-product-list strong {
  overflow: hidden;
  color: var(--color-text-primary);
  font-size: 15px;
  font-weight: var(--font-weight-bold);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.live-create__complete-actions {
  display: flex;
  gap: var(--space-3);
}

.live-create__complete-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 128px;
  height: var(--button-height-standard);
  padding: 0 var(--space-5);
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-control);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-weight: var(--font-weight-bold);
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

  .live-create__complete-product-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .live-create__product-list {
    grid-template-columns: 1fr;
  }

  .live-create__complete-product-list {
    grid-template-columns: 1fr;
  }
}
</style>
