import denimJacketInspectionImage from '@/assets/images/products/denim-jacket-ai-inspection.png'
import denimJacketImage from '@/assets/images/products/denim-jacket-original.png'
import type { ProductDetailViewData } from '@/domains/product/types/productDetail.types'

// PROD-006 / PROD-010 화면 확인용 임시 데이터입니다.
// GET /api/products/{id}에 이미지·라이브·찜·AI 분석 필드가 추가되면 adapter에서 실제 응답으로 교체합니다.
export const PRODUCT_DETAIL_MOCK_DATA: ProductDetailViewData = {
  id: 1,
  brand: "Levi's",
  title: "Levi's 70505 빈티지 데님 재킷",
  description:
    '자연스럽게 워싱된 1990년대 데님 재킷입니다. 짧은 기장과 여유 있는 어깨선이 특징이며 계절에 관계없이 레이어드하기 좋습니다.',
  category: '아우터 · 데님 재킷',
  conditionLabel: '사용감 있음',
  sizeLabel: 'M',
  material: '면 100%',
  color: '미디엄 인디고',
  price: 45000,
  saleType: 'DIRECT_SALE',
  saleStatus: 'ON_SALE',
  isLiked: false,
  images: [
    {
      id: 'front',
      url: denimJacketImage,
      alt: '빈티지 데님 재킷 앞면 전체',
      label: '앞면',
    },
    {
      id: 'front-detail',
      url: denimJacketImage,
      alt: '빈티지 데님 재킷 앞면 상단',
      label: '상단',
    },
    {
      id: 'hem-detail',
      url: denimJacketImage,
      alt: '빈티지 데님 재킷 밑단',
      label: '밑단',
    },
    {
      id: 'cuff-detail',
      url: denimJacketImage,
      alt: '빈티지 데님 재킷 소매',
      label: '소매',
    },
  ],
  seller: {
    id: 24,
    nickname: 'archive_room',
    followerCount: 1284,
    productCount: 42,
  },
  linkedLive: {
    id: 31,
    title: '이번 주 빈티지 데님 컬렉션',
    startsAt: '2026-07-29T20:00:00+09:00',
    status: 'SCHEDULED',
    thumbnailUrl: denimJacketImage,
  },
  similarProducts: [
    {
      id: 12,
      title: '90s 오버핏 워싱 데님 재킷',
      price: 29000,
    },
    {
      id: 19,
      title: 'Lee 101J 빈티지 데님 재킷',
      price: 34000,
    },
    {
      id: 27,
      title: 'Wrangler 124MJ 데님 재킷',
      price: 39000,
    },
    {
      id: 33,
      title: "Levi's Type III 트러커 재킷",
      price: 43000,
    },
    {
      id: 41,
      title: '스톤 워시 오버핏 데님 재킷',
      price: 52000,
    },
    {
      id: 52,
      title: '셀비지 인디고 데님 재킷',
      price: 58000,
    },
    {
      id: 63,
      title: '70s 레플리카 셀비지 데님 재킷',
      price: 67000,
    },
  ],
  sellerDisclosedDefects: [
    {
      title: '왼쪽 소매 끝단 마모',
      description: '소매 끝단에 자연스러운 사용감과 옅은 마모가 있습니다.',
    },
  ],
  aiQualityAnalysis: {
    status: 'COMPLETED',
    originalImageUrl: denimJacketImage,
    originalImageAlt: 'AI 품질 분석에 사용한 데님 재킷 원본 이미지',
    analyzedImageUrl: denimJacketInspectionImage,
    analyzedImageAlt: '오염 후보와 마모 의심 위치가 표시된 AI 검수 이미지',
    summary:
      '등록 이미지에서 왼쪽 앞면 밑단의 오염 후보와 오른쪽 소매 끝단의 마모 의심 영역을 확인했습니다.',
    findings: [
      {
        id: 'finding-1',
        type: '오염 후보',
        location: '왼쪽 앞면 밑단',
        description: '주변 원단보다 갈색빛이 도는 색상 차이가 확인됩니다.',
      },
      {
        id: 'finding-2',
        type: '마모 의심',
        location: '오른쪽 소매 끝단',
        description: '원단이 짧게 해지고 올이 드러난 영역이 확인됩니다.',
      },
    ],
    disclaimer:
      'AI 분석은 등록 이미지에서 눈에 보이는 후보를 안내하는 참고 정보이며, 숨은 하자나 상품의 전체 품질을 보증하지 않습니다.',
  },
}
