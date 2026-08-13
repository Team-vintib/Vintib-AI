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

// "동일 상품 시세"(SY046, docs/requests/FE/042 반영) — BE `GET /products/{id}/market-price`.
// matchKey 기준 동일 상품 판정이라, 카테고리 기준인 SimilarProductPricePoint와는 별개 개념이다.
export type ProductMarketPriceKind = 'ASKING' | 'SOLD_DIRECT' | 'SOLD_AUCTION'

export interface ProductMarketPriceItem {
  productId: number
  title: string
  price: number
  priceKind: ProductMarketPriceKind
}

export interface ProductMarketPrice {
  productId: number
  matchKey: string | null
  currentProduct: ProductMarketPriceItem | null
  listings: ProductMarketPriceItem[]
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

// BE가 AI 검수 원본(quality_inspection_result)에서 조립해 내려주는 하자 1건(요청 043 §2).
export interface AiQualityFinding {
  // AI 원본의 고정 식별자. 판매자의 "하자 아님" 표시도 이 key로 주고받는다.
  key: string
  // 이미지 안에서의 순번(1부터). 등록 화면과 번호가 어긋나지 않게 BE가 원본 값을 그대로 준다.
  no: number
  // 하자 종류(한글). AI 원본 label.
  type: string
  // 부위. BE는 원본 코드(COLLAR 등)를 그대로 주므로 aiSectionLabels로 변환해 담는다.
  location: string
  // AI가 설명 문장을 만들지 못하면 null이다(AI 계약상 정상 케이스).
  description: string | null
  box: AiQualityFindingBox | null
  // 판매자가 "하자 아님"으로 뒤집은 항목. 번호를 유지하려고 응답에는 포함되지만 하자로 세지 않는다.
  isExcluded: boolean
}

// alt는 BE가 주지 않는다 — 표시 문구라 label로 FE가 만든다.
// summary(사진별 요약)도 응답에 있지만 findings 목록과 내용이 겹쳐 화면에 쓰지 않는다.
export interface AiQualityAnalysisImage {
  label: string
  originalImageUrl: string
  originalImageAlt: string
  analyzedImageUrl: string
  analyzedImageAlt: string
  findings: AiQualityFinding[]
}

export interface AiQualityAnalysis {
  status: AiQualityAnalysisStatus
  // 검수 이미지 여러 장(넘겨보기). 이미지별로 원본·검수·설명·findings를 가진다.
  images: AiQualityAnalysisImage[]
  disclaimer: string
}

// CH003: 등록 시 확정 등급으로 조회한 AI 시세 산정 결과(원본 PricingResult에서 BE가 추린
// 값). 산정 전 상품이면 상세 응답 자체에서 null.
export interface ProductPriceEstimateComp {
  title: string
  price: number
  source: string
  url: string
}

export interface ProductPriceEstimate {
  priced: boolean
  priceRange: { min: number; mid: number; max: number } | null
  confidence: number | null
  confidenceLevel: string | null
  rationale: string | null
  compsUsed: ProductPriceEstimateComp[]
  notes: string[]
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
  priceEstimate: ProductPriceEstimate | null
}
