import type {
  AiQualityAnalysis,
  AiQualityFinding,
  ProductDetailImage,
} from '@/domains/product/types/productDetail.types'

// ⚠️ Mock 전용 · BE/AI 확인 필요
// AI 품질 검수(다중 이미지) 계약이 아직 없어 데모용 mock을 사용한다.
// 검수 이미지는 여러 장 들어올 수 있으며, 넘길 때마다 아래 설명·findings도 그 이미지 것으로 바뀐다.
// 실제 데이터가 내려오면 이 파일을 제거하고 API 매핑으로 교체한다.
//   → 요청: docs/requests/BE/019-product-quality-multi-image.md
//
// 원본/검수 이미지 URL은 실제 상품 이미지를 재사용하고, 빨간 네모(box)는
// finding 좌표로 검수 이미지 위에 오버레이한다(실제 AI 주석 이미지 대체).

interface MockAnalysisScenario {
  label: string
  summary: string
  findings: (Omit<AiQualityFinding, 'id'> & { id: string })[]
}

const MOCK_ANALYSIS_SCENARIOS: MockAnalysisScenario[] = [
  {
    label: '앞면',
    summary: '앞면 전체는 상태가 양호합니다. 가슴 부근의 잔보풀과 밑단 오염 후보가 탐지되었습니다.',
    findings: [
      {
        id: 'front-1',
        type: '보풀',
        location: '가슴 중앙',
        description: '섬유 뭉침으로 보이는 잔보풀이 관찰됩니다.',
        box: { x: 42, y: 28, width: 18, height: 15 },
      },
      {
        id: 'front-2',
        type: '오염 후보',
        location: '좌측 밑단',
        description: '옅은 얼룩으로 보이는 색 변화가 있습니다. 실물 확인을 권장합니다.',
        box: { x: 14, y: 66, width: 22, height: 16 },
      },
    ],
  },
  {
    label: '뒷면',
    summary: '뒷면 칼라 안쪽에서 변색 후보가 탐지되었습니다. 그 외 큰 손상은 없습니다.',
    findings: [
      {
        id: 'back-1',
        type: '변색 후보',
        location: '칼라 안쪽',
        description: '착용 흔적으로 보이는 옅은 변색이 있습니다.',
        box: { x: 38, y: 10, width: 26, height: 13 },
      },
    ],
  },
  {
    label: '소매 디테일',
    summary: '소매 끝단에서 마모가 탐지되었습니다. 사용감이 있는 부위입니다.',
    findings: [
      {
        id: 'sleeve-1',
        type: '마모',
        location: '소매 끝단',
        description: '반복 착용으로 인한 마모가 관찰됩니다.',
        box: { x: 58, y: 68, width: 28, height: 21 },
      },
    ],
  },
]

const MOCK_DISCLAIMER =
  'AI 분석 결과는 참고용입니다. 실제 상품 상태는 상세 설명과 판매자 고지를 함께 확인해 주세요.'

const EMPTY_MOCK_ANALYSIS: AiQualityAnalysis = {
  status: 'NOT_REQUESTED',
  images: [],
  disclaimer: '',
}

export const buildMockAiQualityAnalysis = (
  productImages: ProductDetailImage[],
): AiQualityAnalysis => {
  if (!productImages.length) {
    return EMPTY_MOCK_ANALYSIS
  }

  const images = MOCK_ANALYSIS_SCENARIOS.map((scenario, index) => {
    const source = productImages[index % productImages.length]

    return {
      id: `ai-analysis-${index}`,
      label: scenario.label,
      originalImageUrl: source.url,
      originalImageAlt: `${scenario.label} 원본 이미지`,
      analyzedImageUrl: source.url,
      analyzedImageAlt: `${scenario.label} AI 검수 이미지`,
      summary: scenario.summary,
      findings: scenario.findings.map((finding) => ({ ...finding })),
    }
  })

  return {
    status: 'COMPLETED',
    images,
    disclaimer: MOCK_DISCLAIMER,
  }
}
