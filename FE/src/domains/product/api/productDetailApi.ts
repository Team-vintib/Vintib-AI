import { PRODUCT_DETAIL_MOCK_DATA } from '@/domains/product/constants/productDetailMockData'
import type {
  AiQualityAnalysisStatus,
  ProductDetailMockScenario,
  ProductDetailViewData,
} from '@/domains/product/types/productDetail.types'

export class ProductDetailNotFoundError extends Error {
  constructor() {
    super('상품을 찾을 수 없습니다.')
    this.name = 'ProductDetailNotFoundError'
  }
}

const waitForMockResponse = () =>
  new Promise<void>((resolve) => {
    window.setTimeout(resolve, 280)
  })

const cloneProductDetailMockData = (): ProductDetailViewData => ({
  ...PRODUCT_DETAIL_MOCK_DATA,
  images: PRODUCT_DETAIL_MOCK_DATA.images.map((image) => ({ ...image })),
  seller: { ...PRODUCT_DETAIL_MOCK_DATA.seller },
  linkedLive: PRODUCT_DETAIL_MOCK_DATA.linkedLive
    ? { ...PRODUCT_DETAIL_MOCK_DATA.linkedLive }
    : null,
  sellerDisclosedDefects: PRODUCT_DETAIL_MOCK_DATA.sellerDisclosedDefects.map((defect) => ({
    ...defect,
  })),
  aiQualityAnalysis: {
    ...PRODUCT_DETAIL_MOCK_DATA.aiQualityAnalysis,
    findings: PRODUCT_DETAIL_MOCK_DATA.aiQualityAnalysis.findings.map((finding) => ({
      ...finding,
    })),
  },
})

const AI_SCENARIO_STATUS: Partial<Record<ProductDetailMockScenario, AiQualityAnalysisStatus>> = {
  'ai-not-requested': 'NOT_REQUESTED',
  'ai-analyzing': 'ANALYZING',
  'ai-no-findings': 'NO_FINDINGS',
  'ai-failed': 'FAILED',
}

export const getProductDetailViewData = async (
  productId: number,
  scenario: ProductDetailMockScenario = 'default',
): Promise<ProductDetailViewData> => {
  // 최신 Swagger의 GET /api/products/{id}는 기본 정보만 반환합니다.
  // 이미지·연결 라이브·찜·AI 품질 분석 계약이 합쳐지면 이 함수 안에서 응답을 ViewData로 매핑합니다.
  await waitForMockResponse()

  if (scenario === 'error') {
    throw new Error('상품 상세 mock 조회 실패')
  }

  if (scenario === 'not-found' || productId === 404) {
    throw new ProductDetailNotFoundError()
  }

  const product = cloneProductDetailMockData()
  product.id = productId

  if (scenario === 'sold') {
    product.saleStatus = 'SOLD'
  }

  const aiStatus = AI_SCENARIO_STATUS[scenario]

  if (aiStatus) {
    product.aiQualityAnalysis.status = aiStatus
  }

  if (aiStatus === 'NO_FINDINGS') {
    product.aiQualityAnalysis.summary =
      '등록 이미지에서 눈에 띄는 하자 후보를 찾지 못했습니다.'
    product.aiQualityAnalysis.findings = []
  }

  return product
}
