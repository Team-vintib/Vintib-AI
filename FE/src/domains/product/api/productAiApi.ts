import { buildMockAiRegistrationAnalysis } from '@/domains/product/constants/productRegistrationAiMockData'

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
