import { ROUTE_PATHS } from '@/shared/constants/routes'

import type { HomeViewMockData } from '../types/homeView.types'

// Mock 전용 데이터입니다. API 응답 계약이 확정되면 제거하거나 API adapter 테스트 fixture로 이동합니다.
export const homeMockData: HomeViewMockData = {
  liveNow: [
    {
      id: 101,
      status: 'LIVE',
      title: '90s 데님 재킷 라이브 셀렉션',
      hostName: 'Archive Room',
      categoryName: '아우터',
      thumbnailUrl:
        'https://images.unsplash.com/photo-1516762689617-e1cffcef479d?auto=format&fit=crop&w=900&q=80',
      viewerCount: 128,
      startedAt: '2026-07-27T20:00:00+09:00',
    },
    {
      id: 102,
      status: 'LIVE',
      title: '디자이너 백 빈티지 경매',
      hostName: 'Second Vault',
      categoryName: '가방',
      thumbnailUrl:
        'https://images.unsplash.com/photo-1590874103328-eac38a683ce7?auto=format&fit=crop&w=900&q=80',
      viewerCount: 86,
      startedAt: '2026-07-27T19:30:00+09:00',
    },
    {
      id: 103,
      status: 'LIVE',
      title: '레더 아우터 컬렉션 경매',
      hostName: 'Heritage Depot',
      categoryName: '아우터',
      thumbnailUrl:
        'https://images.unsplash.com/photo-1551028719-00167b16eac5?auto=format&fit=crop&w=900&q=80',
      viewerCount: 64,
      startedAt: '2026-07-27T20:10:00+09:00',
    },
  ],
  scheduledLives: [
    {
      id: 201,
      status: 'SCHEDULED',
      title: '주말 니트웨어 프리뷰',
      hostName: 'Slow Knit Market',
      categoryName: '상의',
      thumbnailUrl:
        'https://images.unsplash.com/photo-1489987707025-afc232f7ea0f?auto=format&fit=crop&w=900&q=80',
      reservationCount: 42,
      scheduledProductCount: 8,
      scheduledAt: '2026-07-28T21:00:00+09:00',
    },
    {
      id: 202,
      status: 'SCHEDULED',
      title: '실버 주얼리 소장품 오픈',
      hostName: '925 Collective',
      categoryName: '액세서리',
      thumbnailUrl:
        'https://images.unsplash.com/photo-1515562141207-7a88fb7ce338?auto=format&fit=crop&w=900&q=80',
      reservationCount: 31,
      scheduledProductCount: 6,
      scheduledAt: '2026-07-29T20:30:00+09:00',
    },
    {
      id: 203,
      status: 'SCHEDULED',
      title: '데님 팬츠 아카이브 프리뷰',
      hostName: 'Blue Label',
      categoryName: '하의',
      thumbnailUrl:
        'https://images.unsplash.com/photo-1542272604-787c3835535d?auto=format&fit=crop&w=900&q=80',
      reservationCount: 27,
      scheduledProductCount: 10,
      scheduledAt: '2026-07-30T19:00:00+09:00',
    },
  ],
  directSaleProducts: [
    {
      id: 301,
      saleType: 'DIRECT_SALE',
      saleStatus: 'ON_SALE',
      title: 'Burberry check wool muffler',
      sellerName: 'Classic Depot',
      brandName: 'Burberry',
      categoryName: '액세서리',
      primaryImageUrl:
        'https://images.unsplash.com/photo-1520903920243-00d872a2d1c9?auto=format&fit=crop&w=900&q=80',
      price: 118000,
      isWished: false,
    },
    {
      id: 302,
      saleType: 'DIRECT_SALE',
      saleStatus: 'ON_SALE',
      title: 'Ralph Lauren linen shirt',
      sellerName: 'Weekend Closet',
      brandName: 'Ralph Lauren',
      categoryName: '상의',
      primaryImageUrl:
        'https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?auto=format&fit=crop&w=900&q=80',
      price: 69000,
      isWished: true,
    },
    {
      id: 303,
      saleType: 'DIRECT_SALE',
      saleStatus: 'ON_SALE',
      title: 'Maison leather belt',
      sellerName: 'Old Edition',
      brandName: 'Maison Margiela',
      categoryName: '액세서리',
      primaryImageUrl:
        'https://images.unsplash.com/photo-1624222247344-550fb60583dc?auto=format&fit=crop&w=900&q=80',
      price: 94000,
      isWished: false,
    },
  ],
  upcomingAuctionProducts: [
    {
      id: 401,
      saleType: 'AUCTION',
      saleStatus: 'AUCTION_SCHEDULED',
      title: 'Gucci horsebit loafer',
      sellerName: 'Rare Walk',
      brandName: 'Gucci',
      categoryName: '신발',
      primaryImageUrl:
        'https://images.unsplash.com/photo-1549298916-b41d501d3772?auto=format&fit=crop&w=900&q=80',
      price: 240000,
      startingBid: 150000,
      auctionStartsAt: '2026-07-30T21:00:00+09:00',
      isWished: true,
    },
    {
      id: 402,
      saleType: 'AUCTION',
      saleStatus: 'AUCTION_SCHEDULED',
      title: 'Omega vintage watch',
      sellerName: 'Time Archive',
      brandName: 'Omega',
      categoryName: '시계',
      primaryImageUrl:
        'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=900&q=80',
      price: 680000,
      startingBid: 420000,
      auctionStartsAt: '2026-07-31T20:00:00+09:00',
      isWished: false,
    },
  ],
  followedSellers: [
    {
      id: 601,
      liveId: 101,
      name: 'Archive Room',
      profileImageUrl:
        'https://images.unsplash.com/photo-1529139574466-a303027c1d8b?auto=format&fit=crop&w=400&q=80',
      coverImageUrl:
        'https://images.unsplash.com/photo-1516762689617-e1cffcef479d?auto=format&fit=crop&w=900&q=80',
      specialty: '90s denim and outer',
      followerCount: 1240,
      newProductCount: 12,
      liveStatus: 'LIVE',
      liveTitle: '90s 데님 재킷 라이브 셀렉션',
      liveAt: '2026-07-27T20:00:00+09:00',
    },
    {
      id: 602,
      liveId: 202,
      name: '925 Collective',
      profileImageUrl:
        'https://images.unsplash.com/photo-1499952127939-9bbf5af6c51c?auto=format&fit=crop&w=400&q=80',
      coverImageUrl:
        'https://images.unsplash.com/photo-1515562141207-7a88fb7ce338?auto=format&fit=crop&w=900&q=80',
      specialty: 'silver jewelry',
      followerCount: 860,
      newProductCount: 6,
      liveStatus: 'SCHEDULED',
      liveTitle: '실버 주얼리 소장품 오픈',
      liveAt: '2026-07-29T20:30:00+09:00',
    },
    {
      id: 603,
      liveId: 201,
      name: 'Slow Knit Market',
      profileImageUrl:
        'https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?auto=format&fit=crop&w=400&q=80',
      coverImageUrl:
        'https://images.unsplash.com/photo-1489987707025-afc232f7ea0f?auto=format&fit=crop&w=900&q=80',
      specialty: 'knit and calm casual',
      followerCount: 540,
      newProductCount: 8,
      liveStatus: 'SCHEDULED',
      liveTitle: '주말 니트웨어 프리뷰',
      liveAt: '2026-07-28T21:00:00+09:00',
    },
  ],
  recommendedProducts: [
    {
      id: 701,
      saleType: 'DIRECT_SALE',
      saleStatus: 'ON_SALE',
      title: 'Levi’s 501 washed denim',
      sellerName: 'Blue Label',
      brandName: 'Levi’s',
      categoryName: '하의',
      primaryImageUrl:
        'https://images.unsplash.com/photo-1541099649105-f69ad21f3246?auto=format&fit=crop&w=900&q=80',
      price: 86000,
      isWished: true,
      recommendationReason: '최근 데님 상품을 자주 봤어요',
    },
    {
      id: 702,
      saleType: 'AUCTION',
      saleStatus: 'AUCTION_SCHEDULED',
      title: 'Prada nylon shoulder bag',
      sellerName: 'Second Vault',
      brandName: 'Prada',
      categoryName: '가방',
      primaryImageUrl:
        'https://images.unsplash.com/photo-1590874103328-eac38a683ce7?auto=format&fit=crop&w=900&q=80',
      price: 390000,
      startingBid: 250000,
      auctionStartsAt: '2026-07-30T20:00:00+09:00',
      isWished: false,
      recommendationReason: '팔로우 셀러의 경매 예정 상품',
    },
    {
      id: 703,
      saleType: 'DIRECT_SALE',
      saleStatus: 'ON_SALE',
      title: 'Vintage leather bomber',
      sellerName: 'Heritage Depot',
      brandName: 'Schott',
      categoryName: '아우터',
      primaryImageUrl:
        'https://images.unsplash.com/photo-1551028719-00167b16eac5?auto=format&fit=crop&w=900&q=80',
      price: 210000,
      isWished: false,
      recommendationReason: '아우터 관심 카테고리와 맞아요',
    },
  ],
  contentCards: [
    {
      id: 501,
      title: '라이브로 만나는 빈티지 셀렉션',
      description: '실시간으로 상태를 확인하고 판매자와 대화하며 구매해 보세요.',
      imageUrl:
        'https://images.unsplash.com/photo-1496747611176-843222e1e57c?auto=format&fit=crop&w=1200&q=80',
      ctaLabel: '라이브 둘러보기',
      targetPath: ROUTE_PATHS.LIVE_LIST,
      audience: 'guest',
    },
    {
      id: 502,
      title: '팔로우한 셀러의 새 라이브',
      description: '관심 있는 셀러의 라이브와 상품을 홈에서 바로 확인하세요.',
      imageUrl:
        'https://images.unsplash.com/photo-1483985988355-763728e1935b?auto=format&fit=crop&w=1200&q=80',
      ctaLabel: '팔로잉 보기',
      targetPath: ROUTE_PATHS.FOLLOWING_HOME,
      audience: 'member',
    },
  ],
}
