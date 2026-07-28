export type ProductDetailSaleType = 'DIRECT_SALE' | 'AUCTION'

export type ProductDetailSaleStatus =
  | 'DRAFT'
  | 'ON_SALE'
  | 'AUCTION_SCHEDULED'
  | 'AUCTION_IN_PROGRESS'
  | 'AUCTION_FAILED'
  | 'SOLD'
  | 'PRIVATE'

export type AiQualityAnalysisStatus =
  | 'NOT_REQUESTED'
  | 'ANALYZING'
  | 'COMPLETED'
  | 'NO_FINDINGS'
  | 'FAILED'

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

export interface SellerDisclosedDefect {
  title: string
  description: string
}

export interface AiQualityFinding {
  id: string
  type: string
  location: string
  description: string
}

export interface AiQualityAnalysis {
  status: AiQualityAnalysisStatus
  originalImageUrl: string
  originalImageAlt: string
  analyzedImageUrl: string
  analyzedImageAlt: string
  summary: string
  findings: AiQualityFinding[]
  disclaimer: string
}

export interface ProductDetailViewData {
  id: number
  brand: string
  title: string
  description: string
  category: string
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
  sellerDisclosedDefects: SellerDisclosedDefect[]
  aiQualityAnalysis: AiQualityAnalysis
}
