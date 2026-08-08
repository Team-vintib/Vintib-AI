export type ProductDetailSaleType = 'DIRECT_SALE' | 'AUCTION'

export type ProductDetailSaleStatus =
  'DRAFT' | 'ON_SALE' | 'AUCTION_SCHEDULED' | 'AUCTION_IN_PROGRESS' | 'AUCTION_FAILED' | 'SOLD'

export type AiQualityAnalysisStatus =
  'NOT_REQUESTED' | 'ANALYZING' | 'COMPLETED' | 'NO_FINDINGS' | 'FAILED'

export interface ProductDetailImage {
  id: string
  url: string
  alt: string
  label: string
}

export interface ProductSellerSummary {
  id: number
  nickname: string
  followerCount: number
  productCount: number
}

export interface ProductLinkedLive {
  id: number
  title: string
  startsAt: string
  status: 'LIVE' | 'SCHEDULED'
  thumbnailUrl: string
}

export interface SimilarProductPricePoint {
  id: number
  title: string
  price: number
}

export interface SellerDisclosedDefect {
  title: string
  description: string
}

export interface AiQualityFindingBox {
  // 검수 이미지 위 빨간 네모 위치(프레임 기준 %, 0~100)
  x: number
  y: number
  width: number
  height: number
}

export interface AiQualityFinding {
  id: string
  type: string
  location: string
  description: string
  box?: AiQualityFindingBox
}

export interface AiQualityAnalysisImage {
  id: string
  label: string
  originalImageUrl: string
  originalImageAlt: string
  analyzedImageUrl: string
  analyzedImageAlt: string
  summary: string
  findings: AiQualityFinding[]
}

export interface AiQualityAnalysis {
  status: AiQualityAnalysisStatus
  // 검수 이미지 여러 장(넘겨보기). 이미지별로 원본·검수·설명·findings를 가진다.
  images: AiQualityAnalysisImage[]
  disclaimer: string
}

export type ProductAiModelCutStatus = 'NONE' | 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED'

export interface ProductAiModelCut {
  status: ProductAiModelCutStatus
  imageUrl: string | null
}

export interface ProductDetailViewData {
  id: number
  brand: string
  title: string
  description: string
  category: string
  // 유사 상품 추천을 같은 카테고리로 좁힐 때 쓴다(BE 상세 응답의 categoryId).
  categoryId: number | null
  conditionLabel: string
  sizeLabel: string
  material: string
  color: string
  price: number
  saleType: ProductDetailSaleType
  saleStatus: ProductDetailSaleStatus
  isLiked: boolean
  images: ProductDetailImage[]
  seller: ProductSellerSummary
  linkedLive: ProductLinkedLive | null
  measurements: Record<string, number>
  similarProducts: SimilarProductPricePoint[]
  sellerDisclosedDefects: SellerDisclosedDefect[]
  aiQualityAnalysis: AiQualityAnalysis | null
  aiModelCut: ProductAiModelCut | null
}
