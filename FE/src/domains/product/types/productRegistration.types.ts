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

export type ProductRegistrationAiDefectType =
  | 'STAIN'
  | 'DIRT_MARK'
  | 'HOLE_TEAR'
  | 'DISCOLORATION'
  | 'PILLING'
  | 'FRAY'

export type ProductRegistrationAiDefectSeverity = 'MINOR' | 'MODERATE' | 'MAJOR'

// docs/requests/BE/041-quality-inspection-integration.md §2, docs/requests/FE/036-quality-finding-bbox-rendering.md의
// findings[] 필드를 그대로 따른다(필드명까지) — BE/AI가 이 형태로 확정했으므로 임의 변형하지 않는다.
export interface ProductRegistrationAiFinding {
  key: string
  defectType: ProductRegistrationAiDefectType
  label: string
  status: 'DETECTED' | 'SUSPECTED'
  imageIndex: number
  no: number
  // 정규화 좌표 [x1, y1, x2, y2] (0~1) — AI가 주는 형태 그대로 보관하고, 렌더링 시에만
  // qualityFindingBox.ts의 toPercentBox()로 {x,y,width,height}%(0~100)로 변환한다.
  bbox: [number, number, number, number]
  confidence: number
  severity: ProductRegistrationAiDefectSeverity
  statementRequired: boolean
  needsSellerReview: boolean
  description: string | null
  // AI 원본 부위 코드(예: "SHOULDER_RIGHT")와, aiSectionLabels.ts로 변환한 한글 라벨.
  section: string
  sectionLabel: string
  // AI가 주는 값이 아니다 — 판매자가 직접 인정/제외한 로컬 상태(기본 true).
  isActualDefect: boolean
}

export interface ProductRegistrationAiPhotoResult {
  photoId: string
  findings: ProductRegistrationAiFinding[]
  // 사용자가 이 사진의 하자 판정을 다 확인하고 "결과 저장"을 눌렀는지 여부.
  confirmed: boolean
  // 이 사진(image_index) 기준 AI 한 줄 요약. 없을 수 있다(웹훅 전이거나 하자 없음 등).
  summary: string | null
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
  // SY043: '상태/하자' 스텝 진입 시 미리 만들어진 실제 DRAFT 상품 id(있으면 최종 제출은
  // PATCH로 나머지 필드만 갱신, 이미지도 재업로드하지 않는다).
  draftProductId: number | null
}

export interface ProductRegistrationSubmitResult {
  productId: string
  submittedAt: string
}
