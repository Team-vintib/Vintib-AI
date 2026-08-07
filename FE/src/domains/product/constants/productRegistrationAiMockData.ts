// ⚠️ Mock 전용 — AI 가격 추천(docs/requests/BE/028-pricing-async.md)만 아직 실 트리거
// 엔드포인트가 없어 이 mock을 쓴다(docs/requests/BE/044-pricing-estimate-trigger.md 회신 대기).
// 카테고리/색상 분류·품질 검증 mock은 실연동 완료로 제거됨(productApi.ts 참고).

export interface MockAiPriceEstimate {
  grade: 'S' | 'A' | 'B' | 'C'
  priced: boolean
  priceRangeMid: number | null
  compPrices: number[]
}

// docs/requests/BE/028-pricing-async.md의 comps_used는 등급(condition)과 무관하게 같은
// 매물 목록을 근거로 삼고, 등급별 계수만 price_range에 반영된다 — mock도 동일하게 comps
// 가격 목록은 4등급이 공유하고 등급별 계수만 다르게 곱한다.
const MOCK_COMP_PRICES = [42_000, 51_000, 55_000, 63_000, 71_000]
const MOCK_COMP_MEDIAN = 55_000
const MOCK_GRADE_COEFFICIENTS: Record<MockAiPriceEstimate['grade'], number> = {
  S: 1.25,
  A: 1.1,
  B: 0.95,
  C: 0.75,
}

export const buildMockPriceEstimates = (): MockAiPriceEstimate[] =>
  (Object.keys(MOCK_GRADE_COEFFICIENTS) as MockAiPriceEstimate['grade'][]).map((grade) => ({
    grade,
    priced: true,
    priceRangeMid: Math.round((MOCK_COMP_MEDIAN * MOCK_GRADE_COEFFICIENTS[grade]) / 1_000) * 1_000,
    compPrices: MOCK_COMP_PRICES,
  }))
