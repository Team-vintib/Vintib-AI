import { buildMockAiQualityAnalysis } from '@/domains/product/constants/aiQualityAnalysisMockData'
import type {
  ProductDetailImage,
  ProductDetailViewData,
} from '@/domains/product/types/productDetail.types'

// Mock 전용 상세 데이터입니다. BE 상세 계약이 확정되면 제거하거나 fixture로 이동합니다.
const image = (id: string) => `https://images.unsplash.com/${id}?auto=format&fit=crop&w=900&q=80`

const detailImages: ProductDetailImage[] = [
  {
    id: 'detail-1',
    url: image('photo-1551028719-00167b16eac5'),
    alt: '레더 라이더 재킷 정면',
    label: '정면',
  },
  {
    id: 'detail-2',
    url: image('photo-1516762689617-e1cffcef479d'),
    alt: '레더 라이더 재킷 디테일',
    label: '디테일',
  },
  {
    id: 'detail-3',
    url: image('photo-1543163521-1bf539c55dd2'),
    alt: '레더 라이더 재킷 측면',
    label: '측면',
  },
  {
    id: 'detail-4',
    url: image('photo-1525966222134-fcfa99b8ae77'),
    alt: '레더 라이더 재킷 후면',
    label: '후면',
  },
]

export const buildMockProductDetail = (productId: number): ProductDetailViewData => ({
  id: productId,
  brand: 'Schott',
  title: '80s 카우하이드 레더 라이더 재킷',
  description:
    '미국 오리건 현지에서 직접 셀렉한 빈티지 레더 라이더 재킷입니다. 은은한 사용감이 있으나 원단과 스티치 상태가 양호합니다. 안감 교체 이력은 없습니다.',
  category: '아우터',
  categoryId: 1,
  conditionLabel: 'S급',
  sizeLabel: 'M (100)',
  material: '카우하이드 레더',
  color: '블랙',
  price: 218000,
  saleType: 'DIRECT_SALE',
  saleStatus: 'ON_SALE',
  isLiked: false,
  images: detailImages,
  seller: { id: 42, nickname: 'leather.dept', followerCount: 1245, productCount: 86 },
  linkedLive: {
    id: 101,
    title: '레더 아우터 컬렉션 경매',
    startsAt: '2026-07-29T11:00:00+09:00',
    status: 'LIVE',
    thumbnailUrl: image('photo-1551028719-00167b16eac5'),
  },
  measurements: { 어깨: 46, 가슴: 54, 소매: 63, 총장: 66 },
  similarProducts: [
    // 0–2만원대
    { id: 501, title: '베이직 크루넥 반팔 티셔츠', price: 12000 },
    { id: 502, title: '오버사이즈 화이트 무지 티', price: 15000 },
    { id: 503, title: '빈티지 워싱 그래픽 티셔츠', price: 18000 },
    // 4–6만원대
    { id: 504, title: '90s USA 밴드 티셔츠', price: 45000 },
    { id: 505, title: '레트로 프린팅 반팔 티', price: 52000 },
    { id: 506, title: '헤비웨이트 옥스포드 티셔츠', price: 58000 },
    // 6–8만원대
    { id: 507, title: 'Champion 리버스 위브 티셔츠', price: 65000 },
    { id: 508, title: '빈티지 스트라이프 헨리넥 티', price: 72000 },
    { id: 509, title: '코듀로이 카라 반팔 티셔츠', price: 78000 },
    // 10–12만원대
    { id: 510, title: 'Supreme 박스로고 티셔츠', price: 105000 },
    { id: 511, title: 'Stussy 빈티지 아카이브 티', price: 112000 },
    { id: 512, title: '90s Polo Ralph Lauren 티셔츠', price: 118000 },
  ],
  sellerDisclosedDefects: [
    {
      title: '좌측 소매 스침',
      description: '좌측 소매 하단에 옅은 스침 자국이 있습니다. 착용 시 눈에 띄지 않는 수준입니다.',
    },
    {
      title: '안감 실밥 풀림',
      description: '안감 하단 실밥 일부가 풀려 있습니다. 착용과 내구성에는 지장이 없습니다.',
    },
  ],
  aiQualityAnalysis: buildMockAiQualityAnalysis(detailImages),
  aiModelCut: null,
  priceEstimate: {
    priced: true,
    priceRange: { min: 78000, mid: 89000, max: 102000 },
    confidence: 0.72,
    confidenceLevel: 'MEDIUM',
    rationale: '동일 브랜드·유사 상태의 중고 거래가를 기준으로 산정했습니다.',
    compsUsed: [
      { title: 'Maison Kitsuné 폭스 헤드 티셔츠 블랙 M', price: 85000, source: 'llm_web_search', url: '' },
      { title: 'Maison Kitsuné 티셔츠 새 상품급', price: 98000, source: 'llm_web_search', url: '' },
    ],
    notes: [],
  },
})
