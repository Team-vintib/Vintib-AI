export type OrderStatus =
  | 'PAID'
  | 'SHIPPING'
  | 'DELIVERED'
  | 'CONFIRMED'
  | 'SETTLED'
  | 'REFUNDED'
  | 'CANCELED'

export interface OrderProductSummary {
  id: number
  sellerId: number
  title: string
  price: number
  saleType: 'DIRECT_SALE' | 'AUCTION'
  saleStatus: string
  conditionGrade: string | null
  sizeLabel: string | null
}

export interface OrderSummary {
  orderId: number
  product: OrderProductSummary
  buyerId: number
  buyerNickname: string
  sellerId: number
  sellerNickname: string
  orderPrice: number
  status: OrderStatus
  createdAt: string
}

export interface OrderAddressInput {
  recipientName: string
  recipientPhone: string
  zipcode: string
  address1: string
  address2?: string
}
