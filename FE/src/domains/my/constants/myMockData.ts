import { liveListMockData } from '@/domains/live/constants/liveListMockData'
import { PRODUCT_LIST_MOCK_DATA } from '@/domains/product/constants/productListMockData'
import type {
  MyBusinessVerificationStatus,
  MyLiveItem,
  MyOrderItem,
  MyPageViewData,
  MyProductItem,
  MyProductStatus,
  MyProfile,
  MySaleItem,
  MySectionId,
  MySettlementStatus,
  MyWishItem,
} from '@/domains/my/types/my.types'

export const MY_SECTION_OPTIONS: Array<{ id: MySectionId; label: string }> = [
  { id: 'dashboard', label: '마이페이지' },
  { id: 'seller', label: '판매자 대시보드' },
  { id: 'profile', label: '내 정보 변경' },
  { id: 'products', label: '판매 상품 관리' },
  { id: 'orders', label: '구매·낙찰 내역' },
  { id: 'sales', label: '판매·정산 내역' },
  { id: 'lives', label: '라이브 관리' },
  { id: 'wishlist', label: '찜한 상품' },
  { id: 'social', label: '팔로워·팔로잉' },
  { id: 'points', label: '포인트·출금' },
  { id: 'business', label: '사업자 정보' },
]

export const MY_PRODUCT_STATUS_LABELS: Record<MyProductStatus, string> = {
  ON_SALE: '판매중',
  AUCTION_SCHEDULED: '경매 예정',
  SOLD: '판매 완료',
  PRIVATE: '비공개',
}

export const MY_ORDER_STATUS_LABELS: Record<MyOrderItem['status'], string> = {
  CREATED: '주문 생성',
  PAID: '결제 완료',
  SHIPPING: '배송 중',
  DELIVERED: '배송 완료',
  CONFIRMED: '구매 확정',
  REFUND_REQUESTED: '환불 요청',
  REFUNDED: '환불 완료',
}

export const MY_LIVE_STATUS_LABELS: Record<MyLiveItem['status'], string> = {
  LIVE: '진행 중',
  SCHEDULED: '예약',
  ENDED: '종료',
}

export const MY_SETTLEMENT_STATUS_LABELS: Record<MySettlementStatus, string> = {
  ESCROW: '거래 보관',
  PENDING: '정산 예정',
  SETTLED: '정산 완료',
  REFUND_REQUESTED: '환불 확인',
}

export const MY_BUSINESS_STATUS_LABELS: Record<MyBusinessVerificationStatus, string> = {
  NONE: '미인증',
  PENDING: '검토 중',
  APPROVED: '인증 완료',
  REJECTED: '반려',
}

export const mockMyProfile: MyProfile = {
  id: 1,
  email: 'user@example.com',
  name: '홍길동',
  nickname: 'vintagelover',
  phoneNumber: '01012345678',
  postalCode: '06236',
  address: '서울시 강남구 테헤란로 212',
  detailAddress: '3층',
  gender: 'FEMALE',
  profileImageUrl: null,
  memberType: 'BUSINESS',
  businessVerificationStatus: 'APPROVED',
  onboardingCompleted: true,
}

const mockProducts: MyProductItem[] = PRODUCT_LIST_MOCK_DATA.slice(0, 4).map((product, index) => ({
  id: product.id,
  product,
  status: (['ON_SALE', 'AUCTION_SCHEDULED', 'SOLD', 'PRIVATE'] as const)[index],
  updatedAt: `2026-08-0${index + 1}T10:00:00+09:00`,
}))

const mockOrders: MyOrderItem[] = [
  {
    id: 9001,
    type: 'DIRECT',
    status: 'SHIPPING',
    productName: PRODUCT_LIST_MOCK_DATA[0].name,
    productThumbnailUrl: PRODUCT_LIST_MOCK_DATA[0].imageUrl,
    sellerNickname: 'Archive Room',
    paidAmount: PRODUCT_LIST_MOCK_DATA[0].price,
    createdAt: '2026-08-01T12:30:00+09:00',
  },
  {
    id: 9002,
    type: 'AUCTION',
    status: 'PAID',
    productName: PRODUCT_LIST_MOCK_DATA[2].name,
    productThumbnailUrl: PRODUCT_LIST_MOCK_DATA[2].imageUrl,
    sellerNickname: 'Classic Depot',
    paidAmount: PRODUCT_LIST_MOCK_DATA[2].price,
    createdAt: '2026-07-31T21:10:00+09:00',
  },
]

const mockSales: MySaleItem[] = [
  {
    id: 8101,
    status: 'DELIVERED',
    settlementStatus: 'PENDING',
    productName: PRODUCT_LIST_MOCK_DATA[1].name,
    buyerNickname: 'slowbuyer',
    paidAmount: PRODUCT_LIST_MOCK_DATA[1].price,
    createdAt: '2026-08-01T15:20:00+09:00',
  },
  {
    id: 8102,
    status: 'CONFIRMED',
    settlementStatus: 'SETTLED',
    productName: PRODUCT_LIST_MOCK_DATA[5].name,
    buyerNickname: 'rarecollector',
    paidAmount: PRODUCT_LIST_MOCK_DATA[5].price,
    createdAt: '2026-07-30T19:40:00+09:00',
  },
]

const mockLives: MyLiveItem[] = liveListMockData.slice(0, 3).map((live) => ({
  id: live.id,
  title: live.title,
  status: live.status,
  thumbnailUrl: live.thumbnailUrl,
  productCount: live.status === 'ENDED' ? 6 : 4,
  viewerCount: live.viewerCount,
  broadcastAt: live.broadcastAt,
}))

const mockWishes: MyWishItem[] = PRODUCT_LIST_MOCK_DATA.filter((product) => product.isLiked).map(
  (product, index) => ({
    product,
    wishedAt: `2026-08-0${index + 1}T09:30:00+09:00`,
  }),
)

export const mockMyPageViewData: MyPageViewData = {
  summary: {
    profile: mockMyProfile,
    counts: {
      orders: mockOrders.length,
      sales: mockSales.length,
      wishes: mockWishes.length,
      followers: 12,
      unreadNotifications: 1,
    },
    pointBalance: 128500,
    pendingSettlementAmount: 156000,
    salesPerformance: {
      soldCount: 18,
      grossRevenue: 2460000,
      netRevenue: 2214000,
      averageOrderAmount: 136700,
      sellThroughRate: 64,
      repeatBuyerCount: 5,
    },
    settlementSummary: {
      settledAmount: 1680000,
      pendingAmount: 156000,
      escrowAmount: 420000,
      withdrawableAmount: 128500,
      lastSettledAt: '2026-08-01T09:00:00+09:00',
    },
    todoCounts: {
      shippingPending: 3,
      refundRequests: 1,
      privateProducts: 2,
      scheduledLives: 2,
    },
    productStatusCounts: {
      onSale: 9,
      auctionScheduled: 4,
      sold: 18,
      private: 2,
    },
    monthlyRevenue: [
      { month: '3월', revenue: 420000, soldCount: 4 },
      { month: '4월', revenue: 560000, soldCount: 5 },
      { month: '5월', revenue: 390000, soldCount: 3 },
      { month: '6월', revenue: 720000, soldCount: 6 },
      { month: '7월', revenue: 980000, soldCount: 8 },
      { month: '8월', revenue: 246000, soldCount: 2 },
    ],
  },
  products: mockProducts,
  orders: mockOrders,
  sales: mockSales,
  lives: mockLives,
  wishes: mockWishes,
  wishMeta: {
    page: 1,
    size: 20,
    totalElements: mockWishes.length,
    totalPages: mockWishes.length > 0 ? 1 : 0,
  },
}
