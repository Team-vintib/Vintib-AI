import { buildMockPriceEstimates } from '@/domains/product/constants/productRegistrationAiMockData'
import { pollAiJob } from '@/domains/product/api/aiGatewayApi'
import { http } from '@/shared/api/http'
import type { ApiResponse } from '@/shared/types/api.types'

// 등록 화면에서 front/back 사진이 갖춰지면 자동으로 도는 AI 분석 중, 가격 추천처럼 아직 실
// 엔드포인트가 없는 기능만 이 플래그로 mock을 쓴다(카테고리/색상 분류는 실연동 완료 —
// productApi.ts의 createProductPreUploadUrl 등 참고).
const PRODUCT_AI_ENABLED = import.meta.env.VITE_PRODUCT_AI_ENABLED === 'true'

// ── AI 가격 추천 (docs/requests/BE/028-pricing-async.md, 044, docs/requests/FE/042) ──

export type ProductRegistrationPriceGrade = 'S' | 'A' | 'B' | 'C'

// 등급별 대표 condition_score. AI가 확인해준 실제 예시는 "82점 → A등급" 하나뿐이라
// 나머지 등급 값은 여전히 잠정치다(044 반영 후에도 실측 없이 그대로 채택 — CH001).
export const AI_PRICE_GRADE_SCORES: Record<ProductRegistrationPriceGrade, number> = {
  S: 95,
  A: 82,
  B: 68,
  C: 50,
}

export interface ProductAiPriceEstimateInput {
  productId?: number
  productName: string
  categoryId?: number
  brand?: string
  conditionScore: number
  conditionGrade: ProductRegistrationPriceGrade
}

export interface ProductAiPriceEstimate {
  grade: ProductRegistrationPriceGrade
  priced: boolean
  priceRangeMid: number | null
  compPrices: number[]
  // CH030: `internal_text` 백엔드가 계산한 '동일 상품' 판정 키. 등급과 무관하게 동일 값이라
  // 아무 등급 응답에서나 가져다 쓰면 된다. `internal_text`가 아니면 null.
  matchKey: string | null
  // CH003: PricingResult 원본 그대로 — 확정 등급 것만 골라 PATCH의 priceEstimateSnapshot으로
  // 전달한다(상품 상세가 이 값을 그대로 저장해뒀다가 보여준다, LLM 재호출 없음). mock 모드는
  // 실 PricingResult가 없어 null.
  rawResult: PricingResult | null
}

export class ProductAiPriceEstimateUnavailableError extends Error {
  constructor() {
    super('AI 가격 추천 API 연결을 기다리고 있습니다.')
    this.name = 'ProductAiPriceEstimateUnavailableError'
  }
}

// BE 트리거(044) 응답 — 접수증만 온다.
interface PriceEstimateJobResponse {
  jobId: string
}

// `GET /ai/jobs/{jobId}`의 result. AI 게이트웨이를 BE를 거치지 않고 FE가 직접 폴링하므로
// 이 안쪽 필드는 전부 snake_case다(quality-inspection처럼 BE가 캐멀케이스로 감싸주지 않음).
// CH003: 이 객체를 통째로 PATCH의 priceEstimateSnapshot으로 BE에 전달하므로, 실제 AI
// PricingResult 스키마에 있는 필드는(화면에서 안 쓰더라도) 임의로 빼지 않는다 — BE가
// 상세 응답을 조립할 때(ProductPriceEstimateResponse) 여기 없는 값은 못 쓴다.
interface PricingResult {
  priced: boolean
  price_range: { min: number; mid: number; max: number } | null
  confidence: number | null
  confidence_level: string | null
  rationale: string | null
  comps_used: { title: string; price: number; source: string; url: string }[]
  notes: string[]
  product_match_key: string | null
}

// 등급 4개를 각각 조회해야 하는데(028, 등급 1건당 job 1개), AI 쪽 동시 처리 상한이 2건이라
// 호출부(ProductRegistrationPage.vue)에서 2개씩 나눠 부른다 — 이 함수는 등급 1건만 담당한다.
export const estimateRegistrationPrice = async (
  grade: ProductRegistrationPriceGrade,
  input: ProductAiPriceEstimateInput,
): Promise<ProductAiPriceEstimate> => {
  if (!PRODUCT_AI_ENABLED) {
    const mock = buildMockPriceEstimates().find((estimate) => estimate.grade === grade)

    if (!mock) {
      throw new ProductAiPriceEstimateUnavailableError()
    }

    return { ...mock, matchKey: null, rawResult: null }
  }

  const jobResponse = await http.post<ApiResponse<PriceEstimateJobResponse>>(
    '/products/price-estimates',
    {
      productId: input.productId,
      productName: input.productName,
      categoryId: input.categoryId,
      brand: input.brand,
      conditionScore: input.conditionScore,
      conditionGrade: input.conditionGrade,
    },
  )

  if (!jobResponse.data.success || !jobResponse.data.data) {
    throw new ProductAiPriceEstimateUnavailableError()
  }

  const result = await pollAiJob<PricingResult>(jobResponse.data.data.jobId)

  return {
    grade,
    priced: result.priced,
    priceRangeMid: result.price_range?.mid ?? null,
    compPrices: result.comps_used.map((comp) => comp.price),
    matchKey: result.product_match_key,
    rawResult: result,
  }
}
