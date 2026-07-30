<script setup lang="ts">
import { computed, onBeforeUnmount, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import ProductPhotoUploader from '@/domains/product/components/ProductPhotoUploader.vue'
import {
  PRODUCT_REGISTRATION_CATEGORY_OPTIONS,
  PRODUCT_REGISTRATION_COLOR_OPTIONS,
  PRODUCT_REGISTRATION_SIZE_OPTIONS,
  PRODUCT_REGISTRATION_STEPS,
  PRODUCT_REGISTRATION_VALIDATION_MESSAGES,
} from '@/domains/product/constants/productRegistrationOptions'
import type {
  ProductRegistrationDraft,
  ProductRegistrationPhotoDraft,
  ProductRegistrationPhotoRole,
} from '@/domains/product/types/productRegistration.types'
import { ROUTE_NAMES, ROUTE_PATHS } from '@/shared/constants/routes'
import DefaultLayout from '@/shared/layouts/DefaultLayout.vue'

const PRODUCT_REGISTRATION_MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024

const router = useRouter()
const currentStepIndex = ref(0)
const draftSaveMessage = ref('')
const photoStepTouched = ref(false)
const photoUploadError = ref('')
const basicStepTouched = reactive({
  name: false,
  brand: false,
  color: false,
  categoryId: false,
})
const attributesStepTouched = reactive({
  size: false,
  shoulder: false,
  chest: false,
  sleeve: false,
  length: false,
})

const draft = reactive<ProductRegistrationDraft>({
  photos: [],
  representativePhotoId: '',
  name: '',
  brand: '',
  color: '',
  customColor: '',
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
const frontPhotos = computed(() => draft.photos.filter((photo) => photo.role === 'front'))
const backPhotos = computed(() => draft.photos.filter((photo) => photo.role === 'back'))
const additionalPhotos = computed(() =>
  draft.photos.filter((photo) => photo.role === 'additional'),
)
const frontPhotoCountLabel = computed(() => `(${Math.min(frontPhotos.value.length, 1)}/1)`)
const backPhotoCountLabel = computed(() => `(${Math.min(backPhotos.value.length, 1)}/1)`)
const representativePhoto = computed(
  () => draft.photos.find((photo) => photo.id === draft.representativePhotoId) ?? null,
)
const photoStepErrors = computed(() => ({
  front: photoStepTouched.value && frontPhotos.value.length === 0
    ? PRODUCT_REGISTRATION_VALIDATION_MESSAGES.frontPhotoRequired
    : '',
  back: photoStepTouched.value && backPhotos.value.length === 0
    ? PRODUCT_REGISTRATION_VALIDATION_MESSAGES.backPhotoRequired
    : '',
  representative: photoStepTouched.value && !draft.representativePhotoId
    ? PRODUCT_REGISTRATION_VALIDATION_MESSAGES.representativePhotoRequired
    : '',
}))
const basicStepErrors = computed(() => ({
  name:
    basicStepTouched.name && !draft.name.trim()
      ? PRODUCT_REGISTRATION_VALIDATION_MESSAGES.nameRequired
      : '',
  brand:
    basicStepTouched.brand && !draft.brand.trim()
      ? PRODUCT_REGISTRATION_VALIDATION_MESSAGES.brandRequired
      : '',
  color:
    basicStepTouched.color && !draft.color
      ? PRODUCT_REGISTRATION_VALIDATION_MESSAGES.colorRequired
      : basicStepTouched.color && draft.color === 'etc' && !draft.customColor.trim()
        ? PRODUCT_REGISTRATION_VALIDATION_MESSAGES.customColorRequired
        : '',
  categoryId:
    basicStepTouched.categoryId && !draft.categoryId
      ? PRODUCT_REGISTRATION_VALIDATION_MESSAGES.categoryRequired
      : '',
}))
const normalizeMeasurementValue = (value: string | number) => String(value ?? '').trim()

const isPositiveMeasurement = (value: string | number) => {
  const normalizedValue = normalizeMeasurementValue(value)
  const parsedValue = Number(normalizedValue)

  return normalizedValue !== '' && Number.isFinite(parsedValue) && parsedValue > 0
}

const getMeasurementError = (field: keyof typeof attributesStepTouched, value: string | number) => {
  if (!attributesStepTouched[field]) {
    return ''
  }

  if (!normalizeMeasurementValue(value)) {
    return PRODUCT_REGISTRATION_VALIDATION_MESSAGES.measurementRequired
  }

  return isPositiveMeasurement(value)
    ? ''
    : PRODUCT_REGISTRATION_VALIDATION_MESSAGES.measurementInvalid
}

const attributesStepErrors = computed(() => ({
  size:
    attributesStepTouched.size && !draft.size
      ? PRODUCT_REGISTRATION_VALIDATION_MESSAGES.sizeRequired
      : '',
  shoulder: getMeasurementError('shoulder', draft.measurements.shoulder),
  chest: getMeasurementError('chest', draft.measurements.chest),
  sleeve: getMeasurementError('sleeve', draft.measurements.sleeve),
  length: getMeasurementError('length', draft.measurements.length),
}))
const isPhotoStepValid = computed(
  () =>
    frontPhotos.value.length > 0 &&
    backPhotos.value.length > 0 &&
    Boolean(draft.representativePhotoId),
)
const isBasicStepValid = computed(
  () =>
    Boolean(draft.name.trim()) &&
    Boolean(draft.brand.trim()) &&
    Boolean(draft.color) &&
    (draft.color !== 'etc' || Boolean(draft.customColor.trim())) &&
    Boolean(draft.categoryId),
)
const isAttributesStepValid = computed(
  () =>
    Boolean(draft.size) &&
    isPositiveMeasurement(draft.measurements.shoulder) &&
    isPositiveMeasurement(draft.measurements.chest) &&
    isPositiveMeasurement(draft.measurements.sleeve) &&
    isPositiveMeasurement(draft.measurements.length),
)
const selectedColorLabel = computed(
  () =>
    draft.color === 'etc'
      ? draft.customColor.trim() || '기타'
      :
    PRODUCT_REGISTRATION_COLOR_OPTIONS.find((option) => option.id === draft.color)?.label ||
    draft.color ||
    '미선택',
)
const selectedCategoryLabel = computed(
  () =>
    PRODUCT_REGISTRATION_CATEGORY_OPTIONS.find((option) => option.id === draft.categoryId)?.label ||
    '미선택',
)
const selectedSizeLabel = computed(
  () =>
    PRODUCT_REGISTRATION_SIZE_OPTIONS.find((option) => option.id === draft.size)?.label ||
    '미선택',
)

const canMoveCurrentStepNext = computed(() => {
  if (currentStep.value.id === 'photos') {
    return isPhotoStepValid.value
  }

  if (currentStep.value.id === 'basic') {
    return isBasicStepValid.value
  }

  if (currentStep.value.id === 'attributes') {
    return isAttributesStepValid.value
  }

  return true
})

const revokePhotoPreviewUrl = (photo: ProductRegistrationPhotoDraft) => {
  if (photo.previewUrl) {
    URL.revokeObjectURL(photo.previewUrl)
  }
}

const createPhotoDraft = (
  role: ProductRegistrationPhotoRole,
  file: File,
): ProductRegistrationPhotoDraft => ({
  id: `${role}-${Date.now()}-${crypto.randomUUID()}`,
  role,
  file,
  previewUrl: URL.createObjectURL(file),
  fileName: file.name,
  isRepresentative: false,
})

const validateImageFile = (file: File) => {
  if (!file.type.startsWith('image/')) {
    return PRODUCT_REGISTRATION_VALIDATION_MESSAGES.imageTypeInvalid
  }

  if (file.size > PRODUCT_REGISTRATION_MAX_IMAGE_SIZE_BYTES) {
    return PRODUCT_REGISTRATION_VALIDATION_MESSAGES.imageSizeInvalid
  }

  return ''
}

const addPhotos = (role: ProductRegistrationPhotoRole, files: File[]) => {
  photoUploadError.value = ''
  photoStepTouched.value = true

  const validPhotos: ProductRegistrationPhotoDraft[] = []

  for (const file of files) {
    const error = validateImageFile(file)

    if (error) {
      photoUploadError.value = error
      continue
    }

    validPhotos.push(createPhotoDraft(role, file))
  }

  if (validPhotos.length === 0) {
    return
  }

  if (role === 'front' || role === 'back') {
    draft.photos
      .filter((photo) => photo.role === role)
      .forEach((photo) => {
        revokePhotoPreviewUrl(photo)
      })

    draft.photos = draft.photos.filter((photo) => photo.role !== role)
    draft.photos.push(validPhotos[0])

    if (draft.representativePhotoId && !draft.photos.some((photo) => photo.id === draft.representativePhotoId)) {
      draft.representativePhotoId = ''
    }

    return
  }

  draft.photos.push(...validPhotos)
}

const removePhoto = (photoId: string) => {
  const photo = draft.photos.find((item) => item.id === photoId)

  if (!photo) {
    return
  }

  revokePhotoPreviewUrl(photo)
  draft.photos = draft.photos.filter((item) => item.id !== photoId)

  if (draft.representativePhotoId === photoId) {
    draft.representativePhotoId = ''
  }
}

const selectRepresentativePhoto = (photoId: string) => {
  draft.representativePhotoId = photoId
  draft.photos = draft.photos.map((photo) => ({
    ...photo,
    isRepresentative: photo.id === photoId,
  }))
}

const markCurrentStepTouched = () => {
  if (currentStep.value.id === 'photos') {
    photoStepTouched.value = true
    return
  }

  if (currentStep.value.id === 'basic') {
    basicStepTouched.name = true
    basicStepTouched.brand = true
    basicStepTouched.color = true
    basicStepTouched.categoryId = true
    return
  }

  if (currentStep.value.id === 'attributes') {
    attributesStepTouched.size = true
    attributesStepTouched.shoulder = true
    attributesStepTouched.chest = true
    attributesStepTouched.sleeve = true
    attributesStepTouched.length = true
  }
}

const moveToPreviousStep = () => {
  if (isFirstStep.value || isCompleteStep.value) {
    return
  }

  currentStepIndex.value -= 1
}

const moveToNextStep = () => {
  markCurrentStepTouched()

  if (isCompleteStep.value) {
    return
  }

  if (!canMoveCurrentStepNext.value) {
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

onBeforeUnmount(() => {
  draft.photos.forEach((photo) => {
    revokePhotoPreviewUrl(photo)
  })
})
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

          <div v-if="currentStep.id === 'photos'" class="product-registration__photo-step">
            <ul class="product-registration__photo-guide">
              <li>대표 이미지를 직접 선택해 주세요.</li>
            </ul>

            <ProductPhotoUploader
              id="product-front-photo"
              title="앞면 이미지 업로드"
              description="옷의 앞면이 잘 보이는 사진을 등록해 주세요."
              :requirement-label="frontPhotoCountLabel"
              :requirement-met="frontPhotos.length > 0"
              role="front"
              :photos="frontPhotos"
              :representative-photo-id="draft.representativePhotoId"
              :error="photoStepErrors.front"
              @upload="addPhotos"
              @remove="removePhoto"
              @select-representative="selectRepresentativePhoto"
            />

            <ProductPhotoUploader
              id="product-back-photo"
              title="뒷면 이미지 업로드"
              description="옷의 뒷면이 잘 보이는 사진을 등록해 주세요."
              :requirement-label="backPhotoCountLabel"
              :requirement-met="backPhotos.length > 0"
              role="back"
              :photos="backPhotos"
              :representative-photo-id="draft.representativePhotoId"
              :error="photoStepErrors.back"
              @upload="addPhotos"
              @remove="removePhoto"
              @select-representative="selectRepresentativePhoto"
            />

            <ProductPhotoUploader
              id="product-additional-photo"
              title="추가 사진"
              description="디테일, 라벨, 착용감이 드러나는 사진을 더 등록할 수 있습니다."
              role="additional"
              multiple
              :photos="additionalPhotos"
              :representative-photo-id="draft.representativePhotoId"
              @upload="addPhotos"
              @remove="removePhoto"
              @select-representative="selectRepresentativePhoto"
            />

            <p v-if="photoStepErrors.representative" class="product-registration__field-error" role="alert">
              {{ photoStepErrors.representative }}
            </p>
            <p v-if="photoUploadError" class="product-registration__field-error" role="alert">
              {{ photoUploadError }}
            </p>
          </div>

          <form
            v-else-if="currentStep.id === 'basic'"
            class="product-registration__form"
            aria-label="상품 기본 정보 입력"
          >
            <label class="product-registration__field" for="product-registration-name">
              <span>상품명</span>
              <input
                id="product-registration-name"
                v-model="draft.name"
                type="text"
                maxlength="60"
                placeholder="예: 90s 오버핏 데님 재킷"
                :aria-invalid="basicStepErrors.name ? 'true' : 'false'"
                aria-describedby="product-registration-name-error"
                @blur="basicStepTouched.name = true"
              />
              <span
                v-if="basicStepErrors.name"
                id="product-registration-name-error"
                class="product-registration__field-error"
                role="alert"
              >
                {{ basicStepErrors.name }}
              </span>
            </label>

            <label class="product-registration__field" for="product-registration-brand">
              <span>브랜드</span>
              <input
                id="product-registration-brand"
                v-model="draft.brand"
                type="text"
                maxlength="40"
                placeholder="예: Levi's, Burberry"
                :aria-invalid="basicStepErrors.brand ? 'true' : 'false'"
                aria-describedby="product-registration-brand-error"
                @blur="basicStepTouched.brand = true"
              />
              <span
                v-if="basicStepErrors.brand"
                id="product-registration-brand-error"
                class="product-registration__field-error"
                role="alert"
              >
                {{ basicStepErrors.brand }}
              </span>
            </label>

            <div class="product-registration__form-grid">
              <label class="product-registration__field" for="product-registration-color">
                <span>색상</span>
                <select
                  id="product-registration-color"
                  v-model="draft.color"
                  :aria-invalid="basicStepErrors.color ? 'true' : 'false'"
                  aria-describedby="product-registration-color-error"
                  @blur="basicStepTouched.color = true"
                >
                  <option value="">색상 선택</option>
                  <option
                    v-for="option in PRODUCT_REGISTRATION_COLOR_OPTIONS"
                    :key="option.id"
                    :value="option.id"
                  >
                    {{ option.label }}
                  </option>
                </select>
                <span
                  v-if="basicStepErrors.color"
                  id="product-registration-color-error"
                  class="product-registration__field-error"
                  role="alert"
                >
                  {{ basicStepErrors.color }}
                </span>
              </label>

              <label class="product-registration__field" for="product-registration-category">
                <span>카테고리</span>
                <select
                  id="product-registration-category"
                  v-model="draft.categoryId"
                  :aria-invalid="basicStepErrors.categoryId ? 'true' : 'false'"
                  aria-describedby="product-registration-category-error"
                  @blur="basicStepTouched.categoryId = true"
                >
                  <option value="">카테고리 선택</option>
                  <option
                    v-for="option in PRODUCT_REGISTRATION_CATEGORY_OPTIONS"
                    :key="option.id"
                    :value="option.id"
                  >
                    {{ option.label }}
                  </option>
                </select>
                <span
                  v-if="basicStepErrors.categoryId"
                  id="product-registration-category-error"
                  class="product-registration__field-error"
                  role="alert"
                >
                  {{ basicStepErrors.categoryId }}
                </span>
              </label>
            </div>

            <label
              v-if="draft.color === 'etc'"
              class="product-registration__field"
              for="product-registration-custom-color"
            >
              <span>기타 색상</span>
              <input
                id="product-registration-custom-color"
                v-model="draft.customColor"
                type="text"
                maxlength="30"
                placeholder="색상을 직접 입력해 주세요"
                :aria-invalid="basicStepErrors.color ? 'true' : 'false'"
                aria-describedby="product-registration-color-error"
                @blur="basicStepTouched.color = true"
              />
            </label>

            <label class="product-registration__field" for="product-registration-description">
              <span>상품 설명</span>
              <textarea
                id="product-registration-description"
                v-model="draft.description"
                maxlength="500"
                rows="4"
                placeholder="상품의 특징, 착용감, 구매자에게 알리고 싶은 내용을 입력해 주세요."
              />
            </label>

            <div class="product-registration__form-grid">
              <label class="product-registration__field" for="product-registration-purchased-at">
                <span>구매 시기</span>
                <input
                  id="product-registration-purchased-at"
                  v-model="draft.purchasedAt"
                  type="text"
                  maxlength="40"
                  placeholder="예: 1990년대, 2005년"
                />
              </label>

              <label class="product-registration__field" for="product-registration-purchased-country">
                <span>구매 국가</span>
                <input
                  id="product-registration-purchased-country"
                  v-model="draft.purchasedCountry"
                  type="text"
                  maxlength="40"
                  placeholder="예: 미국, 일본, 영국"
                />
              </label>
            </div>
          </form>

          <form
            v-else-if="currentStep.id === 'attributes'"
            class="product-registration__form"
            aria-label="상품 사이즈와 소재 입력"
          >
            <div class="product-registration__form-grid">
              <label class="product-registration__field" for="product-registration-size">
                <span>사이즈</span>
                <select
                  id="product-registration-size"
                  v-model="draft.size"
                  :aria-invalid="attributesStepErrors.size ? 'true' : 'false'"
                  aria-describedby="product-registration-size-error"
                  @blur="attributesStepTouched.size = true"
                >
                  <option value="">사이즈 선택</option>
                  <option
                    v-for="option in PRODUCT_REGISTRATION_SIZE_OPTIONS"
                    :key="option.id"
                    :value="option.id"
                  >
                    {{ option.label }}
                  </option>
                </select>
                <span
                  v-if="attributesStepErrors.size"
                  id="product-registration-size-error"
                  class="product-registration__field-error"
                  role="alert"
                >
                  {{ attributesStepErrors.size }}
                </span>
              </label>

              <label class="product-registration__field" for="product-registration-material">
                <span>소재</span>
                <input
                  id="product-registration-material"
                  v-model="draft.material"
                  type="text"
                  maxlength="60"
                  placeholder="예: 면 100%, 울 80%"
                />
              </label>
            </div>

            <fieldset class="product-registration__fieldset">
              <legend>실측 정보</legend>
              <p>cm 기준으로 0보다 큰 숫자를 입력해 주세요.</p>

              <div class="product-registration__form-grid">
                <label class="product-registration__field" for="product-registration-shoulder">
                  <span>어깨</span>
                  <input
                    id="product-registration-shoulder"
                    v-model="draft.measurements.shoulder"
                    type="number"
                    inputmode="decimal"
                    min="0"
                    step="0.1"
                    placeholder="예: 45"
                    :aria-invalid="attributesStepErrors.shoulder ? 'true' : 'false'"
                    aria-describedby="product-registration-shoulder-error"
                    @blur="attributesStepTouched.shoulder = true"
                  />
                  <span
                    v-if="attributesStepErrors.shoulder"
                    id="product-registration-shoulder-error"
                    class="product-registration__field-error"
                    role="alert"
                  >
                    {{ attributesStepErrors.shoulder }}
                  </span>
                </label>

                <label class="product-registration__field" for="product-registration-chest">
                  <span>가슴</span>
                  <input
                    id="product-registration-chest"
                    v-model="draft.measurements.chest"
                    type="number"
                    inputmode="decimal"
                    min="0"
                    step="0.1"
                    placeholder="예: 52"
                    :aria-invalid="attributesStepErrors.chest ? 'true' : 'false'"
                    aria-describedby="product-registration-chest-error"
                    @blur="attributesStepTouched.chest = true"
                  />
                  <span
                    v-if="attributesStepErrors.chest"
                    id="product-registration-chest-error"
                    class="product-registration__field-error"
                    role="alert"
                  >
                    {{ attributesStepErrors.chest }}
                  </span>
                </label>

                <label class="product-registration__field" for="product-registration-sleeve">
                  <span>소매</span>
                  <input
                    id="product-registration-sleeve"
                    v-model="draft.measurements.sleeve"
                    type="number"
                    inputmode="decimal"
                    min="0"
                    step="0.1"
                    placeholder="예: 61"
                    :aria-invalid="attributesStepErrors.sleeve ? 'true' : 'false'"
                    aria-describedby="product-registration-sleeve-error"
                    @blur="attributesStepTouched.sleeve = true"
                  />
                  <span
                    v-if="attributesStepErrors.sleeve"
                    id="product-registration-sleeve-error"
                    class="product-registration__field-error"
                    role="alert"
                  >
                    {{ attributesStepErrors.sleeve }}
                  </span>
                </label>

                <label class="product-registration__field" for="product-registration-length">
                  <span>총장</span>
                  <input
                    id="product-registration-length"
                    v-model="draft.measurements.length"
                    type="number"
                    inputmode="decimal"
                    min="0"
                    step="0.1"
                    placeholder="예: 68"
                    :aria-invalid="attributesStepErrors.length ? 'true' : 'false'"
                    aria-describedby="product-registration-length-error"
                    @blur="attributesStepTouched.length = true"
                  />
                  <span
                    v-if="attributesStepErrors.length"
                    id="product-registration-length-error"
                    class="product-registration__field-error"
                    role="alert"
                  >
                    {{ attributesStepErrors.length }}
                  </span>
                </label>
              </div>
            </fieldset>
          </form>

          <div
            v-else-if="!isCompleteStep"
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
          <h2 id="registration-summary-title">상품 정보</h2>
          <dl>
            <div>
              <dt>대표 이미지</dt>
              <dd>{{ representativePhoto?.fileName || '미선택' }}</dd>
            </div>
            <div>
              <dt>사진</dt>
              <dd>{{ draft.photos.length }}장</dd>
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
              <dt>색상</dt>
              <dd>{{ selectedColorLabel }}</dd>
            </div>
            <div>
              <dt>카테고리</dt>
              <dd>{{ selectedCategoryLabel }}</dd>
            </div>
            <div>
              <dt>사이즈</dt>
              <dd>{{ selectedSizeLabel }}</dd>
            </div>
            <div>
              <dt>소재</dt>
              <dd>{{ draft.material || '미입력' }}</dd>
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

.product-registration__photo-step {
  display: grid;
  gap: var(--space-5);
  margin-top: var(--space-4);
}

.product-registration__photo-guide {
  padding: var(--space-4);
  border-radius: var(--radius-control);
  background: var(--color-primary-soft);
  color: var(--color-text-primary);
  line-height: var(--line-height-body);
}

.product-registration__field-error {
  color: var(--color-error);
  font-size: 13px;
  line-height: 20px;
}

.product-registration__form {
  display: grid;
  gap: var(--space-5);
  margin-top: var(--space-4);
}

.product-registration__form-grid {
  display: grid;
  gap: var(--space-5);
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.product-registration__field {
  display: grid;
  gap: var(--space-2);
}

.product-registration__field span:first-child {
  color: var(--color-text-primary);
  font-size: 14px;
  font-weight: var(--font-weight-bold);
  line-height: 20px;
}

.product-registration__field input,
.product-registration__field select,
.product-registration__field textarea {
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

.product-registration__field input,
.product-registration__field select {
  height: var(--button-height-standard);
  padding: 0 var(--space-4);
}

.product-registration__field textarea {
  min-height: 112px;
  padding: var(--space-3) var(--space-4);
  resize: vertical;
}

.product-registration__field input::placeholder,
.product-registration__field textarea::placeholder {
  color: var(--color-text-muted);
}

.product-registration__field input:focus,
.product-registration__field select:focus,
.product-registration__field textarea:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
  outline: none;
}

.product-registration__field input[aria-invalid='true'],
.product-registration__field select[aria-invalid='true'],
.product-registration__field textarea[aria-invalid='true'] {
  border-color: var(--color-error);
}

.product-registration__fieldset {
  display: grid;
  gap: var(--space-4);
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
}

.product-registration__fieldset legend {
  padding: 0 var(--space-1);
  color: var(--color-text-primary);
  font-size: 16px;
  font-weight: var(--font-weight-bold);
  line-height: 24px;
}

.product-registration__fieldset > p {
  color: var(--color-text-secondary);
  font-size: 14px;
  line-height: 20px;
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
  flex: 0 0 auto;
  color: var(--color-text-muted);
  font-size: 13px;
  white-space: nowrap;
}

.product-registration__summary dd {
  min-width: 0;
  color: var(--color-text-primary);
  font-weight: var(--font-weight-bold);
  text-align: right;
  overflow-wrap: anywhere;
}

@media (max-width: 960px) {
  .product-registration__steps ol,
  .product-registration__body {
    grid-template-columns: 1fr;
  }

  .product-registration__actions {
    flex-wrap: wrap;
  }

  .product-registration__form-grid {
    grid-template-columns: 1fr;
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
