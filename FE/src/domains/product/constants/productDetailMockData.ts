import { buildMockAiQualityAnalysis } from '@/domains/product/constants/aiQualityAnalysisMockData'
import type {
  ProductDetailImage,
  ProductDetailViewData,
} from '@/domains/product/types/productDetail.types'

// Mock 전용 상세 데이터입니다. BE 상세 계약이 확정되면 제거하거나 fixture로 이동합니다.
const image = (id: string) =>
  `https://images.unsplash.com/${id}?auto=format&fit=crop&w=900&q=80`

const detailImages: ProductDetailImage[] = [
  { id: 'detail-1', url: image('photo-1551028719-00167b16eac5'), alt: '레더 라이더 재킷 정면', label: '정면' },
  { id: 'detail-2', url: image('photo-1516762689617-e1cffcef479d'), alt: '레더 라이더 재킷 디테일', label: '디테일' },
  { id: 'detail-3', url: image('photo-1543163521-1bf539c55dd2'), alt: '레더 라이더 재킷 측면', label: '측면' },
  { id: 'detail-4', url: image('photo-1525966222134-fcfa99b8ae77'), alt: '레더 라이더 재킷 후면', label: '후면' },
]

export const buildMockProductDetail = (productId: number): ProductDetailViewData => ({
  id: productId,
  brand: 'Schott',
  title: '80s 카우하이드 레더 라이더 재킷',
  description:
    '미국 오리건 현지에서 직접 셀렉한 빈티지 레더 라이더 재킷입니다. 은은한 사용감이 있으나 원단과 스티치 상태가 양호합니다. 안감 교체 이력은 없습니다.',
  category: '아우터',
  conditionLabel: '사용감 적음',
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
    { id: 501, title: 'Alpha MA-1 플라이트 재킷', price: 132000 },
    { id: 502, title: '80s 무톤 레더 재킷', price: 264000 },
    { id: 503, title: 'Schott 페리코 라이더', price: 342000 },
    { id: 504, title: '빈티지 카페레이서 재킷', price: 198000 },
    { id: 505, title: '더블 라이더 레더 재킷', price: 225000 },
    { id: 506, title: '워크웨어 덕 자켓', price: 96000 },
  ],
  sellerDisclosedDefects: [
    { title: '좌측 소매 스침', description: '좌측 소매 하단에 옅은 스침 자국이 있습니다. 착용 시 눈에 띄지 않는 수준입니다.' },
    { title: '안감 실밥 풀림', description: '안감 하단 실밥 일부가 풀려 있습니다. 착용과 내구성에는 지장이 없습니다.' },
  ],
  aiQualityAnalysis: buildMockAiQualityAnalysis(detailImages),
})
