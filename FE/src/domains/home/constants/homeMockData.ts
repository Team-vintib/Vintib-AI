import { ROUTE_PATHS } from '@/shared/constants/routes'

import type { HomeMockData } from '../types/home.types'

export const homeMockData: HomeMockData = {
  liveNow: [
    {
      id: 101,
      status: 'live',
      title: '90s 데님 재킷 라이브 셀렉션',
      sellerName: 'Archive Room',
      category: '아우터',
      thumbnailUrl:
        'https://images.unsplash.com/photo-1516762689617-e1cffcef479d?auto=format&fit=crop&w=900&q=80',
      representativeProductName: "Levi's faded trucker jacket",
      viewerCount: 128,
      startedAt: '2026-07-27T20:00:00+09:00',
    },
    {
      id: 102,
      status: 'live',
      title: '디자이너 백 빈티지 경매',
      sellerName: 'Second Vault',
      category: '가방',
      thumbnailUrl:
        'https://images.unsplash.com/photo-1590874103328-eac38a683ce7?auto=format&fit=crop&w=900&q=80',
      representativeProductName: 'vintage leather shoulder bag',
      viewerCount: 86,
      startedAt: '2026-07-27T19:30:00+09:00',
    },
  ],
  scheduledLives: [
    {
      id: 201,
      status: 'scheduled',
      title: '주말 니트웨어 프리뷰',
      sellerName: 'Slow Knit Market',
      category: '상의',
      thumbnailUrl:
        'https://images.unsplash.com/photo-1489987707025-afc232f7ea0f?auto=format&fit=crop&w=900&q=80',
      representativeProductName: 'wool cable knit cardigan',
      reservationCount: 42,
      scheduledAt: '2026-07-28T21:00:00+09:00',
    },
    {
      id: 202,
      status: 'scheduled',
      title: '실버 주얼리 소장품 오픈',
      sellerName: '925 Collective',
      category: '액세서리',
      thumbnailUrl:
        'https://images.unsplash.com/photo-1515562141207-7a88fb7ce338?auto=format&fit=crop&w=900&q=80',
      representativeProductName: 'sterling silver ring set',
      reservationCount: 31,
      scheduledAt: '2026-07-29T20:30:00+09:00',
    },
  ],
  fixedPriceProducts: [
    {
      id: 301,
      saleType: 'fixed',
      status: 'on_sale',
      name: 'Burberry check wool muffler',
      sellerName: 'Classic Depot',
      brandName: 'Burberry',
      category: '액세서리',
      imageUrl:
        'https://images.unsplash.com/photo-1520903920243-00d872a2d1c9?auto=format&fit=crop&w=900&q=80',
      price: 118000,
      isWished: false,
    },
    {
      id: 302,
      saleType: 'fixed',
      status: 'on_sale',
      name: 'Ralph Lauren linen shirt',
      sellerName: 'Weekend Closet',
      brandName: 'Ralph Lauren',
      category: '상의',
      imageUrl:
        'https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?auto=format&fit=crop&w=900&q=80',
      price: 69000,
      isWished: true,
    },
    {
      id: 303,
      saleType: 'fixed',
      status: 'on_sale',
      name: 'Maison leather belt',
      sellerName: 'Old Edition',
      brandName: 'Maison Margiela',
      category: '액세서리',
      imageUrl:
        'https://images.unsplash.com/photo-1624222247344-550fb60583dc?auto=format&fit=crop&w=900&q=80',
      price: 94000,
      isWished: false,
    },
  ],
  upcomingAuctions: [
    {
      id: 401,
      saleType: 'auction',
      status: 'auction_scheduled',
      name: 'Gucci horsebit loafer',
      sellerName: 'Rare Walk',
      brandName: 'Gucci',
      category: '신발',
      imageUrl:
        'https://images.unsplash.com/photo-1549298916-b41d501d3772?auto=format&fit=crop&w=900&q=80',
      startingBid: 150000,
      auctionStartsAt: '2026-07-30T21:00:00+09:00',
      isWished: true,
    },
    {
      id: 402,
      saleType: 'auction',
      status: 'auction_scheduled',
      name: 'Omega vintage watch',
      sellerName: 'Time Archive',
      brandName: 'Omega',
      category: '시계',
      imageUrl:
        'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=900&q=80',
      startingBid: 420000,
      auctionStartsAt: '2026-07-31T20:00:00+09:00',
      isWished: false,
    },
  ],
  contents: [
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
  recommendedSellers: [
    {
      id: 601,
      name: 'Archive Room',
      profileImageUrl:
        'https://images.unsplash.com/photo-1508214751196-bcfd4ca60f91?auto=format&fit=crop&w=400&q=80',
      description: '90s 캐주얼과 데님 중심의 빈티지 셀러',
      followerCount: 1240,
    },
    {
      id: 602,
      name: 'Second Vault',
      profileImageUrl:
        'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=400&q=80',
      description: '가방, 지갑, 소품 위주의 프리미엄 셀렉션',
      followerCount: 936,
    },
  ],
  followingLives: [
    {
      id: 101,
      status: 'live',
      title: '90s 데님 재킷 라이브 셀렉션',
      sellerName: 'Archive Room',
      category: '아우터',
      thumbnailUrl:
        'https://images.unsplash.com/photo-1516762689617-e1cffcef479d?auto=format&fit=crop&w=900&q=80',
      representativeProductName: "Levi's faded trucker jacket",
      viewerCount: 128,
      startedAt: '2026-07-27T20:00:00+09:00',
    },
  ],
  followingProducts: [
    {
      id: 302,
      saleType: 'fixed',
      status: 'on_sale',
      name: 'Ralph Lauren linen shirt',
      sellerName: 'Weekend Closet',
      brandName: 'Ralph Lauren',
      category: '상의',
      imageUrl:
        'https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?auto=format&fit=crop&w=900&q=80',
      price: 69000,
      isWished: true,
    },
  ],
}
