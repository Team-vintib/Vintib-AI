import type { ProductListItem } from '@/domains/product/types/productList.types'
import type { PageMeta } from '@/shared/types/api.types'

export type MySectionId =
  | 'dashboard'
  | 'seller'
  | 'profile'
  | 'tryon'
  | 'products'
  | 'orders'
  | 'sales'
  | 'lives'
  | 'social'
  | 'points'
  | 'business'

export type MyMemberType = 'GENERAL' | 'BUSINESS'
export type MyBusinessVerificationStatus = 'NONE' | 'PENDING' | 'APPROVED' | 'REJECTED'
export type MyOrderStatus =
  | 'PAID'
  | 'SHIPPING'
  | 'DELIVERED'
  | 'CONFIRMED'
  | 'SETTLED'
  | 'REFUNDED'
  | 'CANCELED'
export type MyProductStatus = 'ON_SALE' | 'AUCTION_SCHEDULED' | 'SOLD'
export type MyLiveStatus = 'LIVE' | 'SCHEDULED' | 'ENDED'
export type MySettlementStatus = 'ESCROW' | 'PENDING' | 'SETTLED' | 'REFUND_REQUESTED'

export interface MyProfile {
  id: number
  email: string
  name: string
  nickname: string
  phoneNumber: string
  postalCode: string | null
  address: string
  detailAddress: string
  gender: 'MALE' | 'FEMALE'
  profileImageUrl: string | null
  defaultTryOnImageUrl: string | null
  memberType: MyMemberType
  businessVerificationStatus: MyBusinessVerificationStatus
  onboardingCompleted: boolean
}

export interface MySummaryCounts {
  orders: number
  sales: number
  wishes: number
  followers: number
  unreadNotifications: number
}

export interface MySummary {
  profile: MyProfile
  counts: MySummaryCounts
  pointBalance: number
  pendingSettlementAmount: number
  salesPerformance: MySalesPerformance
  settlementSummary: MySettlementSummary
  todoCounts: MyTodoCounts
  productStatusCounts: MyProductStatusCounts
  monthlyRevenue: MyMonthlyRevenue[]
}

export interface MySalesPerformance {
  soldCount: number
  grossRevenue: number
  netRevenue: number
  averageOrderAmount: number
  sellThroughRate: number
  repeatBuyerCount: number
}

export interface MySettlementSummary {
  settledAmount: number
  pendingAmount: number
  escrowAmount: number
  withdrawableAmount: number
  lastSettledAt: string
}

export interface MyTodoCounts {
  shippingPending: number
  scheduledLives: number
  refundRequests: number
}

export interface MyProductStatusCounts {
  onSale: number
  auctionScheduled: number
  sold: number
}

export interface MyMonthlyRevenue {
  month: string
  revenue: number
  soldCount: number
}

export interface MyProductItem {
  id: number
  product: ProductListItem
  status: MyProductStatus
  updatedAt: string
}

export interface MyOrderItem {
  id: number
  type: 'DIRECT' | 'AUCTION'
  status: MyOrderStatus
  productName: string
  productThumbnailUrl: string
  sellerNickname: string
  paidAmount: number
  createdAt: string
  recipientName: string
  recipientPhoneNumber: string
  postalCode: string
  address: string
  detailAddress: string
}

export interface MySaleItem {
  id: number
  status: MyOrderStatus
  settlementStatus: MySettlementStatus
  productName: string
  productThumbnailUrl: string
  buyerNickname: string
  paidAmount: number
  createdAt: string
  recipientName: string
  recipientPhoneNumber: string
  postalCode: string
  address: string
  detailAddress: string
}

export interface MyLiveItem {
  id: number
  title: string
  status: MyLiveStatus
  thumbnailUrl: string
  productCount: number
  viewerCount: number
  broadcastAt: string
}

export interface MyWishItem {
  product: ProductListItem
  wishedAt: string
}

export interface MySocialUser {
  id: number
  nickname: string
  profileImageUrl: string | null
  introduction: string
  followerCount: number
  followingCount: number
  followedAt: string
  isFollowing: boolean
}

export interface MyPageViewData {
  summary: MySummary
  products: MyProductItem[]
  orders: MyOrderItem[]
  sales: MySaleItem[]
  lives: MyLiveItem[]
  wishes: MyWishItem[]
  followers: MySocialUser[]
  followings: MySocialUser[]
  wishMeta: PageMeta
}

export interface MyProfileUpdateRequest {
  nickname: string
  phoneNumber: string
  postalCode: string | null
  address: string
  detailAddress: string
  gender: 'MALE' | 'FEMALE'
}
