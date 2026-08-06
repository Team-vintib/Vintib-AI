import {
  buildMockAiRegistrationAnalysis,
  buildMockPriceEstimates,
} from '@/domains/product/constants/productRegistrationAiMockData'

import type { ProductRegistrationAiFinding } from '@/domains/product/types/productRegistration.types'

// 등록 화면에서 front/back 사진이 갖춰지면 자동으로 도는 AI 분석. tryOnResultApi.ts와 동일하게
// 플래그로 실 API/mock을 가른다 — 기본값은 mock이다(실 엔드포인트가 아직 없음).
const PRODUCT_AI_ENABLED = import.meta.env.VITE_PRODUCT_AI_ENABLED === 'true'

export class ProductAiAnalysisUnavailableError extends Error {
  constructor() {
    super('상품 등록 AI 분석(카테고리·색상·품질 검증) API 연결을 기다리고 있습니다.')
    this.name = 'ProductAiAnalysisUnavailableError'
  }
}

export interface ProductAiAnalysisResult {
  category: { majorId: string; minorId: string } | null
  color: { colorId: string } | null
  quality: {
    front: ProductRegistrationAiFinding[]
    back: ProductRegistrationAiFinding[]
  }
}

export const analyzeRegistrationPhotos = async (
  frontFile: File,
  backFile: File,
): Promise<ProductAiAnalysisResult> => {
  if (!PRODUCT_AI_ENABLED) {
    return buildMockAnalysisResult()
  }

  // docs/requests/BE/042, docs/requests/AI/006이 반영되면 실제 엔드포인트 호출로 교체한다.
  // 지금은 요청 대상 경로 자체가 미정이라 호출을 시도하지 않고 명시적으로 실패시킨다.
  void frontFile
  void backFile
  throw new ProductAiAnalysisUnavailableError()
}

const buildMockAnalysisResult = (): ProductAiAnalysisResult => {
  const mock = buildMockAiRegistrationAnalysis()

  return {
    category: { majorId: mock.categoryMajorId, minorId: mock.categoryMinorId },
    color: { colorId: mock.colorId },
    quality: {
      front: mock.frontFindings,
      back: mock.backFindings,
    },
  }
}

// ── AI 가격 추천 (docs/requests/BE/028-pricing-async.md) ────────────────────────────

export type ProductRegistrationPriceGrade = 'S' | 'A' | 'B' | 'C'

// BE 확인 필요 — 등급별 대표 condition_score. AI가 확인해준 실제 예시는 "82점 → A등급"
// 하나뿐이라 나머지 등급 값은 잠정치다. docs/requests/BE/044-pricing-estimate-trigger.md 회신으로 확정한다.
export const AI_PRICE_GRADE_SCORES: Record<ProductRegistrationPriceGrade, number> = {
  S: 95,
  A: 82,
  B: 68,
  C: 50,
}

export interface ProductAiPriceEstimateInput {
  productName: string
  category?: string
  brand?: string
}

export interface ProductAiPriceEstimate {
  grade: ProductRegistrationPriceGrade
  priced: boolean
  priceRangeMid: number | null
  compPrices: number[]
}

export class ProductAiPriceEstimateUnavailableError extends Error {
  constructor() {
    super('AI 가격 추천 API 연결을 기다리고 있습니다.')
    this.name = 'ProductAiPriceEstimateUnavailableError'
  }
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

    return mock
  }

  // docs/requests/BE/044-pricing-estimate-trigger.md(경량 트리거 엔드포인트)가 반영되면
  // 실제 호출로 교체한다. 지금은 그 엔드포인트 자체가 없어 명시적으로 실패시킨다.
  void input
  throw new ProductAiPriceEstimateUnavailableError()
}
