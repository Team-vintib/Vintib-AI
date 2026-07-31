import type {
  LiveWatchMockScenario,
  LiveWatchProduct,
  LiveWatchViewData,
} from '@/domains/live/types/liveWatch.types'

const FIGMA_ASSET_BASE_URL = 'https://images.unsplash.com'

export const LIVE_WATCH_POSTER_URL =
  `${FIGMA_ASSET_BASE_URL}/photo-1441984904996-e0b6ba687e04?w=1000&h=700&fit=crop`

export const LIVE_WATCH_FALLBACK_PRODUCT_IMAGES = [
  `${FIGMA_ASSET_BASE_URL}/photo-1548036328-c9fa89d128fa?w=100&h=100&fit=crop`,
  `${FIGMA_ASSET_BASE_URL}/photo-1539533018447-63fcce2678e3?w=100&h=100&fit=crop`,
  `${FIGMA_ASSET_BASE_URL}/photo-1542272604-787c3835535d?w=100&h=100&fit=crop`,
  `${FIGMA_ASSET_BASE_URL}/photo-1620799140408-edc6dcb6d633?w=100&h=100&fit=crop`,
] as const

const mockProducts: LiveWatchProduct[] = [
  {
    id: 2001,
    title: '1980s 빈티지 레더 메신저백',
    brandName: 'Unlabeled',
    price: 39_000,
    thumbnailUrl: LIVE_WATCH_FALLBACK_PRODUCT_IMAGES[0],
    saleType: 'AUCTION',
    material: '천연 소가죽',
    condition: 'A급',
    measurements: '가로 32cm · 세로 25cm',
    defectSummary: '눈에 띄는 하자 없음',
  },
  {
    id: 2002,
    title: 'Burberry 빈티지 트렌치코트',
    brandName: 'Burberry',
    price: 85_000,
    thumbnailUrl: LIVE_WATCH_FALLBACK_PRODUCT_IMAGES[1],
    saleType: 'FIXED_PRICE',
    material: '코튼 개버딘',
    condition: 'A급',
    measurements: '어깨 46cm · 총장 112cm',
    defectSummary: '소매 끝 미세 사용감',
  },
  {
    id: 2003,
    title: "Levi's 데님 재킷 501",
    brandName: "Levi's",
    price: 28_000,
    thumbnailUrl: LIVE_WATCH_FALLBACK_PRODUCT_IMAGES[2],
    saleType: 'FIXED_PRICE',
    material: '코튼 데님',
    condition: 'B급',
    measurements: '어깨 48cm · 총장 64cm',
    defectSummary: '자연스러운 워싱과 사용감',
  },
  {
    id: 2004,
    title: 'Ralph Lauren 빈티지 스웨터',
    brandName: 'Ralph Lauren',
    price: 45_000,
    thumbnailUrl: LIVE_WATCH_FALLBACK_PRODUCT_IMAGES[3],
    saleType: 'FIXED_PRICE',
    material: '울 혼방',
    condition: 'A급',
    measurements: '어깨 45cm · 총장 67cm',
    defectSummary: '하자 없음',
  },
]

export const liveWatchMockData: LiveWatchViewData = {
  id: 101,
  hostId: 1,
  hostNickname: 'Vintage Hunter',
  hostProfileImageUrl:
    `${FIGMA_ASSET_BASE_URL}/photo-1507003211169-0a1dd7228f2d?w=48&h=48&fit=crop&crop=face`,
  title: '빈티지 레더 경매 라이브',
  description: '시간이 만든 멋을 가진 빈티지 레더 아이템을 소개합니다.',
  posterUrl: LIVE_WATCH_POSTER_URL,
  status: 'LIVE',
  scheduledAt: null,
  startedAt: '2026-07-30T07:44:38+09:00',
  endedAt: null,
  currentViewerCount: 1_248,
  peakViewerCount: 1_436,
  currentProductId: 2001,
  products: mockProducts,
  categories: [
    { id: 10, name: '가방' },
    { id: 11, name: '아우터' },
  ],
}

export const getLiveWatchMockData = (scenario: LiveWatchMockScenario): LiveWatchViewData => {
  if (scenario === 'empty-products') {
    return {
      ...liveWatchMockData,
      currentProductId: null,
      products: [],
    }
  }

  if (scenario === 'scheduled') {
    return {
      ...liveWatchMockData,
      status: 'SCHEDULED',
      scheduledAt: '2026-07-30T20:00:00+09:00',
      startedAt: null,
      currentViewerCount: null,
      currentProductId: null,
    }
  }

  if (scenario === 'ended') {
    return {
      ...liveWatchMockData,
      status: 'ENDED',
      currentViewerCount: null,
      currentProductId: null,
      endedAt: '2026-07-30T09:30:00+09:00',
    }
  }

  return liveWatchMockData
}
