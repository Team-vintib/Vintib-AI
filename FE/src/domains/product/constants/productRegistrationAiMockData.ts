import { mapAiColorKeyToOptionId } from '@/domains/product/constants/aiColorPalette'

import type { ProductRegistrationAiFinding } from '@/domains/product/types/productRegistration.types'

// ⚠️ Mock 전용 · BE/AI 확인 필요
// 상품 등록 시 front/back 사진만으로 카테고리·색상·품질 검증을 자동 채우는 기능은
// 아직 호출 가능한 BE/AI 엔드포인트가 없다(트리거 지점이 docs/requests/BE/042 미해결).
// findings 필드 형태는 docs/requests/BE/041-quality-inspection-integration.md §2,
// docs/requests/FE/036-quality-finding-bbox-rendering.md가 확정한 실제 계약을 그대로 따른다 —
// 실 연동 시 이 mock을 걷어내고 aiGatewayApi.pollAiJob() 결과로 교체하기만 하면 되도록
// 필드명·형태를 미리 맞춰뒀다.
//   → 요청: docs/requests/BE/042-product-registration-ai-pipeline.md
//   → 요청: docs/requests/AI/006-registration-category-color-autofill.md

export interface MockAiRegistrationAnalysis {
  categoryMajorId: string
  categoryMinorId: string
  colorId: string
  frontFindings: ProductRegistrationAiFinding[]
  backFindings: ProductRegistrationAiFinding[]
}

// id 값은 BE `/categories` 응답(depth2/depth3)에 실제로 존재하는 값과 무관한 예시다 —
// 화면에서는 이 값이 majorCategoryOptions/minorCategoryOptions에 없으면 그냥 select가
// "선택 안 됨" 상태로 보일 뿐이라 mock 단계에서는 문제가 되지 않는다.
export const buildMockAiRegistrationAnalysis = (): MockAiRegistrationAnalysis => ({
  categoryMajorId: '6',
  categoryMinorId: '32',
  // AI가 실제로 주는 형태(팔레트 코드, 예: "BLACK")를 흉내내 매핑 함수를 그대로 거친다.
  colorId: mapAiColorKeyToOptionId('BLACK') ?? 'black',
  frontFindings: [
    {
      key: 'fray_0_1',
      defectType: 'FRAY',
      label: '마모',
      status: 'DETECTED',
      imageIndex: 0,
      no: 1,
      bbox: [0.58, 0.18, 0.82, 0.36],
      confidence: 0.81,
      severity: 'MODERATE',
      statementRequired: true,
      needsSellerReview: false,
      description: '소매 끝단 마모가 의심됩니다.',
      isActualDefect: true,
    },
    {
      key: 'stain_0_2',
      defectType: 'STAIN',
      label: '오염',
      status: 'SUSPECTED',
      imageIndex: 0,
      no: 2,
      bbox: [0.22, 0.56, 0.52, 0.76],
      confidence: 0.62,
      severity: 'MINOR',
      statementRequired: true,
      needsSellerReview: true,
      description: 'Front View 하단에 오염 후보가 있습니다.',
      isActualDefect: true,
    },
  ],
  backFindings: [
    {
      key: 'discoloration_1_1',
      defectType: 'DISCOLORATION',
      label: '변색',
      status: 'DETECTED',
      imageIndex: 1,
      no: 1,
      bbox: [0.38, 0.1, 0.64, 0.23],
      confidence: 0.77,
      severity: 'MINOR',
      statementRequired: true,
      needsSellerReview: false,
      description: '뒷목 칼라 안쪽 변색이 확인됩니다.',
      isActualDefect: true,
    },
  ],
})

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
