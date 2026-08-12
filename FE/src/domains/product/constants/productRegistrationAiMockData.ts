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
//
// 지점(만원 단위)마다 comp 개수를 정의 — 실측이 아니라 그래프가 실데이터처럼 보이도록
// 만든 분포다(총합 182개). 5~9만원대 구간(그래프 상 "5-6"·"6-7"·"7-8"·"8-9"·"9-10만원대"
// 막대)이 서로 비슷해 보이지 않도록 35/22/32/28/17건으로 들쭉날쭉하게 잡았다. 등급 경계
// (4·7·9만원)에 걸치는 지점은 두 등급 색이 섞여 보이도록 값을 경계 양쪽으로 나눠 넣는다
// (예: 7만원대는 66,000/74,000으로 나눠 앞쪽은 B, 뒤쪽은 A에 더 가깝게 잡는다) —
// MOCK_GRADE_COEFFICIENTS 기준 등급별 대표가는 C 3.5만/B 5.5만/A 8만/S 9.5만원이라 그
// 중간값이 실제 등급 경계가 된다.
const MOCK_COMP_PRICE_POINTS: { price: number; count: number }[] = [
  { price: 30_000, count: 10 },
  { price: 40_000, count: 13 },
  { price: 50_000, count: 35 },
  { price: 60_000, count: 22 },
  { price: 66_000, count: 18 },
  { price: 74_000, count: 14 },
  { price: 80_000, count: 28 },
  { price: 86_000, count: 14 },
  { price: 94_000, count: 3 },
  { price: 100_000, count: 12 },
  { price: 110_000, count: 13 },
]
const MOCK_COMP_PRICES = MOCK_COMP_PRICE_POINTS.flatMap(({ price, count }) =>
  Array<number>(count).fill(price),
)
const MOCK_COMP_MEDIAN = 50_000
const MOCK_GRADE_COEFFICIENTS: Record<MockAiPriceEstimate['grade'], number> = {
  S: 1.9,
  A: 1.6,
  B: 1.1,
  C: 0.7,
}

export const buildMockPriceEstimates = (): MockAiPriceEstimate[] =>
  (Object.keys(MOCK_GRADE_COEFFICIENTS) as MockAiPriceEstimate['grade'][]).map((grade) => ({
    grade,
    priced: true,
    priceRangeMid: Math.round((MOCK_COMP_MEDIAN * MOCK_GRADE_COEFFICIENTS[grade]) / 1_000) * 1_000,
    compPrices: MOCK_COMP_PRICES,
  }))
