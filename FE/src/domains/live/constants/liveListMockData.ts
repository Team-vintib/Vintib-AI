import denimJacketImage from '@/assets/images/products/product-denim-jacket.webp'
import knitImage from '@/assets/images/products/product-knit.webp'
import leatherBagImage from '@/assets/images/products/product-leather-bag.webp'
import sneakersImage from '@/assets/images/products/product-sneakers.webp'
import trenchCoatImage from '@/assets/images/products/product-trench-coat.webp'
import watchImage from '@/assets/images/products/product-watch.webp'

import type { LiveListItem } from '@/domains/live/types/liveList.types'

// S15P11A108-413 화면 확인용 데이터입니다.
// S15P11A108-418에서 BE 라이브 목록 API 계약을 확인한 뒤 adapter 응답으로 교체합니다.
export const liveListMockData: LiveListItem[] = [
  {
    id: 101,
    title: '90s 데님 재킷 라이브 셀렉션',
    sellerName: 'Archive Room',
    thumbnailUrl: denimJacketImage,
    status: 'LIVE',
    viewerCount: 128,
    category: '아우터',
    broadcastAt: '2026-07-29T11:00:00+09:00',
  },
  {
    id: 102,
    title: '디자이너 백 라이브 셀렉션',
    sellerName: 'Second Vault',
    thumbnailUrl: leatherBagImage,
    status: 'LIVE',
    viewerCount: 86,
    category: '가방',
    broadcastAt: '2026-07-29T10:30:00+09:00',
  },
  {
    id: 103,
    title: '주말 니트웨어 프리뷰',
    sellerName: 'Slow Knit Market',
    thumbnailUrl: knitImage,
    status: 'SCHEDULED',
    viewerCount: 42,
    category: '상의',
    broadcastAt: '2026-07-29T21:00:00+09:00',
  },
  {
    id: 104,
    title: '레어 스니커즈 드롭 라이브',
    sellerName: 'Rare Walk',
    thumbnailUrl: sneakersImage,
    status: 'SCHEDULED',
    viewerCount: 31,
    category: '신발',
    broadcastAt: '2026-07-30T20:30:00+09:00',
  },
  {
    id: 105,
    title: '클래식 트렌치 아카이브',
    sellerName: 'Classic Depot',
    thumbnailUrl: trenchCoatImage,
    status: 'ENDED',
    viewerCount: 342,
    category: '아우터',
    broadcastAt: '2026-07-28T19:00:00+09:00',
  },
  {
    id: 106,
    title: '빈티지 워치 컬렉터 토크',
    sellerName: 'Time Archive',
    thumbnailUrl: watchImage,
    status: 'ENDED',
    viewerCount: 219,
    category: '액세서리',
    broadcastAt: '2026-07-27T20:00:00+09:00',
  },
]
