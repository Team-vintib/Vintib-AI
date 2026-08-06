<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import {
  getBrands,
  getCategories,
  getCategoryCode,
  getProductAiModelCutStatus,
  type BrandDto,
  type CategoryDto,
  type ProductAiModelCutStatusDto,
} from '@/domains/product/api/productApi'
import { analyzeRegistrationPhotos } from '@/domains/product/api/productAiApi'
import { submitProductRegistrationDraft } from '@/domains/product/api/productRegistrationApi'
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
  ProductRegistrationAiModelGender,
  ProductRegistrationAiPhotoResult,
  ProductRegistrationPriceBucket,
  ProductRegistrationPhotoDraft,
  ProductRegistrationPhotoRole,
  ProductRegistrationRecommendedPrice,
  ProductRegistrationSaleType,
  ProductRegistrationStepId,
} from '@/domains/product/types/productRegistration.types'
import { normalizeApiError } from '@/shared/api/http'
import { ROUTE_NAMES, ROUTE_PATHS } from '@/shared/constants/routes'
import DefaultLayout from '@/shared/layouts/DefaultLayout.vue'

const PRODUCT_REGISTRATION_MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024

const router = useRouter()
const currentStepIndex = ref(0)
const photoStepTouched = ref(false)
const aiModelStepTouched = ref(false)
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
})
const pricingStepTouched = reactive({
  saleType: false,
  directSalePrice: false,
})
const currentAiResultIndex = ref(0)
const registeredProductId = ref('')
// AI 착용컷 폴링 상태 — 등록(aiModelEnabled=true) 성공 직후에만 값이 채워진다.
const aiModelCutStatus = ref<ProductAiModelCutStatusDto['status']>('NONE')
const aiModelCutImageUrl = ref<string | null>(null)
const AI_MODEL_CUT_POLL_INTERVAL_MS = 5_000
// 워커가 job마다 VLM/FLUX/CatVTON을 순차로 새로 로드하는 구조라(6GB급 GPU 전제),
// 로컬 실측 기준 완료까지 4분 넘게 걸릴 수 있다 — 120s는 너무 짧아 완료 직전에
// 폴링이 멈추는 문제가 있었다(-517 로컬 테스트에서 확인).
const AI_MODEL_CUT_POLL_TIMEOUT_MS = 600_000
let aiModelCutPollToken = 0
const isSubmittingRegistration = ref(false)
const registrationSubmitError = ref('')
const isCompletenessPromptOpen = ref(false)
const brands = ref<BrandDto[]>([])
const categories = ref<CategoryDto[]>([])
const categoryMajorId = ref('')
interface CategorySelectOption {
  id: string
  label: string
  parentId: string
}

const dedupeCategoryOptionsByLabel = (options: CategorySelectOption[]) => {
  const optionMap = new Map<string, CategorySelectOption>()

  options.forEach((option) => {
    const key = option.label.trim()

    if (!optionMap.has(key)) {
      optionMap.set(key, option)
    }
  })

  return [...optionMap.values()]
}

const majorCategoryOptions = computed<CategorySelectOption[]>(() => {
  if (!categories.value.length) {
    return PRODUCT_REGISTRATION_CATEGORY_OPTIONS.map((option) => ({
      id: option.id,
      label: option.label,
      parentId: '',
    }))
  }

  return dedupeCategoryOptionsByLabel(
    categories.value
      .filter((category) => category.depth === 2)
      .map((category) => ({
        id: String(category.id),
        label: category.name,
        parentId: String(category.parentId ?? ''),
      })),
  )
})
const minorCategoryOptions = computed<CategorySelectOption[]>(() => {
  if (!categories.value.length || !categoryMajorId.value) {
    return []
  }

  const selectedCategory = majorCategoryOptions.value.find(
    (option) => option.id === categoryMajorId.value,
  )

  if (!selectedCategory) {
    return []
  }

  const middleCategoryIds = categories.value
    .filter(
      (category) =>
        category.depth === 2 &&
        category.name.trim() === selectedCategory.label.trim(),
    )
    .map((category) => String(category.id))

  return dedupeCategoryOptionsByLabel(
    categories.value
      .filter(
        (category) =>
          category.depth === 3 && middleCategoryIds.includes(String(category.parentId)),
      )
      .map((category) => ({
        id: String(category.id),
        label: category.name,
        parentId: String(category.parentId ?? ''),
      })),
  )
})
const updateMajorCategory = () => {
  draft.categoryId = categoryMajorId.value
  basicStepTouched.categoryId = true
}

const updateMinorCategory = () => {
  basicStepTouched.categoryId = true
}

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

const createInitialDraft = (): ProductRegistrationDraft => ({
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
  measurements: {},
  conditionGrade: '',
  hasDefect: null,
  sellerDefectDescription: '',
  aiQualityStatus: 'idle',
  aiPhotoResults: [],
  aiCategorySuggestion: null,
  aiColorSuggestion: null,
  aiModelEnabled: false,
  aiModelGender: null,
  saleType: 'DIRECT',
  directSalePrice: '',
  linkedLiveId: '',
})

const draft = reactive<ProductRegistrationDraft>(createInitialDraft())

const currentStep = computed(() => PRODUCT_REGISTRATION_STEPS[currentStepIndex.value])
const isFirstStep = computed(() => currentStepIndex.value === 0)
const isCompleteStep = computed(() => currentStep.value.id === 'complete')
const hasRegistrationSubmitted = computed(() => Boolean(registeredProductId.value))
const isSubmitStep = computed(() => isCompleteStep.value && !hasRegistrationSubmitted.value)
const canShowCompletenessPanel = computed(() =>
  ['photos', 'condition', 'pricing'].includes(currentStep.value.id),
)
const nextActionLabel = computed(() =>
  isSubmitStep.value && isSubmittingRegistration.value ? '등록 중' : isSubmitStep.value ? '등록' : '다음',
)
const frontPhotos = computed(() => draft.photos.filter((photo) => photo.role === 'front'))
const backPhotos = computed(() => draft.photos.filter((photo) => photo.role === 'back'))
const additionalPhotos = computed(() =>
  draft.photos.filter((photo) => photo.role === 'additional'),
)
const frontPhotoCountLabel = computed(() => `(${Math.min(frontPhotos.value.length, 1)}/1)`)
const backPhotoCountLabel = computed(() => `(${Math.min(backPhotos.value.length, 1)}/1)`)
const photoStepErrors = computed(() => ({
  front: photoStepTouched.value && frontPhotos.value.length === 0
    ? PRODUCT_REGISTRATION_VALIDATION_MESSAGES.frontPhotoRequired
    : '',
  back: photoStepTouched.value && backPhotos.value.length === 0
    ? PRODUCT_REGISTRATION_VALIDATION_MESSAGES.backPhotoRequired
    : '',
}))
const isCategorySelectionComplete = computed(() => {
  if (!categoryMajorId.value) {
    return false
  }

  if (minorCategoryOptions.value.length === 0) {
    return Boolean(draft.categoryId)
  }

  return minorCategoryOptions.value.some((option) => option.id === draft.categoryId)
})

const basicStepErrors = computed(() => ({
  name:
    basicStepTouched.name && !draft.name.trim()
      ? PRODUCT_REGISTRATION_VALIDATION_MESSAGES.nameRequired
      : '',
  brand: '',
  color:
    basicStepTouched.color && !draft.color
      ? PRODUCT_REGISTRATION_VALIDATION_MESSAGES.colorRequired
      : '',
  categoryId:
    basicStepTouched.categoryId && !isCategorySelectionComplete.value
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

  if (!normalizeMeasurementValue(value)) return ''

  return isPositiveMeasurement(value)
    ? ''
    : PRODUCT_REGISTRATION_VALIDATION_MESSAGES.measurementInvalid
}

const selectedCategoryCode = computed(() => {
  if (PRODUCT_REGISTRATION_MEASUREMENT_FIELDS_BY_CATEGORY[categoryMajorId.value]) {
    return categoryMajorId.value
  }

  const selectedMajorCategory = categories.value.find(
    (category) => String(category.id) === categoryMajorId.value,
  )

  if (selectedMajorCategory) {
    return getCategoryCode(selectedMajorCategory.name)
  }

  if (PRODUCT_REGISTRATION_MEASUREMENT_FIELDS_BY_CATEGORY[draft.categoryId]) {
    return draft.categoryId
  }

  const selectedCategory = categories.value.find((category) => String(category.id) === draft.categoryId)

  return selectedCategory ? getCategoryCode(selectedCategory.name) : ''
})
const activeMeasurementFields = computed(
  () => PRODUCT_REGISTRATION_MEASUREMENT_FIELDS_BY_CATEGORY[selectedCategoryCode.value] ?? [],
)
const attributesStepErrors = computed(() => ({
  size: '',
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
    backPhotos.value.length > 0,
)
const isAiModelSettingsAvailable = computed(() => isPhotoStepValid.value)
const isAiModelStepValid = computed(
  () => !draft.aiModelEnabled || Boolean(draft.aiModelGender),
)
const aiModelStepError = computed(() =>
  aiModelStepTouched.value && draft.aiModelEnabled && !draft.aiModelGender
    ? PRODUCT_REGISTRATION_VALIDATION_MESSAGES.aiModelGenderRequired
    : '',
)
const aiModelGenderLabel = computed(() => {
  if (draft.aiModelGender === 'FEMALE') return '여성'
  if (draft.aiModelGender === 'MALE') return '남성'

  return ''
})
const isBasicStepValid = computed(
  () => Boolean(draft.name.trim()) && Boolean(draft.color) && isCategorySelectionComplete.value,
)
// 현재 선택값이 AI 추천값과 같은 동안만 배지를 보여준다 — 사용자가 셀렉트를 바꾸면 자동으로 사라진다.
const isCategoryAiSuggested = computed(
  () =>
    draft.aiCategorySuggestion?.status === 'completed' &&
    categoryMajorId.value === draft.aiCategorySuggestion.majorId &&
    draft.categoryId === draft.aiCategorySuggestion.minorId,
)
const isColorAiSuggested = computed(
  () => draft.aiColorSuggestion?.status === 'completed' && draft.color === draft.aiColorSuggestion.colorId,
)
const isAttributesStepValid = computed(
  () =>
    activeMeasurementFields.value.every((field) =>
      !normalizeMeasurementValue(draft.measurements[field.id] ?? '') ||
      isPositiveMeasurement(draft.measurements[field.id] ?? ''),
    ),
)
const currentAiResult = computed<ProductRegistrationAiPhotoResult | null>(
  () => draft.aiPhotoResults[currentAiResultIndex.value] ?? null,
)
const currentAiPhoto = computed(() =>
  currentAiResult.value
    ? draft.photos.find((photo) => photo.id === currentAiResult.value?.photoId) ?? null
    : null,
)
// 분석 자체는 사진 2장이 갖춰지는 즉시 자동으로 돈다. 다만 각 사진의 하자 판정은
// 사용자가 직접 확인하고 "결과 저장"을 눌러야 끝난 것으로 본다 — AI가 실패했을 때는
// 판매자 잘못이 아니므로 그대로 다음 단계로 넘어갈 수 있게 둔다.
const areAllAiPhotosConfirmed = computed(
  () =>
    draft.aiPhotoResults.length > 0 && draft.aiPhotoResults.every((result) => result.confirmed),
)
const isAiQualityCheckSettled = computed(
  () =>
    (draft.aiQualityStatus === 'completed' && areAllAiPhotosConfirmed.value) ||
    draft.aiQualityStatus === 'failed',
)
const conditionStepErrors = computed(() => ({
  conditionGrade: '',
  hasDefect: '',
  sellerDefectDescription: '',
}))
const isConditionStepValid = computed(() => isAiQualityCheckSettled.value)
const isPositivePrice = (value: string) => {
  const normalizedValue = value.trim()
  const parsedValue = Number(normalizedValue)

  return normalizedValue !== '' && Number.isFinite(parsedValue) && parsedValue > 0
}
const formatPrice = (price: number) => `${price.toLocaleString('ko-KR')}원`
const getNumericInputValue = (event: Event) => {
  if (!(event.target instanceof HTMLInputElement)) {
    return ''
  }

  const numericValue = event.target.value.replace(/\D/g, '')
  event.target.value = numericValue

  return numericValue
}
const updateDirectSalePrice = (event: Event) => {
  draft.directSalePrice = getNumericInputValue(event)
}
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
}))
const isPricingStepValid = computed(
  () =>
    Boolean(draft.saleType) &&
    (draft.saleType !== 'DIRECT' || isPositivePrice(draft.directSalePrice)),
)
const canShowBasicInfoSection = computed(() => isPhotoStepValid.value)
const canShowAttributesSection = computed(
  () => isPhotoStepValid.value && isBasicStepValid.value,
)
const isIntroStepValid = computed(
  () =>
    isPhotoStepValid.value &&
    isAiModelStepValid.value &&
    isBasicStepValid.value &&
    isAttributesStepValid.value,
)

const canMoveCurrentStepNext = computed(() => {
  if (currentStep.value.id === 'photos') {
    return isIntroStepValid.value
  }

  if (currentStep.value.id === 'condition') {
    return isConditionStepValid.value
  }

  if (currentStep.value.id === 'pricing') {
    return isPricingStepValid.value
  }

  return true
})

type ProductInfoCompletenessPriority = 'strong' | 'recommended'

interface ProductInfoCompletenessItem {
  id: string
  label: string
  stepId: ProductRegistrationStepId
  priority: ProductInfoCompletenessPriority
  targetId: string
  isCompleted: () => boolean
}

const isDefectInfoCompleted = () => {
  if (draft.hasDefect === false) {
    return true
  }

  return draft.hasDefect === true && Boolean(draft.sellerDefectDescription.trim())
}

const isMeasurementInfoCompleted = () => {
  if (!activeMeasurementFields.value.length) {
    return Boolean(draft.categoryId)
  }

  return activeMeasurementFields.value.every((field) =>
    isPositiveMeasurement(draft.measurements[field.id] ?? ''),
  )
}

const completenessItems: ProductInfoCompletenessItem[] = [
  {
    id: 'front-photo',
    label: 'Front View 이미지',
    stepId: 'photos',
    priority: 'strong',
    targetId: 'product-front-photo',
    isCompleted: () => frontPhotos.value.length > 0,
  },
  {
    id: 'back-photo',
    label: 'Back View 이미지',
    stepId: 'photos',
    priority: 'strong',
    targetId: 'product-back-photo',
    isCompleted: () => backPhotos.value.length > 0,
  },
  {
    id: 'name',
    label: '상품명',
    stepId: 'photos',
    priority: 'strong',
    targetId: 'product-registration-name',
    isCompleted: () => Boolean(draft.name.trim()),
  },
  {
    id: 'ai-quality-check',
    label: 'AI 품질 검증',
    stepId: 'condition',
    priority: 'strong',
    targetId: 'ai-quality-title',
    isCompleted: () => isAiQualityCheckSettled.value,
  },
  {
    id: 'sale-type',
    label: '판매 방식',
    stepId: 'pricing',
    priority: 'strong',
    targetId: 'sale-type-title',
    isCompleted: () => Boolean(draft.saleType),
  },
  {
    id: 'price',
    label: '가격',
    stepId: 'pricing',
    priority: 'strong',
    targetId: 'sale-type-title',
    isCompleted: () =>
      draft.saleType === 'DIRECT'
        ? isPositivePrice(draft.directSalePrice)
        : draft.saleType === 'AUCTION',
  },
  {
    id: 'description',
    label: '상품 설명',
    stepId: 'photos',
    priority: 'strong',
    targetId: 'product-registration-description',
    isCompleted: () => Boolean(draft.description.trim()),
  },
  {
    id: 'category',
    label: '카테고리',
    stepId: 'photos',
    priority: 'strong',
    targetId: 'product-registration-category-major',
    isCompleted: () => isCategorySelectionComplete.value,
  },
  {
    id: 'size',
    label: '사이즈',
    stepId: 'photos',
    priority: 'strong',
    targetId: 'product-registration-size',
    isCompleted: () => Boolean(draft.size),
  },
  {
    id: 'measurements',
    label: '실측 정보',
    stepId: 'photos',
    priority: 'strong',
    targetId: 'product-registration-measurements',
    isCompleted: isMeasurementInfoCompleted,
  },
  {
    id: 'condition-grade',
    label: '상품 상태',
    stepId: 'condition',
    priority: 'strong',
    targetId: 'condition-grade-title',
    isCompleted: () => Boolean(draft.conditionGrade),
  },
  {
    id: 'defect-info',
    label: '하자 정보',
    stepId: 'condition',
    priority: 'strong',
    targetId: 'seller-defect-title',
    isCompleted: isDefectInfoCompleted,
  },
  {
    id: 'color',
    label: '색상',
    stepId: 'photos',
    priority: 'strong',
    targetId: 'product-registration-color',
    isCompleted: () => Boolean(draft.color),
  },
  {
    id: 'brand',
    label: '브랜드',
    stepId: 'photos',
    priority: 'recommended',
    targetId: 'product-registration-brand',
    isCompleted: () => Boolean(draft.brand.trim()),
  },
  {
    id: 'material',
    label: '소재',
    stepId: 'photos',
    priority: 'recommended',
    targetId: 'product-registration-material',
    isCompleted: () => Boolean(draft.material.trim()),
  },
]

const completenessItemLabels: Record<string, string> = {
  name: '상품명',
  description: '상품 설명',
  color: '색상',
  brand: '브랜드',
  category: '카테고리',
  size: '사이즈',
  material: '소재',
  measurements: '실측',
}

const productInfoCompletenessItems = computed<ProductInfoCompletenessItem[]>(() => [
  {
    id: 'photos',
    label: '이미지',
    stepId: 'photos',
    priority: 'strong',
    targetId: 'product-front-photo',
    isCompleted: () => isPhotoStepValid.value,
  },
  ...Object.entries(completenessItemLabels).map(([id, label]) => {
    const item = completenessItems.find((completenessItem) => completenessItem.id === id)

    return {
      ...item,
      id,
      label,
      isCompleted: item?.isCompleted ?? (() => false),
      priority: item?.priority ?? 'recommended',
      stepId: item?.stepId ?? 'photos',
      targetId: item?.targetId ?? '',
    } satisfies ProductInfoCompletenessItem
  }),
  {
    id: 'condition-grade',
    label: '상품 상태',
    stepId: 'condition',
    priority: 'strong',
    targetId: 'condition-grade-title',
    isCompleted: () => Boolean(draft.conditionGrade),
  },
  {
    id: 'ai-quality',
    label: 'AI 품질 검증',
    stepId: 'condition',
    priority: 'strong',
    targetId: 'ai-quality-title',
    isCompleted: () => isAiQualityCheckSettled.value,
  },
  {
    id: 'price',
    label: '가격',
    stepId: 'pricing',
    priority: 'strong',
    targetId: 'sale-type-title',
    isCompleted: () =>
      draft.saleType === 'DIRECT'
        ? isPositivePrice(draft.directSalePrice)
        : draft.saleType === 'AUCTION',
  },
])

const basicInfoCompletenessItems = computed(() =>
  productInfoCompletenessItems.value.filter((item) =>
    [
      'photos',
      'name',
      'description',
      'color',
      'brand',
      'category',
      'size',
      'material',
      'measurements',
    ].includes(item.id),
  ),
)
const isBasicInfoCompletenessComplete = computed(() =>
  basicInfoCompletenessItems.value.every((item) => item.isCompleted()),
)

const completedCompletenessItems = computed(() =>
  productInfoCompletenessItems.value.filter((item) => item.isCompleted()),
)
const incompleteCompletenessItems = computed(() =>
  productInfoCompletenessItems.value.filter((item) => !item.isCompleted()),
)
const productInfoCompletenessPercent = computed(() =>
  Math.round((completedCompletenessItems.value.length / productInfoCompletenessItems.value.length) * 100),
)
const productInfoCompletenessMessage = computed(() => {
  const percent = productInfoCompletenessPercent.value

  if (percent < 40) {
    return '상품을 더 믿고 선택할 수 있도록 정보를 추가해 주세요.'
  }

  if (percent < 70) {
    return '상품 정보가 차근차근 채워지고 있어요.'
  }

  if (percent < 100) {
    return '거의 완성됐어요. 몇 가지 정보만 더 추가해 보세요.'
  }

  return '상품 정보가 충분히 작성됐어요.'
})
const visibleCompletenessItems = computed(() =>
  [...completedCompletenessItems.value, ...incompleteCompletenessItems.value],
)

const findOptionLabel = (options: { id: string; label: string }[], id: string) =>
  options.find((option) => option.id === id)?.label ?? ''

const selectedColorLabel = computed(
  () => findOptionLabel(PRODUCT_REGISTRATION_COLOR_OPTIONS, draft.color) || '-',
)

const selectedCategoryLabel = computed(() => {
  const selectedOption = [...majorCategoryOptions.value, ...minorCategoryOptions.value].find(
    (option) => option.id === draft.categoryId,
  )
  const selectedCategory = categories.value.find((category) => String(category.id) === draft.categoryId)

  return selectedOption?.label || selectedCategory?.name || '-'
})

const selectedConditionGradeLabel = computed(() =>
  findOptionLabel(PRODUCT_REGISTRATION_CONDITION_OPTIONS, draft.conditionGrade) || '-',
)

const selectedSaleTypeLabel = computed(() =>
  findOptionLabel(PRODUCT_REGISTRATION_SALE_TYPE_OPTIONS, draft.saleType) || '-',
)

const selectedPriceLabel = computed(() => {
  if (draft.saleType === 'DIRECT' && isPositivePrice(draft.directSalePrice)) {
    return formatPrice(Number(draft.directSalePrice))
  }

  if (draft.saleType === 'AUCTION') {
    return '경매 예정'
  }

  return '-'
})

const selectedMeasurementSummary = computed(() => {
  const values = activeMeasurementFields.value
    .map((field) => {
      const value = normalizeMeasurementValue(draft.measurements[field.id] ?? '')

      return value ? `${field.label} ${value}cm` : ''
    })
    .filter(Boolean)

  return values.length ? values.join(', ') : '-'
})

const selectedDefectSummary = computed(() => {
  if (draft.hasDefect === false) return '하자 없음'
  if (draft.hasDefect === true) return draft.sellerDefectDescription.trim() || '하자 있음'

  return '-'
})

const selectedAiQualitySummary = computed(() => {
  if (draft.aiQualityStatus === 'completed' && areAllAiPhotosConfirmed.value) {
    return `${draft.aiPhotoResults.length}개 사진 확인 완료`
  }
  if (draft.aiQualityStatus === 'completed') return '확인 대기 중'
  if (draft.aiQualityStatus === 'failed') return '검증 실패'
  if (draft.aiQualityStatus === 'loading') return '검증 중'

  return '-'
})

const editRegistrationStep = (stepId: ProductRegistrationStepId) => {
  const stepIndex = PRODUCT_REGISTRATION_STEPS.findIndex((step) => step.id === stepId)

  if (stepIndex < 0) {
    return
  }

  currentStepIndex.value = stepIndex
  scrollToPageTop()
}

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

const resetAiModelSettings = () => {
  draft.aiModelEnabled = false
  draft.aiModelGender = null
  aiModelStepTouched.value = false
}

const selectAiModelUsage = (enabled: boolean) => {
  if (enabled && !isAiModelSettingsAvailable.value) {
    return
  }

  draft.aiModelEnabled = enabled
  aiModelStepTouched.value = true

  if (!enabled) {
    draft.aiModelGender = null
  }
}

const selectAiModelGender = (gender: ProductRegistrationAiModelGender) => {
  if (!draft.aiModelEnabled || !isAiModelSettingsAvailable.value) {
    return
  }

  draft.aiModelGender = gender
  aiModelStepTouched.value = true
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

    if (role === 'front') {
      selectRepresentativePhoto(validPhotos[0].id)
    } else if (draft.representativePhotoId && !draft.photos.some((photo) => photo.id === draft.representativePhotoId)) {
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

  if (!isAiModelSettingsAvailable.value) {
    resetAiModelSettings()
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

const moveAiResult = (direction: -1 | 1) => {
  if (draft.aiPhotoResults.length === 0) {
    return
  }

  currentAiResultIndex.value =
    (currentAiResultIndex.value + direction + draft.aiPhotoResults.length) %
    draft.aiPhotoResults.length
}

const toggleAiDefectCandidate = (findingId: string) => {
  if (!currentAiResult.value || currentAiResult.value.confirmed) {
    return
  }

  currentAiResult.value.findings = currentAiResult.value.findings.map((finding) => ({
    ...finding,
    isActualDefect: finding.id === findingId ? !finding.isActualDefect : finding.isActualDefect,
  }))
}

const confirmCurrentAiPhoto = () => {
  if (!currentAiResult.value) {
    return
  }

  currentAiResult.value.confirmed = true
}

const editCurrentAiPhotoResult = () => {
  if (!currentAiResult.value) {
    return
  }

  currentAiResult.value.confirmed = false
}

const resetAiAnalysis = () => {
  draft.aiQualityStatus = 'idle'
  draft.aiPhotoResults = []
  draft.aiCategorySuggestion = null
  draft.aiColorSuggestion = null
  currentAiResultIndex.value = 0
}

// AI가 채운 값을 사용자가 이미 직접 고른 뒤라면 덮어쓰지 않는다.
const applyAiCategorySuggestion = (category: { majorId: string; minorId: string } | null) => {
  if (!category) {
    draft.aiCategorySuggestion = null
    return
  }

  draft.aiCategorySuggestion = { ...category, status: 'completed' }

  if (basicStepTouched.categoryId) {
    return
  }

  categoryMajorId.value = category.majorId
  draft.categoryId = category.minorId
}

const applyAiColorSuggestion = (color: { colorId: string } | null) => {
  if (!color) {
    draft.aiColorSuggestion = null
    return
  }

  draft.aiColorSuggestion = { ...color, status: 'completed' }

  if (basicStepTouched.color) {
    return
  }

  draft.color = color.colorId
}

// front/back 사진이 모두 갖춰지면(또는 다시 바뀌면) 자동으로 도는 AI 분석 —
// 사용자가 누르는 확인 버튼은 더 이상 없다.
const triggerAiPhotoAnalysis = async () => {
  const frontPhoto = frontPhotos.value[0]
  const backPhoto = backPhotos.value[0]

  if (!frontPhoto?.file || !backPhoto?.file) {
    resetAiAnalysis()
    return
  }

  draft.aiQualityStatus = 'loading'

  try {
    const result = await analyzeRegistrationPhotos(frontPhoto.file, backPhoto.file)

    draft.aiPhotoResults = [
      { photoId: frontPhoto.id, findings: result.quality.front, confirmed: false },
      { photoId: backPhoto.id, findings: result.quality.back, confirmed: false },
    ]
    currentAiResultIndex.value = 0
    draft.aiQualityStatus = 'completed'

    applyAiCategorySuggestion(result.category)
    applyAiColorSuggestion(result.color)
  } catch (error) {
    console.error('[ProductRegistrationPage] AI 분석 실패', error)
    draft.aiQualityStatus = 'failed'
    draft.aiPhotoResults = []
    draft.aiCategorySuggestion = null
    draft.aiColorSuggestion = null
  }
}

// front/back 사진의 id(=파일이 바뀌면 새로 생성됨)를 감시해, 사진이 갖춰지거나
// 다른 사진으로 교체될 때마다 AI 분석을 다시 트리거한다.
const aiTriggerPhotoKey = computed(
  () => `${frontPhotos.value[0]?.id ?? ''}|${backPhotos.value[0]?.id ?? ''}`,
)

watch(aiTriggerPhotoKey, () => {
  if (isPhotoStepValid.value) {
    void triggerAiPhotoAnalysis()
  } else {
    resetAiAnalysis()
  }
})

const markCurrentStepTouched = () => {
  if (currentStep.value.id === 'photos') {
    photoStepTouched.value = true
    aiModelStepTouched.value = draft.aiModelEnabled

    if (canShowBasicInfoSection.value) {
      basicStepTouched.name = true
      basicStepTouched.brand = true
      basicStepTouched.color = true
      basicStepTouched.categoryId = true
    }

    if (canShowAttributesSection.value) {
      attributesStepTouched.size = true
      activeMeasurementFields.value.forEach((field) => {
        attributesStepTouched.measurements[field.id] = true
      })
    }

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
    return
  }

  if (currentStep.value.id === 'pricing') {
    pricingStepTouched.saleType = true
    pricingStepTouched.directSalePrice = true
  }
}

const scrollToPageTop = () => {
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

const moveToPreviousStep = () => {
  if (isFirstStep.value || hasRegistrationSubmitted.value) {
    return
  }

  currentStepIndex.value -= 1
  scrollToPageTop()
}

const sleep = (ms: number) => new Promise<void>((resolve) => window.setTimeout(resolve, ms))

// AI 착용컷 생성 상태를 완료 화면에서 폴링한다. 대표 이미지 등록 시점에 BE가 job을
// 트리거하므로, 상품 생성 직후에는 아직 NONE/PENDING일 수 있다 — 완료·실패까지 반복
// 조회한다. 실패해도 상품 등록 자체는 이미 끝난 상태라 조용히 멈춘다(보조 기능).
const pollAiModelCutStatus = async (productId: string) => {
  const token = ++aiModelCutPollToken
  const deadline = Date.now() + AI_MODEL_CUT_POLL_TIMEOUT_MS

  while (Date.now() < deadline) {
    if (token !== aiModelCutPollToken) return

    try {
      const result = await getProductAiModelCutStatus(Number(productId))
      if (token !== aiModelCutPollToken) return

      aiModelCutStatus.value = result.status
      aiModelCutImageUrl.value = result.imageUrl

      if (result.status === 'COMPLETED' || result.status === 'FAILED' || result.status === 'NONE') {
        return
      }
    } catch {
      // 일시적 오류일 수 있다 — 다음 폴링에서 재시도, 화면 상태는 건드리지 않는다.
    }

    await sleep(AI_MODEL_CUT_POLL_INTERVAL_MS)
  }
}

const proceedToNextStep = async (skipCompletenessPrompt = false) => {
  if (isSubmittingRegistration.value) {
    return
  }

  markCurrentStepTouched()

  if (isCompleteStep.value && hasRegistrationSubmitted.value) {
    return
  }

  if (!canMoveCurrentStepNext.value) {
    return
  }

  if (
    !skipCompletenessPrompt &&
    currentStep.value.id === 'photos' &&
    !isBasicInfoCompletenessComplete.value
  ) {
    isCompletenessPromptOpen.value = true
    return
  }

  if (isSubmitStep.value) {
    registrationSubmitError.value = ''
    isSubmittingRegistration.value = true

    try {
      const submitResult = await submitProductRegistrationDraft(draft, {
        brands: brands.value,
        categories: categories.value,
      })
      registeredProductId.value = submitResult.productId

      if (draft.aiModelEnabled) {
        aiModelCutStatus.value = 'PENDING'
        aiModelCutImageUrl.value = null
        void pollAiModelCutStatus(submitResult.productId)
      }
    } catch (error) {
      registrationSubmitError.value = normalizeApiError(error).message
      isSubmittingRegistration.value = false
      return
    }

    isSubmittingRegistration.value = false

    if (isCompleteStep.value) {
      scrollToPageTop()
      return
    }
  }

  currentStepIndex.value += 1
  scrollToPageTop()
}

const moveToNextStep = () => {
  void proceedToNextStep()
}

const continueCompletenessInput = () => {
  isCompletenessPromptOpen.value = false
}

const skipCompletenessInput = () => {
  isCompletenessPromptOpen.value = false
  void proceedToNextStep(true)
}

const cancelRegistration = () => {
  router.push(ROUTE_PATHS.PRODUCT_LIST)
}

const resetRegistrationDraft = () => {
  draft.photos.forEach((photo) => {
    revokePhotoPreviewUrl(photo)
  })
  Object.assign(draft, createInitialDraft())
  photoStepTouched.value = false
  aiModelStepTouched.value = false
  photoUploadError.value = ''
  basicStepTouched.name = false
  basicStepTouched.brand = false
  basicStepTouched.color = false
  basicStepTouched.categoryId = false
  attributesStepTouched.size = false
  attributesStepTouched.measurements = {}
  conditionStepTouched.conditionGrade = false
  conditionStepTouched.hasDefect = false
  conditionStepTouched.sellerDefectDescription = false
  pricingStepTouched.saleType = false
  pricingStepTouched.directSalePrice = false
  currentAiResultIndex.value = 0
  registeredProductId.value = ''
  isSubmittingRegistration.value = false
  registrationSubmitError.value = ''
  isCompletenessPromptOpen.value = false
  aiModelCutPollToken += 1
  aiModelCutStatus.value = 'NONE'
  aiModelCutImageUrl.value = null
}

const continueRegistration = () => {
  resetRegistrationDraft()
  currentStepIndex.value = 0
  scrollToPageTop()
}

const moveToRegisteredProduct = () => {
  router.push({ name: ROUTE_NAMES.PRODUCT_DETAIL, params: { productId: registeredProductId.value || 'preview' } })
}

const loadProductMasterData = async () => {
  try {
    const [brandResponse, categoryResponse] = await Promise.all([getBrands(), getCategories()])

    brands.value = brandResponse
    categories.value = categoryResponse
  } catch {
    brands.value = []
    categories.value = []
  }
}

onMounted(() => {
  void loadProductMasterData()
})

onBeforeUnmount(() => {
  aiModelCutPollToken += 1
  draft.photos.forEach((photo) => {
    revokePhotoPreviewUrl(photo)
  })
})
</script>

<template>
  <DefaultLayout content-max-width="1280px">
    <section class="product-registration" aria-label="상품 등록">
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
            <span>{{ index < currentStepIndex ? '✓' : index + 1 }}</span>
            <strong>{{ step.label }}</strong>
          </li>
        </ol>
      </nav>

      <div
        class="product-registration__body"
        :class="{ 'product-registration__body--centered': isCompleteStep }"
      >
        <section class="product-registration__panel" :aria-labelledby="`${currentStep.id}-title`">
          <h2 :id="`${currentStep.id}-title`">{{ currentStep.label }}</h2>

          <aside
            v-if="canShowCompletenessPanel"
            class="product-registration__completeness product-registration__completeness--mobile"
            aria-labelledby="product-info-completeness-mobile-title"
          >
            <div class="product-registration__completeness-header">
              <h3 id="product-info-completeness-mobile-title">상품 정보 완성도</h3>
              <strong>{{ productInfoCompletenessPercent }}%</strong>
            </div>
            <div class="product-registration__progress" aria-hidden="true">
              <span :style="{ width: `${productInfoCompletenessPercent}%` }" />
            </div>
            <p>{{ productInfoCompletenessMessage }}</p>
            <div class="product-registration__completeness-list">
              <strong>입력 현황</strong>
              <ul>
                <li
                  v-for="item in visibleCompletenessItems"
                  :key="item.id"
                  :class="{ 'product-registration__completeness-item--done': item.isCompleted() }"
                >
                  <span aria-hidden="true">{{ item.isCompleted() ? '✓' : '○' }}</span>
                  {{ item.label }}
                </li>
              </ul>
            </div>
          </aside>

          <div v-if="currentStep.id === 'photos'" class="product-registration__photo-step">
            <div class="product-registration__photo-required-row">
              <ProductPhotoUploader
                id="product-front-photo"
                class="product-registration__photo-uploader"
                title="상품 이미지 1"
                :description="'의류는 앞면을,\n그 외 상품은 전체 형태가 잘 보이도록 촬영해 주세요.'"
                required
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
                class="product-registration__photo-uploader"
                title="상품 이미지 2"
                :description="'의류는 뒷면을,\n그 외 상품은 다른 각도에서 촬영해 주세요.'"
                required
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
            </div>

            <ProductPhotoUploader
              id="product-additional-photo"
              class="product-registration__photo-uploader"
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

            <p v-if="photoUploadError" class="product-registration__field-error" role="alert">
              {{ photoUploadError }}
            </p>
          </div>

          <section
            v-if="currentStep.id === 'photos'"
            class="product-registration__section product-registration__ai-model"
            :class="{ 'product-registration__ai-model--disabled': !isAiModelSettingsAvailable }"
            aria-labelledby="product-registration-ai-model-title"
          >
            <div class="product-registration__section-header">
              <div>
                <h3 id="product-registration-ai-model-title">AI 착용컷 설정</h3>
                <p>
                  업로드한 상품 사진을 바탕으로 AI 마네킹 착용 이미지를 생성해
                  상품 상세 페이지에 추가로 보여줄 수 있어요.
                </p>
              </div>
            </div>

            <p
              v-if="!isAiModelSettingsAvailable"
              class="product-registration__ai-model-disabled-message"
            >
              앞면과 뒷면 이미지를 모두 등록하면 AI 착용컷을 설정할 수 있어요.
            </p>

            <div
              class="product-registration__segmented"
              role="radiogroup"
              aria-label="AI 착용컷 사용 여부"
            >
              <button
                type="button"
                class="product-registration__option"
                :class="{ 'product-registration__option--selected': !draft.aiModelEnabled }"
                :disabled="!isAiModelSettingsAvailable"
                :aria-pressed="!draft.aiModelEnabled"
                @click="selectAiModelUsage(false)"
              >
                사용 안 함
              </button>
              <button
                type="button"
                class="product-registration__option"
                :class="{ 'product-registration__option--selected': draft.aiModelEnabled }"
                :disabled="!isAiModelSettingsAvailable"
                :aria-pressed="draft.aiModelEnabled"
                @click="selectAiModelUsage(true)"
              >
                사용함
              </button>
            </div>

            <div v-if="draft.aiModelEnabled" class="product-registration__ai-model-choice">
              <span>AI 모델 선택</span>
              <div
                class="product-registration__segmented"
                role="radiogroup"
                aria-label="AI 모델 선택"
              >
                <button
                  type="button"
                  class="product-registration__option"
                  :class="{ 'product-registration__option--selected': draft.aiModelGender === 'FEMALE' }"
                  :aria-pressed="draft.aiModelGender === 'FEMALE'"
                  @click="selectAiModelGender('FEMALE')"
                >
                  여성
                </button>
                <button
                  type="button"
                  class="product-registration__option"
                  :class="{ 'product-registration__option--selected': draft.aiModelGender === 'MALE' }"
                  :aria-pressed="draft.aiModelGender === 'MALE'"
                  @click="selectAiModelGender('MALE')"
                >
                  남성
                </button>
              </div>
              <span
                v-if="aiModelStepError"
                class="product-registration__field-error"
                role="alert"
              >
                {{ aiModelStepError }}
              </span>
              <p class="product-registration__field-hint">
                AI 착용컷은 실제 착용 사진이 아닌 AI 생성 예시 이미지이며,
                상품 상세 페이지에서 보조 이미지로 표시돼요.
              </p>
            </div>
          </section>

          <form
            v-if="currentStep.id === 'photos' && canShowBasicInfoSection"
            class="product-registration__form"
            aria-label="상품 기본 정보 입력"
          >
            <p class="product-registration__optional-note">
              모든 항목은 선택 사항이에요. 정보가 많을수록 구매자가 상품을 쉽게 찾고 판단하는 데 도움이 돼요.
            </p>

            <label class="product-registration__field" for="product-registration-name">
              <span>
                상품명
                <span class="product-registration__required" aria-hidden="true"> * </span>
                <span class="product-registration__required-text"> 필수 입력 </span>
              </span>
              <input
                id="product-registration-name"
                v-model="draft.name"
                type="text"
                maxlength="60"
                placeholder="예: 90s 오버핏 데님 재킷"
                required
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

            <label class="product-registration__field" for="product-registration-description">
              <span>
                상품 설명
              </span>
              <p class="product-registration__field-hint">
                상품의 특징과 착용감 등을 알려주면 구매자가 상품을 이해하는 데 도움이 돼요.
              </p>
              <textarea
                id="product-registration-description"
                v-model="draft.description"
                maxlength="500"
                rows="4"
                placeholder="상품의 특징, 착용감, 구매자에게 알리고 싶은 내용을 입력해 주세요."
              />
            </label>

            <div class="product-registration__form-grid">
              <label class="product-registration__field" for="product-registration-color">
                <span>
                  색상
                  <span class="product-registration__required" aria-hidden="true"> * </span>
                  <span class="product-registration__required-text"> 필수 입력 </span>
                  <span v-if="isColorAiSuggested" class="product-registration__ai-badge">AI 추천</span>
                </span>
                <p class="product-registration__field-hint">
                  구매자가 색상 필터로 상품을 찾는 데 활용돼요.
                </p>
                <select
                  id="product-registration-color"
                  class="product-registration__select"
                  v-model="draft.color"
                  required
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

              <label class="product-registration__field" for="product-registration-brand">
                <span>
                  브랜드
                </span>
                <p class="product-registration__field-hint">
                  브랜드 검색과 필터에 활용돼요.
                </p>
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
            </div>

            <div class="product-registration__form-grid">
              <label class="product-registration__field" for="product-registration-category-major">
                <span>
                  카테고리 대분류
                  <span class="product-registration__required" aria-hidden="true"> * </span>
                  <span class="product-registration__required-text"> 필수 입력 </span>
                  <span v-if="isCategoryAiSuggested" class="product-registration__ai-badge">AI 추천</span>
                </span>
                <p class="product-registration__field-hint">
                  정확한 카테고리는 구매자가 상품을 쉽게 찾는 데 도움이 돼요.
                </p>
                <select
                  id="product-registration-category-major"
                  class="product-registration__select"
                  v-model="categoryMajorId"
                  required
                  :disabled="majorCategoryOptions.length === 0"
                  :aria-invalid="basicStepErrors.categoryId ? 'true' : 'false'"
                  aria-describedby="product-registration-category-error"
                  @change="updateMajorCategory"
                  @blur="basicStepTouched.categoryId = true"
                >
                  <option value="">대분류 선택</option>
                  <option
                    v-for="option in majorCategoryOptions"
                    :key="option.id"
                    :value="option.id"
                  >
                    {{ option.label }}
                  </option>
                </select>
              </label>

              <label class="product-registration__field" for="product-registration-category-minor">
                <span>
                  카테고리 소분류
                  <span class="product-registration__required" aria-hidden="true"> * </span>
                  <span class="product-registration__required-text"> 필수 입력 </span>
                </span>
                <p class="product-registration__field-hint product-registration__field-hint--spacer" aria-hidden="true">
                  정확한 카테고리는 구매자가 상품을 쉽게 찾는 데 도움이 돼요.
                </p>
                <select
                  id="product-registration-category-minor"
                  class="product-registration__select"
                  v-model="draft.categoryId"
                  required
                  :disabled="!categoryMajorId || minorCategoryOptions.length === 0"
                  :aria-invalid="basicStepErrors.categoryId ? 'true' : 'false'"
                  aria-describedby="product-registration-category-error"
                  @change="updateMinorCategory"
                  @blur="basicStepTouched.categoryId = true"
                >
                  <option value="">소분류 선택</option>
                  <option
                    v-for="option in minorCategoryOptions"
                    :key="option.id"
                    :value="option.id"
                  >
                    {{ option.label }}
                  </option>
                </select>
              </label>
            </div>

            <span
              v-if="basicStepErrors.categoryId"
              id="product-registration-category-error"
              class="product-registration__field-error"
              role="alert"
            >
              {{ basicStepErrors.categoryId }}
            </span>
          </form>

          <form
            v-if="currentStep.id === 'photos' && canShowAttributesSection"
            class="product-registration__form"
            aria-label="상품 사이즈와 소재 입력"
          >
            <div class="product-registration__form-grid">
              <label class="product-registration__field" for="product-registration-size">
                <span>
                  사이즈
                </span>
                <p class="product-registration__field-hint">
                  구매자가 상품의 착용 크기를 판단하는 데 도움이 돼요.
                </p>
                <select
                  id="product-registration-size"
                  class="product-registration__select"
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
                <span>
                  소재
                </span>
                <p class="product-registration__field-hint">
                  구매자가 계절감과 착용감을 판단하는 데 도움이 돼요.
                </p>
                <input
                  id="product-registration-material"
                  v-model="draft.material"
                  type="text"
                  maxlength="60"
                  placeholder="예: 면 100%, 울 80%"
                />
              </label>
            </div>

            <fieldset
              id="product-registration-measurements"
              class="product-registration__fieldset"
            >
              <legend>
                실측 정보
              </legend>
              <p>
                실제 크기를 알려주면 사이즈 문의와 구매 후 불일치를 줄이는 데 도움이 돼요.
              </p>

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
            <p class="product-registration__optional-note">
              모든 항목은 선택 사항이에요. 정보가 많을수록 구매자가 상품을 쉽게 찾고 판단하는 데 도움이 돼요.
            </p>

            <section class="product-registration__section" aria-labelledby="condition-grade-title">
              <h3 id="condition-grade-title">
                상품 상태
              </h3>
              <p class="product-registration__field-hint">
                현재 상품 상태를 정확하게 알려주면 구매 판단에 도움이 돼요.
              </p>
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
              <h3 id="seller-defect-title">
                상품 하자
              </h3>
              <p class="product-registration__field-hint">
                오염이나 손상 정보를 미리 알려주면 거래 과정의 오해를 줄일 수 있어요.
              </p>
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
                  <p>Front View와 Back View 사진을 기준으로 AI가 자동으로 검증합니다.</p>
                </div>
              </div>

              <div v-if="draft.aiQualityStatus === 'loading'" class="product-registration__ai-empty" role="status">
                <span class="product-registration__ai-spinner" aria-hidden="true" />
                <strong>AI가 사진을 검증하고 있습니다…</strong>
                <p>잠시만 기다려 주세요.</p>
              </div>

              <div
                v-else-if="draft.aiQualityStatus === 'failed'"
                class="product-registration__ai-empty"
                role="alert"
              >
                <strong>AI 품질 검증을 완료하지 못했습니다.</strong>
                <p>일시적인 오류일 수 있어요. 상품 상태는 아래 항목에서 직접 알려주세요.</p>
              </div>

              <div
                v-else-if="draft.aiQualityStatus === 'idle'"
                class="product-registration__ai-empty"
                role="status"
              >
                <strong>AI 품질 검증 결과가 없습니다.</strong>
                <p>Front View와 Back View 사진을 등록하면 자동으로 검증이 시작됩니다.</p>
              </div>

              <div v-else-if="currentAiResult && currentAiPhoto" class="product-registration__ai-result">
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
                    {{ currentAiPhoto.role === 'front' ? 'Front View' : 'Back View' }}
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

                <div class="product-registration__ai-result-content">
                  <div class="product-registration__ai-image">
                    <img :src="currentAiPhoto.previewUrl" :alt="`${currentAiPhoto.fileName} AI 품질 검증 결과`" />
                    <span
                      v-for="finding in currentAiResult.findings"
                      :key="finding.id"
                      class="product-registration__ai-box"
                      :class="{ 'product-registration__ai-box--excluded': !finding.isActualDefect }"
                      :style="{
                        left: `${finding.box.x}%`,
                        top: `${finding.box.y}%`,
                        width: `${finding.box.width}%`,
                        height: `${finding.box.height}%`,
                      }"
                    >
                      {{ finding.labelNumber }}
                    </span>
                  </div>

                  <div class="product-registration__ai-cards">
                    <p v-if="currentAiResult.findings.length === 0" class="product-registration__ai-no-findings">
                      이상 소견이 발견되지 않았습니다.
                    </p>
                    <article
                      v-for="finding in currentAiResult.findings"
                      :key="finding.id"
                      class="product-registration__ai-card"
                      :class="{ 'product-registration__ai-card--excluded': !finding.isActualDefect }"
                    >
                      <div>
                        <strong>{{ finding.labelNumber }}번</strong>
                        <p>{{ finding.description }}</p>
                      </div>
                      <button
                        type="button"
                        :disabled="currentAiResult.confirmed"
                        @click="toggleAiDefectCandidate(finding.id)"
                      >
                        {{ finding.isActualDefect ? '하자 제외' : '하자로 표시' }}
                      </button>
                    </article>
                  </div>
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

              <p
                v-if="draft.aiQualityStatus === 'completed' && !areAllAiPhotosConfirmed"
                class="product-registration__ai-confirm-hint"
              >
                모든 사진의 결과를 저장해야 다음 단계로 진행할 수 있어요.
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
                <span>
                  판매가
                  <span class="product-registration__required" aria-hidden="true"> * </span>
                  <span class="product-registration__required-text"> 필수 입력 </span>
                </span>
                <span class="product-registration__price-input">
                  <input
                    :value="draft.directSalePrice"
                    inputmode="numeric"
                    pattern="[0-9]*"
                    placeholder="판매가를 입력해 주세요"
                    required
                    @input="updateDirectSalePrice"
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


            </section>
          </form>

          <section
            v-else-if="currentStep.id === 'complete' && !hasRegistrationSubmitted"
            class="product-registration__review"
            aria-labelledby="registration-review-title"
          >
            <div class="product-registration__section-header">
              <div>
                <h3 id="registration-review-title">입력 정보 검증</h3>
                <p>등록 전에 입력한 상품 정보를 한 번 더 확인해 주세요.</p>
              </div>
            </div>

            <article class="product-registration__review-card">
              <div class="product-registration__review-card-header">
                <h4>기본 정보</h4>
                <button
                  class="product-registration__button product-registration__button--secondary"
                  type="button"
                  @click="editRegistrationStep('photos')"
                >
                  정보 수정하기
                </button>
              </div>
              <dl class="product-registration__review-list">
                <div>
                  <dt>이미지</dt>
                  <dd>앞면 {{ frontPhotos.length }}장 / 뒷면 {{ backPhotos.length }}장 / 추가 {{ additionalPhotos.length }}장</dd>
                </div>
                <div>
                  <dt>상품명</dt>
                  <dd>{{ draft.name || '-' }}</dd>
                </div>
                <div>
                  <dt>상품 설명</dt>
                  <dd>{{ draft.description || '-' }}</dd>
                </div>
                <div>
                  <dt>색상</dt>
                  <dd>{{ selectedColorLabel }}</dd>
                </div>
                <div>
                  <dt>브랜드</dt>
                  <dd>{{ draft.brand || '-' }}</dd>
                </div>
                <div>
                  <dt>카테고리</dt>
                  <dd>{{ selectedCategoryLabel }}</dd>
                </div>
              </dl>
            </article>

            <article class="product-registration__review-card">
              <div class="product-registration__review-card-header">
                <h4>사이즈 / 소재</h4>
                <button
                  class="product-registration__button product-registration__button--secondary"
                  type="button"
                  @click="editRegistrationStep('photos')"
                >
                  정보 수정하기
                </button>
              </div>
              <dl class="product-registration__review-list">
                <div>
                  <dt>사이즈</dt>
                  <dd>{{ draft.size || '-' }}</dd>
                </div>
                <div>
                  <dt>소재</dt>
                  <dd>{{ draft.material || '-' }}</dd>
                </div>
                <div>
                  <dt>실측</dt>
                  <dd>{{ selectedMeasurementSummary }}</dd>
                </div>
              </dl>
            </article>

            <article class="product-registration__review-card">
              <div class="product-registration__review-card-header">
                <h4>품질</h4>
                <button
                  class="product-registration__button product-registration__button--secondary"
                  type="button"
                  @click="editRegistrationStep('condition')"
                >
                  정보 수정하기
                </button>
              </div>
              <dl class="product-registration__review-list">
                <div>
                  <dt>상품 상태</dt>
                  <dd>{{ selectedConditionGradeLabel }}</dd>
                </div>
                <div>
                  <dt>하자 정보</dt>
                  <dd>{{ selectedDefectSummary }}</dd>
                </div>
                <div>
                  <dt>AI 품질 검증</dt>
                  <dd>{{ selectedAiQualitySummary }}</dd>
                </div>
              </dl>
            </article>

            <article class="product-registration__review-card">
              <div class="product-registration__review-card-header">
                <h4>가격</h4>
                <button
                  class="product-registration__button product-registration__button--secondary"
                  type="button"
                  @click="editRegistrationStep('pricing')"
                >
                  정보 수정하기
                </button>
              </div>
              <dl class="product-registration__review-list">
                <div>
                  <dt>판매 방식</dt>
                  <dd>{{ selectedSaleTypeLabel }}</dd>
                </div>
                <div>
                  <dt>가격</dt>
                  <dd>{{ selectedPriceLabel }}</dd>
                </div>
              </dl>
            </article>

            <article class="product-registration__review-card">
              <div class="product-registration__review-card-header">
                <h4>AI 착용컷</h4>
                <button
                  class="product-registration__button product-registration__button--secondary"
                  type="button"
                  @click="editRegistrationStep('photos')"
                >
                  정보 수정하기
                </button>
              </div>
              <dl class="product-registration__review-list">
                <div>
                  <dt>사용 여부</dt>
                  <dd>{{ draft.aiModelEnabled ? '사용함' : '사용 안 함' }}</dd>
                </div>
                <div v-if="draft.aiModelEnabled">
                  <dt>AI 모델</dt>
                  <dd>{{ aiModelGenderLabel }}</dd>
                </div>
              </dl>
            </article>
          </section>

          <div
            v-if="currentStep.id === 'complete' && hasRegistrationSubmitted"
            class="product-registration__complete"
            role="status"
          >
            <span class="product-registration__complete-icon" aria-hidden="true">✓</span>
            <h3>상품 등록이 완료되었습니다.</h3>
            <p>등록한 상품을 확인하거나 이어서 새 상품을 등록할 수 있습니다.</p>

            <div
              v-if="draft.aiModelEnabled"
              class="product-registration__ai-model-cut-status"
              role="status"
            >
              <template v-if="aiModelCutStatus === 'PENDING' || aiModelCutStatus === 'PROCESSING'">
                <span class="product-registration__spinner" aria-hidden="true"></span>
                <p>AI 착용컷을 생성하고 있어요. 완료되면 여기에 표시됩니다.</p>
              </template>
              <template v-else-if="aiModelCutStatus === 'COMPLETED' && aiModelCutImageUrl">
                <img
                  :src="aiModelCutImageUrl"
                  alt="AI 착용컷 결과"
                  class="product-registration__ai-model-cut-image"
                />
                <p>AI 착용컷 생성이 완료됐어요.</p>
              </template>
              <template v-else-if="aiModelCutStatus === 'FAILED'">
                <p>AI 착용컷 생성에는 실패했지만, 상품 등록은 정상적으로 완료됐어요.</p>
              </template>
            </div>

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

          <p
            v-if="registrationSubmitError"
            class="product-registration__field-error"
            role="alert"
          >
            {{ registrationSubmitError }}
          </p>

          <div v-if="!hasRegistrationSubmitted" class="product-registration__actions">
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
              :disabled="isFirstStep || isSubmittingRegistration || hasRegistrationSubmitted"
              @click="moveToPreviousStep"
            >
              이전
            </button>
            <button
              class="product-registration__button product-registration__button--primary"
              type="button"
              :disabled="isSubmittingRegistration"
              @click="moveToNextStep"
            >
              {{ nextActionLabel }}
            </button>
          </div>

          <Teleport to="body">
            <div
              v-if="isCompletenessPromptOpen"
              class="product-registration__prompt-backdrop"
              role="presentation"
            >
              <section
                class="product-registration__prompt"
                role="dialog"
                aria-modal="true"
                aria-labelledby="product-registration-completeness-prompt-title"
              >
                <h3 id="product-registration-completeness-prompt-title">
                  상품 정보를 더 채워볼까요?
                </h3>
                <p>
                  사진, 설명, 색상, 브랜드, 카테고리, 사이즈, 소재, 실측 정보가 충분하면
                  구매자가 상품을 더 쉽게 판단할 수 있어요.
                </p>
                <div class="product-registration__prompt-actions">
                  <button
                    class="product-registration__button product-registration__button--secondary"
                    type="button"
                    @click="continueCompletenessInput"
                  >
                    정보 입력 이어하기
                  </button>
                  <button
                    class="product-registration__button product-registration__button--primary"
                    type="button"
                    @click="skipCompletenessInput"
                  >
                    다음
                  </button>
                </div>
              </section>
            </div>
          </Teleport>
        </section>

        <aside
          v-if="canShowCompletenessPanel"
          class="product-registration__completeness product-registration__completeness--desktop"
          aria-labelledby="product-info-completeness-desktop-title"
        >
          <div class="product-registration__completeness-header">
            <h3 id="product-info-completeness-desktop-title">상품 정보 완성도</h3>
            <strong>{{ productInfoCompletenessPercent }}%</strong>
          </div>
          <div class="product-registration__progress" aria-hidden="true">
            <span :style="{ width: `${productInfoCompletenessPercent}%` }" />
          </div>
          <p>{{ productInfoCompletenessMessage }}</p>
          <div class="product-registration__completeness-list">
            <strong>입력 현황</strong>
            <ul>
              <li
                v-for="item in visibleCompletenessItems"
                :key="item.id"
                :class="{ 'product-registration__completeness-item--done': item.isCompleted() }"
              >
                <span aria-hidden="true">{{ item.isCompleted() ? '✓' : '○' }}</span>
                {{ item.label }}
              </li>
            </ul>
          </div>
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

.product-registration__steps ol {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  list-style: none;
}

.product-registration__steps li {
  position: relative;
  display: flex;
  align-items: center;
  flex-direction: column;
  min-width: 0;
  gap: var(--space-2);
  color: var(--color-text-muted);
  text-align: center;
}

.product-registration__steps li:not(:last-child)::after {
  position: absolute;
  top: 17px;
  left: calc(50% + 24px);
  width: calc(100% - 48px);
  height: 2px;
  background: var(--color-border);
  content: '';
}

.product-registration__step--complete:not(:last-child)::after {
  background: var(--color-primary);
}

.product-registration__steps span {
  position: relative;
  z-index: var(--z-layer-1);
  display: grid;
  width: 34px;
  height: 34px;
  border: 1px solid var(--color-border-input);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-muted);
  flex: 0 0 auto;
  font-family: var(--font-mono);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-medium);
  place-items: center;
}

.product-registration__steps strong {
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-snug);
  overflow-wrap: anywhere;
  word-break: keep-all;
}

.product-registration__step--current {
  color: var(--color-text-primary);
}

.product-registration__step--current span,
.product-registration__step--complete span {
  border-color: var(--color-primary);
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

.product-registration__step--current strong {
  color: var(--color-primary);
}

.product-registration__body {
  display: grid;
  align-items: start;
  gap: var(--space-6);
  grid-template-columns: minmax(0, 1fr) minmax(280px, 320px);
}

.product-registration__body--centered {
  justify-content: center;
  grid-template-columns: minmax(0, 1120px);
}

.product-registration__panel {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
}

.product-registration__panel {
  display: grid;
  align-content: start;
  min-height: var(--surface-min-height-lg);
  gap: var(--space-4);
  padding: var(--space-8);
}

.product-registration__panel h2 {
  color: var(--color-text-primary);
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-extrabold);
  line-height: var(--line-height-2xl);
}

.product-registration__completeness {
  display: grid;
  align-content: start;
  gap: var(--space-4);
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
}

.product-registration__completeness--desktop {
  position: sticky;
  top: calc(var(--thumbnail-size-sm) + var(--space-6));
}

.product-registration__completeness--mobile {
  display: none;
}

.product-registration__completeness-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-4);
}

.product-registration__completeness-header h3 {
  color: var(--color-text-primary);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-lg);
}

.product-registration__completeness-header strong {
  color: var(--color-primary);
  font-size: var(--font-size-3xl);
  font-weight: var(--font-weight-extrabold);
  line-height: 34px;
}

.product-registration__progress {
  overflow: hidden;
  height: 8px;
  border-radius: 2px;
  background: var(--color-surface-secondary);
}

.product-registration__progress span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--color-primary);
  transition: width var(--transition-moderate);
}

.product-registration__completeness > p {
  color: var(--color-text-secondary);
  font-size: var(--font-size-button-small);
  line-height: var(--line-height-control);
}

.product-registration__completeness-list {
  display: grid;
  gap: var(--space-3);
}

.product-registration__completeness-list > strong {
  color: var(--color-text-primary);
  font-size: var(--font-size-button-small);
  line-height: var(--line-height-control);
}

.product-registration__completeness-list ul {
  display: grid;
  gap: var(--space-2);
  padding: 0;
  margin: 0;
  list-style: none;
}

.product-registration__completeness-list li {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--color-text-secondary);
  font-size: var(--font-size-button-small);
  line-height: var(--line-height-control);
}

.product-registration__completeness-list li span {
  color: var(--color-text-muted);
  font-weight: var(--font-weight-bold);
}

.product-registration__completeness-item--done {
  color: var(--color-text-primary);
}

.product-registration__completeness-item--done span {
  color: var(--color-primary);
}

.product-registration__completeness .product-registration__button {
  width: 100%;
}

.product-registration__photo-step {
  display: grid;
  gap: var(--space-5);
  margin-top: var(--space-4);
}

.product-registration__photo-required-row {
  display: grid;
  gap: var(--space-4);
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.product-registration__photo-uploader {
  padding: var(--space-4);
}

.product-registration__photo-uploader :deep(.product-photo-uploader__grid) {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.product-registration__photo-required-row .product-registration__photo-uploader :deep(.product-photo-uploader__grid) {
  grid-template-columns: 1fr;
}

.product-registration__photo-uploader :deep(.product-photo-uploader__item img) {
  aspect-ratio: 4 / 3;
}

.product-registration__photo-uploader :deep(.product-photo-uploader__empty) {
  min-height: 104px;
  padding: var(--space-4);
}

.product-registration__field-error {
  color: var(--color-error);
  font-size: var(--font-size-caption);
  line-height: var(--line-height-control);
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
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-control);
}

.product-registration__field .product-registration__required,
.product-registration__section h3 .product-registration__required {
  margin-left: 2px;
  color: var(--color-error);
}

.product-registration__ai-badge {
  margin-left: var(--space-2);
  padding: 1px var(--space-2);
  border-radius: var(--radius-badge);
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-semibold);
}

.product-registration__required-text {
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

.product-registration__field-hint {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  font-style: normal;
  line-height: var(--line-height-snug);
}

.product-registration__field-hint--spacer {
  visibility: hidden;
}

@media (min-width: 961px) {
  .product-registration__field-hint {
    white-space: nowrap;
  }
}

.product-registration__optional-note {
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface-secondary);
  color: var(--color-text-secondary);
  font-size: var(--font-size-button-small);
  line-height: var(--line-height-control);
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
    border-color var(--transition-base),
    box-shadow var(--transition-base);
}

.product-registration__field input,
.product-registration__field select {
  height: var(--button-height-standard);
  padding: 0 var(--space-4);
}

.product-registration__field .product-registration__select {
  appearance: none;
  padding-right: 52px;
  background-image: url("data:image/svg+xml,%3Csvg width='20' height='20' viewBox='0 0 20 20' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M5 7.5L10 12.5L15 7.5' stroke='%23686A64' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
  background-position: right 16px center;
  background-repeat: no-repeat;
  background-size: 20px 20px;
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
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-control);
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
  box-shadow: none;
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
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-body);
}

.product-registration__fieldset > p {
  color: var(--color-text-secondary);
  font-size: var(--font-size-button-small);
  line-height: var(--line-height-control);
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
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-lg);
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
  font-size: var(--font-size-button-small);
  line-height: var(--line-height-control);
}

.product-registration__ai-model {
  margin-top: var(--space-1);
}

.product-registration__ai-model--disabled {
  background: var(--color-surface-secondary);
}

.product-registration__ai-model-disabled-message {
  padding: var(--space-3) var(--space-4);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-control);
  color: var(--color-text-secondary);
  font-size: var(--font-size-button-small);
  line-height: var(--line-height-control);
}

.product-registration__segmented {
  display: grid;
  gap: var(--space-3);
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.product-registration__ai-model-choice {
  display: grid;
  gap: var(--space-3);
}

.product-registration__ai-model-choice > span:first-child {
  color: var(--color-text-primary);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-control);
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

.product-registration__option:disabled {
  border-color: var(--color-border);
  background: var(--color-surface);
  color: var(--color-text-muted);
  cursor: not-allowed;
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
  width: var(--button-height-small);
  height: var(--button-height-small);
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
  width: var(--icon-size-md);
  height: var(--icon-size-md);
}

.product-registration__ai-result-toolbar strong {
  color: var(--color-text-primary);
  text-align: center;
}

.product-registration__ai-result-content {
  display: grid;
  grid-template-columns: minmax(0, 460px) minmax(0, 1fr);
  gap: var(--space-4);
  align-items: start;
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
  border: 2px solid var(--color-error);
  background: rgb(196 61 70 / 12%);
  color: var(--color-error);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-bold);
  line-height: 1;
  place-items: start;
}

.product-registration__ai-box--excluded {
  border-color: var(--color-border-strong);
  background: transparent;
  color: var(--color-text-muted);
}

.product-registration__ai-cards {
  display: grid;
  align-content: start;
  gap: var(--space-2);
}

.product-registration__ai-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--space-2);
  padding: var(--space-3);
  border: 1px solid var(--color-error);
  border-radius: var(--radius-control);
  background: var(--color-surface);
}

.product-registration__ai-card--excluded {
  border-color: var(--color-border);
  opacity: 0.6;
}

.product-registration__ai-no-findings {
  color: var(--color-text-secondary);
  font-size: var(--font-size-caption);
}

.product-registration__ai-card div {
  display: grid;
  gap: var(--space-1);
}

.product-registration__ai-card strong {
  color: var(--color-text-primary);
  font-size: var(--font-size-body);
}

.product-registration__ai-card p {
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
  line-height: var(--line-height-control);
}

.product-registration__ai-card button {
  min-width: 72px;
  height: var(--button-height-small);
  padding: 0 var(--space-2);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-bold);
  white-space: nowrap;
}

.product-registration__ai-card:not(.product-registration__ai-card--excluded) button {
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
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-bold);
}

.product-registration__ai-confirm-hint {
  color: var(--color-text-secondary);
  font-size: var(--font-size-caption);
  text-align: right;
}

.product-registration__ai-empty {
  display: grid;
  gap: var(--space-1);
  min-height: var(--surface-min-height-2xs);
  place-content: center;
  place-items: center;
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

.product-registration__ai-spinner {
  width: var(--badge-height-md);
  height: var(--badge-height-md);
  border: 3px solid var(--color-primary-soft);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: product-registration-ai-spin 900ms linear infinite;
}

@keyframes product-registration-ai-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .product-registration__ai-spinner {
    animation: none;
  }
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
  font-size: var(--font-size-xs);
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
  font-size: var(--font-size-xs);
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
  font-size: var(--font-size-xs);
  line-height: var(--line-height-xs);
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
  font-size: var(--font-size-2xs);
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
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-bold);
}

.product-registration__price-recommendations dd {
  color: var(--color-text-primary);
  font-weight: var(--font-weight-bold);
}

.product-registration__review {
  display: grid;
  gap: var(--space-4);
  margin-top: var(--space-4);
}

.product-registration__review-card {
  display: grid;
  gap: var(--space-4);
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
}

.product-registration__review-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
}

.product-registration__review-card-header h4 {
  color: var(--color-text-primary);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-lg);
}

.product-registration__review-card-header .product-registration__button {
  min-width: 120px;
  height: var(--button-height-small);
  padding: 0 var(--space-3);
  font-size: var(--font-size-caption);
}

.product-registration__review-list {
  display: grid;
  gap: var(--space-3);
}

.product-registration__review-list div {
  display: grid;
  gap: var(--space-3);
  grid-template-columns: 112px minmax(0, 1fr);
}

.product-registration__review-list dt {
  color: var(--color-text-secondary);
  font-size: var(--font-size-button-small);
  line-height: var(--line-height-control);
}

.product-registration__review-list dd {
  min-width: 0;
  color: var(--color-text-primary);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-control);
  overflow-wrap: anywhere;
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
  width: var(--button-height-major);
  height: var(--button-height-major);
  border-radius: 50%;
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  place-items: center;
}

.product-registration__complete h3 {
  color: var(--color-text-primary);
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-extrabold);
  line-height: 30px;
}

.product-registration__complete p {
  max-width: var(--prose-max-width);
  color: var(--color-text-secondary);
  line-height: var(--line-height-body);
}

.product-registration__ai-model-cut-status {
  display: grid;
  justify-items: center;
  gap: var(--space-3);
  width: 100%;
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
}

.product-registration__ai-model-cut-status p {
  max-width: var(--prose-max-width);
  color: var(--color-text-secondary);
  line-height: var(--line-height-body);
}

.product-registration__spinner {
  width: 28px;
  height: 28px;
  border: 3px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: product-registration-spin 0.8s linear infinite;
}

@keyframes product-registration-spin {
  to {
    transform: rotate(360deg);
  }
}

.product-registration__ai-model-cut-image {
  max-width: 220px;
  border-radius: var(--radius-control);
  object-fit: cover;
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

.product-registration__prompt-backdrop {
  position: fixed;
  /* 뷰포트(현재 보이는 화면) 기준으로 항상 중앙에 뜨도록 fixed + inset:0을 쓴다.
     다른 겹침 요소보다 위에 오도록 헤더보다 훨씬 높은 값을 쓴다. */
  z-index: 500;
  display: grid;
  background: rgb(0 0 0 / 28%);
  inset: 0;
  place-items: center;
  padding: var(--space-5);
}

.product-registration__prompt {
  display: grid;
  width: min(100%, 420px);
  gap: var(--space-4);
  padding: var(--space-6);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
  box-shadow: none;
}

.product-registration__prompt h3 {
  color: var(--color-text-primary);
  font-size: var(--font-size-lg-plus);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-lg-plus);
}

.product-registration__prompt p {
  color: var(--color-text-secondary);
  font-size: var(--font-size-button-small);
  line-height: var(--line-height-relaxed);
}

.product-registration__prompt-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
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

@media (max-width: 960px) {
  .product-registration__body {
    grid-template-columns: 1fr;
  }

  .product-registration__completeness--desktop {
    display: none;
  }

  .product-registration__completeness--mobile {
    display: grid;
  }

  .product-registration__actions {
    flex-wrap: wrap;
  }

  .product-registration__photo-required-row,
  .product-registration__form-grid {
    grid-template-columns: 1fr;
  }

  .product-registration__option-grid,
  .product-registration__segmented {
    grid-template-columns: 1fr;
  }

  .product-registration__ai-result-content {
    grid-template-columns: minmax(0, 1fr);
  }

  .product-registration__section-header,
  .product-registration__review-card-header {
    flex-direction: column;
    align-items: stretch;
  }

  .product-registration__review-card-header .product-registration__button {
    width: 100%;
  }

  .product-registration__review-list div {
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
