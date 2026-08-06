import type { ProductRegistrationAiFinding } from '@/domains/product/types/productRegistration.types'

// ⚠️ Mock 전용 · BE/AI 확인 필요
// 상품 등록 시 front/back 사진만으로 카테고리·색상·품질 검증을 자동 채우는 기능은
// 아직 호출 가능한 BE/AI 엔드포인트가 없다. 실제 계약이 정해지면 이 파일을 제거하고
// productAiApi.ts의 mock 분기를 실 API 매핑으로 교체한다.
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
  colorId: 'black',
  frontFindings: [
    {
      id: crypto.randomUUID(),
      labelNumber: 1,
      description: '소매 끝단 마모 의심',
      box: { x: 58, y: 18, width: 24, height: 18 },
      isActualDefect: true,
    },
    {
      id: crypto.randomUUID(),
      labelNumber: 2,
      description: 'Front View 하단 오염 후보',
      box: { x: 22, y: 56, width: 30, height: 20 },
      isActualDefect: true,
    },
  ],
  backFindings: [
    {
      id: crypto.randomUUID(),
      labelNumber: 1,
      description: '뒷목 칼라 안쪽 변색 후보',
      box: { x: 38, y: 10, width: 26, height: 13 },
      isActualDefect: true,
    },
  ],
})
