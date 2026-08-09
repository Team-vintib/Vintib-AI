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
  findings: AiQualityFinding[]
}

const MOCK_ANALYSIS_SCENARIOS: MockAnalysisScenario[] = [
  {
    label: '앞면',
    findings: [
      {
        key: 'pilling_0_5_1',
        no: 1,
        type: '보풀',
        location: '가슴 중앙',
        description: '섬유 뭉침으로 보이는 잔보풀이 관찰됩니다.',
        box: { x: 42, y: 28, width: 18, height: 15 },
        isExcluded: false,
      },
      {
        // AI가 설명을 못 주는 경우(신뢰도 낮은 '의심' 항목)를 재현한다 — 설명 줄이 안 그려진다.
        key: 'stain_0_7_1',
        no: 2,
        type: '오염 후보',
        location: '왼쪽 밑단',
        description: null,
        box: { x: 14, y: 66, width: 22, height: 16 },
        isExcluded: false,
      },
    ],
  },
  {
    label: '뒷면',
    findings: [
      {
        // 판매자가 "하자 아님"으로 확인한 항목 — 회색·취소선으로 죽여서 표시된다.
        key: 'discoloration_1_2_1',
        no: 1,
        type: '변색 후보',
        location: '목깃',
        description: '착용 흔적으로 보이는 옅은 변색이 있습니다.',
        box: { x: 38, y: 10, width: 26, height: 13 },
        isExcluded: true,
      },
    ],
  },
  {
    label: '소매 디테일',
    findings: [
      {
        key: 'fray_2_6_1',
        no: 1,
        type: '마모',
        location: '오른쪽 소매',
        description: '반복 착용으로 인한 마모가 관찰됩니다.',
        box: { x: 58, y: 68, width: 28, height: 21 },
        isExcluded: false,
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
      label: scenario.label,
      originalImageUrl: source.url,
      originalImageAlt: `${scenario.label} 원본 이미지`,
      analyzedImageUrl: source.url,
      analyzedImageAlt: `${scenario.label} AI 검수 이미지`,
      findings: scenario.findings.map((finding) => ({ ...finding })),
    }
  })

  return {
    status: 'COMPLETED',
    images,
    disclaimer: MOCK_DISCLAIMER,
  }
}
