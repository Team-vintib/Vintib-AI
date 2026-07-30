<script setup lang="ts">
import { computed, onBeforeUnmount, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import ProductPhotoUploader from '@/domains/product/components/ProductPhotoUploader.vue'
import {
  PRODUCT_REGISTRATION_CATEGORY_OPTIONS,
  PRODUCT_REGISTRATION_COLOR_OPTIONS,
  PRODUCT_REGISTRATION_CONDITION_OPTIONS,
  PRODUCT_REGISTRATION_MEASUREMENT_FIELDS_BY_CATEGORY,
  PRODUCT_REGISTRATION_SALE_TYPE_OPTIONS,
  PRODUCT_REGISTRATION_SIZE_OPTIONS,
  PRODUCT_REGISTRATION_STEPS,
  PRODUCT_REGISTRATION_VALIDATION_MESSAGES,
} from '@/domains/product/constants/productRegistrationOptions'
import type {
  ProductRegistrationDraft,
  ProductRegistrationAiDefectCandidate,
  ProductRegistrationAiPhotoResult,
  ProductRegistrationPriceBucket,
  ProductRegistrationPhotoDraft,
  ProductRegistrationPhotoRole,
  ProductRegistrationRecommendedPrice,
  ProductRegistrationSaleType,
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
  measurements: {} as Record<string, boolean>,
})
const conditionStepTouched = reactive({
  conditionGrade: false,
  hasDefect: false,
  sellerDefectDescription: false,
  aiPhotos: false,
  aiConfirmation: false,
})
const pricingStepTouched = reactive({
  saleType: false,
  directSalePrice: false,
  auctionStartPrice: false,
})
const currentAiResultIndex = ref(0)
const isAdditionalAiPhotoPickerOpen = ref(false)

const priceRecommendationBuckets: ProductRegistrationPriceBucket[] = [
  { id: 'under-30', label: '~3만', productCount: 6 },
  { id: '30-50', label: '3~5만', productCount: 14 },
  { id: '50-70', label: '5~7만', productCount: 24 },
  { id: '70-90', label: '7~9만', productCount: 18 },
  { id: '90-120', label: '9~12만', productCount: 11 },
  { id: 'over-120', label: '12만~', productCount: 5 },
]

const recommendedPrices: ProductRegistrationRecommendedPrice[] = [
  { grade: 'S', label: 'S급', price: 108000 },
  { grade: 'A', label: 'A급', price: 92000 },
  { grade: 'B', label: 'B급', price: 74000 },
  { grade: 'C', label: 'C급', price: 56000 },
]

const auctionLiveOptions = [
  { id: 'live-20260730-1', label: '7월 30일 21:00 빈티지 아우터 라이브' },
  { id: 'live-20260731-1', label: '7월 31일 20:00 데일리 셀렉션 라이브' },
  { id: 'live-20260801-1', label: '8월 1일 19:30 주말 경매 라이브' },
]

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
  measurements: {},
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

const getMeasurementError = (fieldId: string, value: string | number) => {
  if (!attributesStepTouched.measurements[fieldId]) {
    return ''
  }

  if (!normalizeMeasurementValue(value)) {
    return PRODUCT_REGISTRATION_VALIDATION_MESSAGES.measurementRequired
  }

  return isPositiveMeasurement(value)
    ? ''
    : PRODUCT_REGISTRATION_VALIDATION_MESSAGES.measurementInvalid
}

const activeMeasurementFields = computed(
  () => PRODUCT_REGISTRATION_MEASUREMENT_FIELDS_BY_CATEGORY[draft.categoryId] ?? [],
)
const requiresMeasurements = computed(() => activeMeasurementFields.value.length > 0)
const attributesStepErrors = computed(() => ({
  size:
    attributesStepTouched.size && !draft.size
      ? PRODUCT_REGISTRATION_VALIDATION_MESSAGES.sizeRequired
      : '',
  measurements: Object.fromEntries(
    activeMeasurementFields.value.map((field) => [
      field.id,
      getMeasurementError(field.id, draft.measurements[field.id] ?? ''),
    ]),
  ) as Record<string, string>,
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
    activeMeasurementFields.value.every((field) =>
      isPositiveMeasurement(draft.measurements[field.id] ?? ''),
    ),
)
const selectedColorLabel = computed(
  () =>
    draft.color === 'etc'
      ? draft.customColor.trim()
      : PRODUCT_REGISTRATION_COLOR_OPTIONS.find((option) => option.id === draft.color)?.label ||
        draft.color ||
        '',
)
const selectedCategoryLabel = computed(
  () =>
    PRODUCT_REGISTRATION_CATEGORY_OPTIONS.find((option) => option.id === draft.categoryId)?.label ||
    '',
)
const selectedSizeLabel = computed(
  () =>
    PRODUCT_REGISTRATION_SIZE_OPTIONS.find((option) => option.id === draft.size)?.label ||
    '',
)
const measurementSummaryLabel = computed(() => {
  if (!requiresMeasurements.value) {
    return '해당 없음'
  }

  const completedCount = activeMeasurementFields.value.filter((field) =>
    isPositiveMeasurement(draft.measurements[field.id] ?? ''),
  ).length

  return `${completedCount}/${activeMeasurementFields.value.length}개`
})
const selectedConditionLabel = computed(
  () =>
    PRODUCT_REGISTRATION_CONDITION_OPTIONS.find((option) => option.id === draft.conditionGrade)?.label ||
    '',
)
const requiredAiSelectablePhotos = computed(() =>
  draft.photos.filter((photo) => photo.role === 'front' || photo.role === 'back'),
)
const additionalAiSelectablePhotos = computed(() =>
  draft.photos.filter((photo) => photo.role === 'additional'),
)
const selectedAiPhotos = computed(() =>
  draft.photos.filter((photo) => draft.aiCheckPhotoIds.includes(photo.id)),
)
const currentAiResult = computed<ProductRegistrationAiPhotoResult | null>(
  () => draft.aiPhotoResults[currentAiResultIndex.value] ?? null,
)
const currentAiPhoto = computed(() =>
  currentAiResult.value
    ? draft.photos.find((photo) => photo.id === currentAiResult.value?.photoId) ?? null
    : null,
)
const hasRequiredAiPhotos = computed(() => {
  const selectedPhotos = selectedAiPhotos.value

  return (
    selectedPhotos.some((photo) => photo.role === 'front') &&
    selectedPhotos.some((photo) => photo.role === 'back')
  )
})
const areAllAiPhotosConfirmed = computed(
  () =>
    draft.aiCheckPhotoIds.length > 0 &&
    draft.aiCheckPhotoIds.every((photoId) =>
      draft.aiPhotoResults.some((result) => result.photoId === photoId && result.confirmed),
    ),
)
const conditionStepErrors = computed(() => ({
  conditionGrade:
    conditionStepTouched.conditionGrade && !draft.conditionGrade
      ? PRODUCT_REGISTRATION_VALIDATION_MESSAGES.conditionRequired
      : '',
  hasDefect:
    conditionStepTouched.hasDefect && draft.hasDefect === null
      ? PRODUCT_REGISTRATION_VALIDATION_MESSAGES.defectRequired
      : '',
  sellerDefectDescription:
    conditionStepTouched.sellerDefectDescription &&
    draft.hasDefect === true &&
    !draft.sellerDefectDescription.trim()
      ? PRODUCT_REGISTRATION_VALIDATION_MESSAGES.sellerDefectDescriptionRequired
      : '',
  aiPhotos:
    conditionStepTouched.aiPhotos && !hasRequiredAiPhotos.value
      ? PRODUCT_REGISTRATION_VALIDATION_MESSAGES.aiPhotoRequired
      : '',
  aiConfirmation:
    conditionStepTouched.aiConfirmation && !areAllAiPhotosConfirmed.value
      ? PRODUCT_REGISTRATION_VALIDATION_MESSAGES.aiPhotoConfirmationRequired
      : '',
}))
const isConditionStepValid = computed(
  () =>
    Boolean(draft.conditionGrade) &&
    draft.hasDefect !== null &&
    (draft.hasDefect !== true || Boolean(draft.sellerDefectDescription.trim())) &&
    hasRequiredAiPhotos.value &&
    areAllAiPhotosConfirmed.value,
)
const isPositivePrice = (value: string) => {
  const normalizedValue = value.trim().replaceAll(',', '')
  const parsedValue = Number(normalizedValue)

  return normalizedValue !== '' && Number.isFinite(parsedValue) && parsedValue > 0
}
const formatPrice = (price: number) => `${price.toLocaleString('ko-KR')}원`
const selectedSaleTypeLabel = computed(
  () =>
    PRODUCT_REGISTRATION_SALE_TYPE_OPTIONS.find((option) => option.id === draft.saleType)?.label ||
    '',
)
const selectedPriceLabel = computed(() => {
  if (draft.saleType === 'DIRECT' && isPositivePrice(draft.directSalePrice)) {
    return formatPrice(Number(draft.directSalePrice.trim().replaceAll(',', '')))
  }

  if (draft.saleType === 'AUCTION' && isPositivePrice(draft.auctionStartPrice)) {
    return formatPrice(Number(draft.auctionStartPrice.trim().replaceAll(',', '')))
  }

  return ''
})
const maxPriceBucketCount = computed(() =>
  Math.max(...priceRecommendationBuckets.map((bucket) => bucket.productCount)),
)
const pricingStepErrors = computed(() => ({
  saleType:
    pricingStepTouched.saleType && !draft.saleType
      ? PRODUCT_REGISTRATION_VALIDATION_MESSAGES.saleTypeRequired
      : '',
  directSalePrice:
    pricingStepTouched.directSalePrice && draft.saleType === 'DIRECT'
      ? !draft.directSalePrice.trim()
        ? PRODUCT_REGISTRATION_VALIDATION_MESSAGES.directSalePriceRequired
        : isPositivePrice(draft.directSalePrice)
          ? ''
          : PRODUCT_REGISTRATION_VALIDATION_MESSAGES.priceInvalid
      : '',
  auctionStartPrice:
    pricingStepTouched.auctionStartPrice && draft.saleType === 'AUCTION'
      ? !draft.auctionStartPrice.trim()
        ? PRODUCT_REGISTRATION_VALIDATION_MESSAGES.auctionStartPriceRequired
        : isPositivePrice(draft.auctionStartPrice)
          ? ''
          : PRODUCT_REGISTRATION_VALIDATION_MESSAGES.priceInvalid
      : '',
}))
const isPricingStepValid = computed(
  () =>
    Boolean(draft.saleType) &&
    (draft.saleType !== 'DIRECT' || isPositivePrice(draft.directSalePrice)) &&
    (draft.saleType !== 'AUCTION' || isPositivePrice(draft.auctionStartPrice)),
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

  if (currentStep.value.id === 'condition') {
    return isConditionStepValid.value
  }

  if (currentStep.value.id === 'pricing') {
    return isPricingStepValid.value
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

const selectConditionGrade = (conditionGrade: string) => {
  if (!['S', 'A', 'B', 'C'].includes(conditionGrade)) {
    return
  }

  draft.conditionGrade = conditionGrade as ProductRegistrationDraft['conditionGrade']
  conditionStepTouched.conditionGrade = true
}

const selectHasDefect = (hasDefect: boolean) => {
  draft.hasDefect = hasDefect
  conditionStepTouched.hasDefect = true
}

const selectSaleType = (saleType: string) => {
  draft.saleType = saleType as ProductRegistrationSaleType
  pricingStepTouched.saleType = true
}

const toggleAiCheckPhoto = (photoId: string) => {
  conditionStepTouched.aiPhotos = true

  if (draft.aiCheckPhotoIds.includes(photoId)) {
    draft.aiCheckPhotoIds = draft.aiCheckPhotoIds.filter((selectedPhotoId) => selectedPhotoId !== photoId)
    draft.aiPhotoResults = draft.aiPhotoResults.filter((result) => result.photoId !== photoId)
    currentAiResultIndex.value = Math.min(currentAiResultIndex.value, Math.max(draft.aiPhotoResults.length - 1, 0))
    return
  }

  draft.aiCheckPhotoIds = [...draft.aiCheckPhotoIds, photoId]
}

const selectedAdditionalAiPhotoCount = computed(
  () =>
    additionalAiSelectablePhotos.value.filter((photo) => draft.aiCheckPhotoIds.includes(photo.id))
      .length,
)

const createMockAiCandidates = (): ProductRegistrationAiDefectCandidate[] => [
  {
    id: crypto.randomUUID(),
    labelNumber: 1,
    description: '소매 끝단 마모 의심',
    box: { x: 58, y: 18, width: 24, height: 18 },
    isActualDefect: true,
  },
  {
    id: crypto.randomUUID(),
    labelNumber: 2,
    description: 'Front View 하단 오염 후보',
    box: { x: 22, y: 56, width: 30, height: 20 },
    isActualDefect: true,
  },
]

const runAiQualityCheck = () => {
  conditionStepTouched.aiPhotos = true
  conditionStepTouched.aiConfirmation = true

  if (!hasRequiredAiPhotos.value) {
    return
  }

  draft.aiPhotoResults = draft.aiCheckPhotoIds.map((photoId) => ({
    photoId,
    status: 'completed',
    candidates: createMockAiCandidates(),
    regeneratedImageUrl: '',
    confirmed: false,
  }))
  currentAiResultIndex.value = 0
}

const moveAiResult = (direction: -1 | 1) => {
  if (draft.aiPhotoResults.length === 0) {
    return
  }

  currentAiResultIndex.value =
    (currentAiResultIndex.value + direction + draft.aiPhotoResults.length) %
    draft.aiPhotoResults.length
}

const toggleAiDefectCandidate = (candidateId: string) => {
  if (!currentAiResult.value || currentAiResult.value.confirmed) {
    return
  }

  currentAiResult.value.confirmed = false
  currentAiResult.value.status = 'completed'
  currentAiResult.value.candidates = currentAiResult.value.candidates.map((candidate) => ({
    ...candidate,
    isActualDefect: candidate.id === candidateId ? !candidate.isActualDefect : candidate.isActualDefect,
  }))
}

const confirmCurrentAiPhoto = () => {
  if (!currentAiResult.value || !currentAiPhoto.value) {
    return
  }

  currentAiResult.value.status = 'confirmed'
  currentAiResult.value.regeneratedImageUrl = currentAiPhoto.value.previewUrl
  currentAiResult.value.confirmed = true
  conditionStepTouched.aiConfirmation = true
}

const editCurrentAiPhotoResult = () => {
  if (!currentAiResult.value) {
    return
  }

  currentAiResult.value.status = 'completed'
  currentAiResult.value.confirmed = false
  conditionStepTouched.aiConfirmation = true
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
    activeMeasurementFields.value.forEach((field) => {
      attributesStepTouched.measurements[field.id] = true
    })
    return
  }

  if (currentStep.value.id === 'condition') {
    conditionStepTouched.conditionGrade = true
    conditionStepTouched.hasDefect = true
    conditionStepTouched.sellerDefectDescription = true
    conditionStepTouched.aiPhotos = true
    conditionStepTouched.aiConfirmation = true
    return
  }

  if (currentStep.value.id === 'pricing') {
    pricingStepTouched.saleType = true
    pricingStepTouched.directSalePrice = true
    pricingStepTouched.auctionStartPrice = true
  }
}

const scrollToPageTop = () => {
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

const moveToPreviousStep = () => {
  if (isFirstStep.value || isCompleteStep.value) {
    return
  }

  currentStepIndex.value -= 1
  scrollToPageTop()
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
  scrollToPageTop()
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
  scrollToPageTop()
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
            <ProductPhotoUploader
              id="product-front-photo"
              title="Front View 이미지 업로드"
              description="옷의 Front View가 잘 보이는 사진을 등록해 주세요."
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
              title="Back View 이미지 업로드"
              description="옷의 Back View가 잘 보이는 사진을 등록해 주세요."
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
              <p>cm 기준의 단면 길이를 0보다 큰 숫자로 입력해 주세요.</p>

              <div v-if="activeMeasurementFields.length" class="product-registration__form-grid">
                <label
                  v-for="field in activeMeasurementFields"
                  :key="field.id"
                  class="product-registration__field"
                  :for="`product-registration-measurement-${field.id}`"
                >
                  <span>{{ field.label }}</span>
                  <input
                    :id="`product-registration-measurement-${field.id}`"
                    v-model="draft.measurements[field.id]"
                    type="number"
                    inputmode="decimal"
                    min="0"
                    step="0.1"
                    placeholder="예: 45"
                    :aria-invalid="attributesStepErrors.measurements[field.id] ? 'true' : 'false'"
                    :aria-describedby="`product-registration-measurement-${field.id}-error`"
                    @blur="attributesStepTouched.measurements[field.id] = true"
                  />
                  <span
                    v-if="attributesStepErrors.measurements[field.id]"
                    :id="`product-registration-measurement-${field.id}-error`"
                    class="product-registration__field-error"
                    role="alert"
                  >
                    {{ attributesStepErrors.measurements[field.id] }}
                  </span>
                </label>
              </div>
              <div v-else class="product-registration__field-empty" role="status">
                선택한 카테고리는 실측 정보를 입력하지 않습니다.
              </div>
            </fieldset>
          </form>

          <form
            v-else-if="currentStep.id === 'condition'"
            class="product-registration__form"
            aria-label="상품 상태와 하자 입력"
          >
            <section class="product-registration__section" aria-labelledby="condition-grade-title">
              <h3 id="condition-grade-title">상품 상태</h3>
              <div class="product-registration__option-grid" role="radiogroup" aria-label="상품 상태 선택">
                <button
                  v-for="option in PRODUCT_REGISTRATION_CONDITION_OPTIONS"
                  :key="option.id"
                  class="product-registration__option"
                  :class="{ 'product-registration__option--selected': draft.conditionGrade === option.id }"
                  type="button"
                  :aria-pressed="draft.conditionGrade === option.id"
                  @click="selectConditionGrade(option.id)"
                >
                  {{ option.label }}
                </button>
              </div>
              <p
                v-if="conditionStepErrors.conditionGrade"
                class="product-registration__field-error"
                role="alert"
              >
                {{ conditionStepErrors.conditionGrade }}
              </p>
            </section>

            <section class="product-registration__section" aria-labelledby="seller-defect-title">
              <h3 id="seller-defect-title">판매자 고지 하자</h3>
              <div class="product-registration__option-grid" role="radiogroup" aria-label="하자 여부 선택">
                <button
                  class="product-registration__option"
                  :class="{ 'product-registration__option--selected': draft.hasDefect === false }"
                  type="button"
                  :aria-pressed="draft.hasDefect === false"
                  @click="selectHasDefect(false)"
                >
                  하자 없음
                </button>
                <button
                  class="product-registration__option"
                  :class="{ 'product-registration__option--selected': draft.hasDefect === true }"
                  type="button"
                  :aria-pressed="draft.hasDefect === true"
                  @click="selectHasDefect(true)"
                >
                  하자 있음
                </button>
              </div>
              <p
                v-if="conditionStepErrors.hasDefect"
                class="product-registration__field-error"
                role="alert"
              >
                {{ conditionStepErrors.hasDefect }}
              </p>

              <label
                v-if="draft.hasDefect"
                class="product-registration__field"
                for="product-registration-seller-defect"
              >
                <span>하자 설명</span>
                <textarea
                  id="product-registration-seller-defect"
                  v-model="draft.sellerDefectDescription"
                  maxlength="300"
                  rows="3"
                  placeholder="판매자가 직접 확인한 하자를 입력해 주세요."
                  :aria-invalid="conditionStepErrors.sellerDefectDescription ? 'true' : 'false'"
                  aria-describedby="product-registration-seller-defect-error"
                  @blur="conditionStepTouched.sellerDefectDescription = true"
                />
                <span
                  v-if="conditionStepErrors.sellerDefectDescription"
                  id="product-registration-seller-defect-error"
                  class="product-registration__field-error"
                  role="alert"
                >
                  {{ conditionStepErrors.sellerDefectDescription }}
                </span>
              </label>
            </section>

            <section class="product-registration__section" aria-labelledby="ai-quality-title">
              <div class="product-registration__section-header">
                <div>
                  <h3 id="ai-quality-title">AI 품질 검증</h3>
                  <p>AI 품질 검증에 사용할 사진을 선택해 주세요. Front View와 Back View는 필수입니다.</p>
                </div>
              </div>

              <div class="product-registration__ai-photo-list" aria-label="AI 품질 검증 사진 선택">
                <button
                  v-for="photo in requiredAiSelectablePhotos"
                  :key="photo.id"
                  class="product-registration__ai-photo"
                  :class="{ 'product-registration__ai-photo--selected': draft.aiCheckPhotoIds.includes(photo.id) }"
                  type="button"
                  :aria-pressed="draft.aiCheckPhotoIds.includes(photo.id)"
                  @click="toggleAiCheckPhoto(photo.id)"
                >
                  <img
                    :src="photo.previewUrl"
                    :alt="`${photo.role === 'front' ? 'Front View' : 'Back View'} 품질 검증 사진`"
                  />
                  <span>
                    {{ photo.role === 'front' ? 'Front View' : 'Back View' }}
                  </span>
                </button>
              </div>
              <button
                v-if="additionalAiSelectablePhotos.length"
                class="product-registration__add-ai-photo-button"
                type="button"
                @click="isAdditionalAiPhotoPickerOpen = !isAdditionalAiPhotoPickerOpen"
              >
                추가 선택
                <span>{{ selectedAdditionalAiPhotoCount }}개 선택</span>
              </button>
              <div
                v-if="isAdditionalAiPhotoPickerOpen"
                class="product-registration__additional-ai-panel"
                aria-label="추가 AI 품질 검증 사진 선택"
              >
                <button
                  v-for="photo in additionalAiSelectablePhotos"
                  :key="photo.id"
                  class="product-registration__additional-ai-photo"
                  :class="{
                    'product-registration__additional-ai-photo--selected': draft.aiCheckPhotoIds.includes(photo.id),
                  }"
                  type="button"
                  :aria-pressed="draft.aiCheckPhotoIds.includes(photo.id)"
                  @click="toggleAiCheckPhoto(photo.id)"
                >
                  <img :src="photo.previewUrl" :alt="`${photo.fileName} 추가 품질 검증 사진`" />
                  <span>{{ draft.aiCheckPhotoIds.includes(photo.id) ? '선택됨' : '선택' }}</span>
                </button>
              </div>
              <p v-if="conditionStepErrors.aiPhotos" class="product-registration__field-error" role="alert">
                {{ conditionStepErrors.aiPhotos }}
              </p>
              <div class="product-registration__ai-actions">
                <button
                  class="product-registration__button product-registration__button--secondary"
                  type="button"
                  @click="runAiQualityCheck"
                >
                  확인
                </button>
              </div>

              <div v-if="currentAiResult && currentAiPhoto" class="product-registration__ai-result">
                <div class="product-registration__ai-result-toolbar">
                  <button type="button" aria-label="이전 사진" @click="moveAiResult(-1)">
                    <svg aria-hidden="true" viewBox="0 0 24 24">
                      <path
                        d="M15 18 9 12l6-6"
                        fill="none"
                        stroke="currentColor"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                      />
                    </svg>
                  </button>
                  <strong>
                    {{ currentAiResultIndex + 1 }} / {{ draft.aiPhotoResults.length }}
                    {{
                      currentAiPhoto.role === 'front'
                        ? 'Front View'
                        : currentAiPhoto.role === 'back'
                          ? 'Back View'
                          : '추가'
                    }}
                    검증 결과
                  </strong>
                  <button type="button" aria-label="다음 사진" @click="moveAiResult(1)">
                    <svg aria-hidden="true" viewBox="0 0 24 24">
                      <path
                        d="m9 18 6-6-6-6"
                        fill="none"
                        stroke="currentColor"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                      />
                    </svg>
                  </button>
                </div>

                <div class="product-registration__ai-image">
                  <img :src="currentAiPhoto.previewUrl" :alt="`${currentAiPhoto.fileName} AI 품질 검증 결과`" />
                  <span
                    v-for="candidate in currentAiResult.candidates"
                    :key="candidate.id"
                    class="product-registration__ai-box"
                    :class="{ 'product-registration__ai-box--actual': candidate.isActualDefect }"
                    :style="{
                      left: `${candidate.box.x}%`,
                      top: `${candidate.box.y}%`,
                      width: `${candidate.box.width}%`,
                      height: `${candidate.box.height}%`,
                    }"
                  >
                    {{ candidate.labelNumber }}
                  </span>
                </div>

                <div class="product-registration__ai-cards">
                  <article
                    v-for="candidate in currentAiResult.candidates"
                    :key="candidate.id"
                    class="product-registration__ai-card"
                    :class="{ 'product-registration__ai-card--actual': candidate.isActualDefect }"
                  >
                    <div>
                      <strong>{{ candidate.labelNumber }}번</strong>
                      <p>{{ candidate.description }}</p>
                    </div>
                    <button
                      type="button"
                      :disabled="currentAiResult.confirmed"
                      @click="toggleAiDefectCandidate(candidate.id)"
                    >
                      {{ candidate.isActualDefect ? '하자 제외' : '하자로 표시' }}
                    </button>
                  </article>
                </div>

                <div class="product-registration__ai-result-actions">
                  <span v-if="currentAiResult.confirmed">저장 완료</span>
                  <button
                    v-if="currentAiResult.confirmed"
                    class="product-registration__button product-registration__button--secondary"
                    type="button"
                    @click="editCurrentAiPhotoResult"
                  >
                    수정하기
                  </button>
                  <button
                    v-else
                    class="product-registration__button product-registration__button--primary"
                    type="button"
                    @click="confirmCurrentAiPhoto"
                  >
                    결과 저장
                  </button>
                </div>
              </div>

              <div v-else class="product-registration__ai-empty" role="status">
                <strong>AI 품질 검증 결과가 없습니다.</strong>
                <p>Front View와 Back View 사진을 필수로 선택한 뒤 확인 버튼을 눌러 주세요.</p>
              </div>

              <p
                v-if="conditionStepErrors.aiConfirmation"
                class="product-registration__field-error"
                role="alert"
              >
                {{ conditionStepErrors.aiConfirmation }}
              </p>
            </section>
          </form>

          <form
            v-else-if="currentStep.id === 'pricing'"
            class="product-registration__form"
            aria-label="상품 가격 입력"
          >
            <section class="product-registration__section" aria-labelledby="price-recommendation-title">
              <div class="product-registration__section-header">
                <div>
                  <h3 id="price-recommendation-title">AI 가격 추천</h3>
                  <p>동일 상품 데이터를 기준으로 가격대별 등록 상품 수와 등급별 추천가를 확인합니다.</p>
                </div>
              </div>

              <div class="product-registration__price-chart" aria-label="가격 추천 그래프">
                <div class="product-registration__price-chart-plot">
                  <div class="product-registration__price-axis product-registration__price-axis--y">
                    <span>상품 수</span>
                  </div>
                  <div class="product-registration__price-chart-body">
                    <div class="product-registration__price-y-scale" aria-hidden="true">
                      <span>{{ maxPriceBucketCount }}</span>
                      <span>{{ Math.round(maxPriceBucketCount / 2) }}</span>
                      <span>0</span>
                    </div>
                    <div class="product-registration__price-bars">
                      <div
                        v-for="bucket in priceRecommendationBuckets"
                        :key="bucket.id"
                        class="product-registration__price-bar"
                      >
                        <strong>{{ bucket.productCount }}</strong>
                        <span
                          class="product-registration__price-bar-fill"
                          :style="{ height: `${(bucket.productCount / maxPriceBucketCount) * 100}%` }"
                        />
                      </div>
                      <div
                        v-for="(recommendation, index) in recommendedPrices"
                        :key="recommendation.grade"
                        class="product-registration__price-marker"
                        :style="{ left: `${18 + index * 16}%` }"
                      >
                        <span>{{ recommendation.label }}</span>
                      </div>
                    </div>
                  </div>
                  <div class="product-registration__price-axis product-registration__price-axis--x">
                    <span
                      v-for="bucket in priceRecommendationBuckets"
                      :key="bucket.id"
                    >
                      {{ bucket.label }}
                    </span>
                  </div>
                </div>

                <dl class="product-registration__price-recommendations">
                  <div
                    v-for="recommendation in recommendedPrices"
                    :key="recommendation.grade"
                  >
                    <dt>{{ recommendation.label }}</dt>
                    <dd>{{ formatPrice(recommendation.price) }}</dd>
                  </div>
                </dl>
              </div>
            </section>

            <section class="product-registration__section" aria-labelledby="sale-type-title">
              <div class="product-registration__section-header">
                <div>
                  <h3 id="sale-type-title">판매 방식 / 가격</h3>
                </div>
              </div>

              <div class="product-registration__option-grid" role="radiogroup" aria-label="판매 방식 선택">
                <button
                  v-for="option in PRODUCT_REGISTRATION_SALE_TYPE_OPTIONS"
                  :key="option.id"
                  class="product-registration__option"
                  :class="{ 'product-registration__option--selected': draft.saleType === option.id }"
                  type="button"
                  :aria-pressed="draft.saleType === option.id"
                  @click="selectSaleType(option.id)"
                >
                  {{ option.label }}
                </button>
              </div>
              <p v-if="pricingStepErrors.saleType" class="product-registration__field-error" role="alert">
                {{ pricingStepErrors.saleType }}
              </p>

              <label v-if="draft.saleType === 'DIRECT'" class="product-registration__field">
                <span>판매가</span>
                <span class="product-registration__price-input">
                  <input
                    v-model="draft.directSalePrice"
                    inputmode="numeric"
                    placeholder="판매가를 입력해 주세요"
                    @blur="pricingStepTouched.directSalePrice = true"
                  />
                  <span>P</span>
                </span>
                <span
                  v-if="pricingStepErrors.directSalePrice"
                  class="product-registration__field-error"
                  role="alert"
                >
                  {{ pricingStepErrors.directSalePrice }}
                </span>
              </label>

              <div v-if="draft.saleType === 'AUCTION'" class="product-registration__form-grid">
                <label class="product-registration__field">
                  <span>시작가</span>
                  <span class="product-registration__price-input">
                    <input
                      v-model="draft.auctionStartPrice"
                      inputmode="numeric"
                      placeholder="시작가를 입력해 주세요"
                      @blur="pricingStepTouched.auctionStartPrice = true"
                    />
                    <span>원</span>
                  </span>
                  <span
                    v-if="pricingStepErrors.auctionStartPrice"
                    class="product-registration__field-error"
                    role="alert"
                  >
                    {{ pricingStepErrors.auctionStartPrice }}
                  </span>
                </label>

                <label class="product-registration__field">
                  <span>경매 라이브</span>
                  <select v-model="draft.linkedLiveId">
                    <option value="">선택 안 함</option>
                    <option
                      v-for="live in auctionLiveOptions"
                      :key="live.id"
                      :value="live.id"
                    >
                      {{ live.label }}
                    </option>
                  </select>
                </label>
              </div>
            </section>
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
          <div class="product-registration__summary-image">
            <img v-if="representativePhoto" :src="representativePhoto.previewUrl" :alt="representativePhoto.fileName" />
          </div>
          <dl>
            <div>
              <dt>상품명</dt>
              <dd>{{ draft.name.trim() }}</dd>
            </div>
            <div>
              <dt>브랜드</dt>
              <dd>{{ draft.brand.trim() }}</dd>
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
              <dt>상태</dt>
              <dd>{{ selectedConditionLabel }}</dd>
            </div>
            <div>
              <dt>판매 유형</dt>
              <dd>{{ selectedSaleTypeLabel }}</dd>
            </div>
            <div>
              <dt>가격</dt>
              <dd>{{ selectedPriceLabel }}</dd>
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
  background: var(--color-live);
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

.product-registration__step--current {
  color: var(--color-text-primary);
}

.product-registration__step--current span,
.product-registration__step--complete span {
  border-color: var(--color-live);
  background: var(--color-live);
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

.product-registration__price-input {
  position: relative;
  display: block;
}

.product-registration__price-input input {
  padding-right: 48px;
}

.product-registration__price-input span {
  position: absolute;
  top: 50%;
  right: var(--space-4);
  color: var(--color-text-secondary);
  font-size: 14px;
  font-weight: var(--font-weight-semibold);
  line-height: 20px;
  transform: translateY(-50%);
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

.product-registration__field select:disabled {
  background: var(--color-surface-secondary);
  color: var(--color-text-muted);
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

.product-registration__field-empty {
  padding: var(--space-5);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface-secondary);
  color: var(--color-text-secondary);
  text-align: center;
}

.product-registration__section {
  display: grid;
  gap: var(--space-4);
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
}

.product-registration__section h3 {
  color: var(--color-text-primary);
  font-size: 18px;
  font-weight: var(--font-weight-bold);
  line-height: 26px;
}

.product-registration__section-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
}

.product-registration__section-header div {
  display: grid;
  gap: var(--space-1);
}

.product-registration__section-header p {
  color: var(--color-text-secondary);
  font-size: 14px;
  line-height: 20px;
}

.product-registration__option-grid {
  display: grid;
  gap: var(--space-3);
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.product-registration__option {
  min-height: var(--button-height-standard);
  padding: 0 var(--space-4);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-weight: var(--font-weight-bold);
}

.product-registration__option--selected {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
  color: var(--color-primary);
}

.product-registration__ai-photo-list {
  display: grid;
  gap: var(--space-3);
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.product-registration__ai-photo {
  position: relative;
  display: grid;
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface-secondary);
  color: var(--color-text-primary);
}

.product-registration__ai-photo--selected {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
}

.product-registration__ai-photo img {
  width: 100%;
  aspect-ratio: 4 / 3;
  object-fit: cover;
}

.product-registration__ai-photo span {
  padding: var(--space-3);
  font-weight: var(--font-weight-bold);
}

.product-registration__add-ai-photo-button {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  width: 100%;
  min-height: var(--button-height-standard);
  padding: 0 var(--space-4);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-weight: var(--font-weight-bold);
}

.product-registration__add-ai-photo-button span {
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: var(--font-weight-semibold);
}

.product-registration__additional-ai-panel {
  display: grid;
  gap: var(--space-3);
  grid-template-columns: repeat(3, minmax(0, 1fr));
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface-secondary);
}

.product-registration__ai-actions {
  display: flex;
  justify-content: flex-end;
}

.product-registration__ai-actions .product-registration__button {
  min-width: 160px;
}

.product-registration__additional-ai-photo {
  display: grid;
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-primary);
}

.product-registration__additional-ai-photo--selected {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
}

.product-registration__additional-ai-photo img {
  width: 100%;
  aspect-ratio: 4 / 3;
  object-fit: cover;
}

.product-registration__additional-ai-photo span {
  padding: var(--space-2);
  font-size: 12px;
  font-weight: var(--font-weight-bold);
}

.product-registration__ai-result {
  display: grid;
  gap: var(--space-4);
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface-secondary);
}

.product-registration__ai-result-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}

.product-registration__ai-result-toolbar button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-weight: var(--font-weight-bold);
}

.product-registration__ai-result-toolbar button:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.product-registration__ai-result-toolbar svg {
  width: 20px;
  height: 20px;
}

.product-registration__ai-result-toolbar strong {
  color: var(--color-text-primary);
  text-align: center;
}

.product-registration__ai-image {
  position: relative;
  overflow: hidden;
  border-radius: var(--radius-control);
  background: var(--color-surface);
}

.product-registration__ai-image img {
  width: 100%;
  aspect-ratio: 4 / 3;
  object-fit: cover;
}

.product-registration__ai-box {
  position: absolute;
  display: grid;
  padding: 4px 0 0 6px;
  border: 2px solid #2563eb;
  background: rgb(37 99 235 / 12%);
  color: #2563eb;
  font-size: 12px;
  font-weight: var(--font-weight-bold);
  line-height: 1;
  place-items: start;
}

.product-registration__ai-box--actual {
  border-color: var(--color-error);
  background: rgb(220 38 38 / 12%);
  color: var(--color-error);
}

.product-registration__ai-cards {
  display: grid;
  gap: var(--space-3);
}

.product-registration__ai-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
}

.product-registration__ai-card--actual {
  border-color: var(--color-error);
}

.product-registration__ai-card div {
  display: grid;
  gap: var(--space-1);
}

.product-registration__ai-card strong {
  color: var(--color-text-primary);
}

.product-registration__ai-card p {
  color: var(--color-text-secondary);
  font-size: 14px;
  line-height: 20px;
}

.product-registration__ai-card button {
  min-width: 88px;
  height: var(--button-height-small);
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-size: 13px;
  font-weight: var(--font-weight-bold);
  white-space: nowrap;
}

.product-registration__ai-card--actual button {
  border-color: var(--color-error);
  background: var(--color-error-soft);
  color: var(--color-error);
}

.product-registration__ai-card button:disabled {
  border-color: var(--color-border);
  background: var(--color-surface-secondary);
  color: var(--color-text-muted);
  cursor: not-allowed;
}

.product-registration__ai-result-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-3);
}

.product-registration__ai-result-actions > span {
  color: var(--color-text-primary);
  font-size: 14px;
  font-weight: var(--font-weight-bold);
}

.product-registration__ai-empty {
  display: grid;
  gap: var(--space-1);
  min-height: 132px;
  place-content: center;
  padding: var(--space-5);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface-secondary);
  color: var(--color-text-secondary);
  text-align: center;
}

.product-registration__ai-empty strong {
  color: var(--color-text-primary);
}

.product-registration__price-chart {
  display: grid;
  gap: var(--space-4);
}

.product-registration__price-chart-plot {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface-secondary);
}

.product-registration__price-axis {
  color: var(--color-text-muted);
  font-size: 12px;
  font-weight: var(--font-weight-semibold);
}

.product-registration__price-axis--y {
  display: flex;
  justify-content: flex-start;
}

.product-registration__price-axis--x {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  margin-left: 36px;
  text-align: center;
}

.product-registration__price-chart-body {
  display: grid;
  gap: var(--space-3);
  grid-template-columns: 24px minmax(0, 1fr);
}

.product-registration__price-y-scale {
  display: flex;
  align-items: stretch;
  flex-direction: column;
  justify-content: space-between;
  height: 220px;
  color: var(--color-text-muted);
  font-size: 12px;
  font-weight: var(--font-weight-semibold);
  text-align: right;
}

.product-registration__price-bars {
  position: relative;
  display: grid;
  align-items: end;
  height: 220px;
  gap: var(--space-3);
  grid-template-columns: repeat(6, minmax(0, 1fr));
  padding: var(--space-4) var(--space-2) 0;
  border-bottom: 1px solid var(--color-border-strong);
}

.product-registration__price-bar {
  position: relative;
  display: flex;
  align-items: end;
  flex-direction: column;
  justify-content: flex-end;
  height: 100%;
  min-width: 0;
}

.product-registration__price-bar-fill {
  display: block;
  width: 100%;
  min-height: 12px;
  border-radius: var(--radius-sm) var(--radius-sm) 0 0;
  background: color-mix(in srgb, var(--color-live) 18%, var(--color-surface));
}

.product-registration__price-bar strong {
  display: block;
  width: 100%;
  margin-bottom: var(--space-1);
  color: var(--color-text-secondary);
  font-size: 12px;
  line-height: 16px;
  text-align: center;
}

.product-registration__price-marker {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 2px;
  background: var(--color-error);
}

.product-registration__price-marker span {
  position: absolute;
  top: -24px;
  left: 50%;
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  background: var(--color-error);
  color: var(--color-text-inverse);
  font-size: 11px;
  font-weight: var(--font-weight-bold);
  white-space: nowrap;
  transform: translateX(-50%);
}

.product-registration__price-recommendations {
  display: grid;
  gap: var(--space-3);
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.product-registration__price-recommendations div {
  display: grid;
  gap: var(--space-1);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
}

.product-registration__price-recommendations dt {
  color: var(--color-error);
  font-size: 12px;
  font-weight: var(--font-weight-bold);
}

.product-registration__price-recommendations dd {
  color: var(--color-text-primary);
  font-weight: var(--font-weight-bold);
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

.product-registration__summary-image {
  display: grid;
  place-items: center;
  overflow: hidden;
  width: 100%;
  aspect-ratio: 4 / 3;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface-secondary);
  color: var(--color-text-muted);
  font-size: 13px;
  font-weight: var(--font-weight-semibold);
}

.product-registration__summary-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
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

  .product-registration__option-grid,
  .product-registration__ai-photo-list {
    grid-template-columns: 1fr;
  }

  .product-registration__additional-ai-panel {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .product-registration__section-header,
  .product-registration__ai-card {
    flex-direction: column;
    align-items: stretch;
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

  .product-registration__additional-ai-panel {
    grid-template-columns: 1fr;
  }
}
</style>
