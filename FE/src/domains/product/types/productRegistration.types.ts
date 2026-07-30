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

export type ProductRegistrationAiCheckStatus =
  | 'idle'
  | 'analyzing'
  | 'failed'
  | 'noFindings'
  | 'completed'
  | 'regenerating'
  | 'confirmed'

export interface ProductRegistrationStep {
  id: ProductRegistrationStepId
  label: string
  description: string
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
  isRepresentative: boolean
}

export interface ProductRegistrationMeasurementDraft {
  shoulder: string
  chest: string
  sleeve: string
  length: string
}

export interface ProductRegistrationAiDefectCandidate {
  id: string
  labelNumber: number
  description: string
  box: {
    x: number
    y: number
    width: number
    height: number
  }
  isActualDefect: boolean
}

export interface ProductRegistrationAiPhotoResult {
  photoId: string
  status: ProductRegistrationAiCheckStatus
  candidates: ProductRegistrationAiDefectCandidate[]
  regeneratedImageUrl: string
  confirmed: boolean
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
  aiCheckPhotoIds: string[]
  aiPhotoResults: ProductRegistrationAiPhotoResult[]
  saleType: ProductRegistrationSaleType | ''
  directSalePrice: string
  auctionStartPrice: string
  linkedLiveId: string
}

