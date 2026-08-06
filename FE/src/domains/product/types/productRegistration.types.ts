import type { ProductConditionGrade } from './productList.types'

export type ProductRegistrationStepId =
  | 'photos'
  | 'basic'
  | 'attributes'
  | 'condition'
  | 'pricing'
  | 'review'
  | 'complete'

export type ProductRegistrationPhotoRole = 'front' | 'back' | 'additional'

export type ProductRegistrationSaleType = 'DIRECT' | 'AUCTION'

export type ProductRegistrationAiModelGender = 'FEMALE' | 'MALE'

// front/back 사진이 갖춰지면 자동으로 도는 AI 분석(카테고리·색상·품질 검증) 공통 상태.
// 사용자가 확인 버튼으로 트리거하지 않으므로 idle→loading→completed/failed 전이만 있다.
export type ProductRegistrationAiPipelineStatus = 'idle' | 'loading' | 'completed' | 'failed'

export interface ProductRegistrationStep {
  id: ProductRegistrationStepId
  label: string
}

export interface ProductRegistrationOption {
  id: string
  label: string
}

export interface ProductRegistrationPhotoDraft {
  id: string
  role: ProductRegistrationPhotoRole
  file: File | null
  previewUrl: string
  fileName: string
  isRepresentative: boolean
}

export type ProductRegistrationMeasurementDraft = Record<string, string>

export interface ProductRegistrationAiFinding {
  id: string
  labelNumber: number
  description: string
  box: {
    x: number
    y: number
    width: number
    height: number
  }
  // AI는 기본 true(하자로 인정)로 채운다 — 사용자가 "하자 제외"를 눌러 false로 뒤집을 수 있다.
  isActualDefect: boolean
}

export interface ProductRegistrationAiPhotoResult {
  photoId: string
  findings: ProductRegistrationAiFinding[]
  // 사용자가 이 사진의 하자 판정을 다 확인하고 "결과 저장"을 눌렀는지 여부.
  confirmed: boolean
}

export interface ProductRegistrationAiCategorySuggestion {
  majorId: string
  minorId: string
  status: ProductRegistrationAiPipelineStatus
}

export interface ProductRegistrationAiColorSuggestion {
  colorId: string
  status: ProductRegistrationAiPipelineStatus
}

export interface ProductRegistrationPriceBucket {
  id: string
  label: string
  productCount: number
}

export interface ProductRegistrationRecommendedPrice {
  grade: ProductConditionGrade
  label: string
  price: number
}

export interface ProductRegistrationDraft {
  photos: ProductRegistrationPhotoDraft[]
  representativePhotoId: string
  name: string
  brand: string
  color: string
  categoryId: string
  description: string
  purchasedAt: string
  purchasedCountry: string
  size: string
  material: string
  measurements: ProductRegistrationMeasurementDraft
  conditionGrade: ProductConditionGrade | ''
  hasDefect: boolean | null
  sellerDefectDescription: string
  aiQualityStatus: ProductRegistrationAiPipelineStatus
  aiPhotoResults: ProductRegistrationAiPhotoResult[]
  aiCategorySuggestion: ProductRegistrationAiCategorySuggestion | null
  aiColorSuggestion: ProductRegistrationAiColorSuggestion | null
  aiModelEnabled: boolean
  aiModelGender: ProductRegistrationAiModelGender | null
  saleType: ProductRegistrationSaleType | ''
  directSalePrice: string
  linkedLiveId: string
}

export interface ProductRegistrationSubmitResult {
  productId: string
  submittedAt: string
}
