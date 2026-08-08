/**
 * 라이브 화면이 구독하는 STOMP 토픽 경로.
 *
 * ⚠️ `currentProduct`(`/product`)와 `productSold`(`/product-sold`)는 한 글자 차이지만 전혀 다른
 * 알림이다 — 앞은 "지금 소개 중인 상품"(NOW 배지), 뒤는 "정찰제로 팔렸다". 문자열을 화면마다
 * 직접 적으면 섞이기 쉬워서 여기로 모았다(BE 계약 안내에서도 같은 주의를 준다).
 */
export const LIVE_TOPICS = {
  status: (liveId: number) => `/topic/lives/${liveId}/status`,
  currentProduct: (liveId: number) => `/topic/lives/${liveId}/product`,
  productSold: (liveId: number) => `/topic/lives/${liveId}/product-sold`,
  auctions: (liveId: number) => `/topic/lives/${liveId}/auctions`,
} as const
