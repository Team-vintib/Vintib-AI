import type { OrderAddressInput, OrderSummary } from '@/domains/order/types/order.types'
import type { OrderShipmentInfo } from '@/domains/shipping/types/shipping.types'
import { http } from '@/shared/api/http'
import type { ApiResponse } from '@/shared/types/api.types'

interface BackendOrderProductDto {
  id: number
  sellerId: number
  categoryId: number | null
  brandId: number | null
  title: string
  description?: string | null
  conditionGrade?: string | null
  sizeLabel?: string | null
  saleType: 'DIRECT_SALE' | 'AUCTION'
  saleStatus?: string
  price: number | null
  createdAt: string
}

interface BackendOrderSummaryDto {
  orderId: number
  product: BackendOrderProductDto
  buyerId: number
  buyerNickname: string
  sellerId: number
  sellerNickname: string
  orderPrice: number
  status: string
  createdAt: string
}

interface BackendOrderShipmentDto {
  recipientName: string
  recipientPhone: string
  zipcode: string
  address1: string
  address2: string | null
  courierCode: string | null
  courierName: string | null
  trackingNumber: string | null
  shippedAt: string | null
  deliveredAt: string | null
}

const unwrapApiData = <T>(response: ApiResponse<T>, fallbackMessage: string): T => {
  if (!response.success || response.data === null) {
    throw new Error(response.error?.message ?? fallbackMessage)
  }

  return response.data
}

const toOrderSummary = (dto: BackendOrderSummaryDto): OrderSummary => ({
  orderId: dto.orderId,
  product: {
    id: dto.product.id,
    sellerId: dto.product.sellerId,
    title: dto.product.title,
    price: dto.product.price ?? 0,
    saleType: dto.product.saleType,
    saleStatus: dto.product.saleStatus ?? '',
    conditionGrade: dto.product.conditionGrade ?? null,
    sizeLabel: dto.product.sizeLabel ?? null,
  },
  buyerId: dto.buyerId,
  buyerNickname: dto.buyerNickname,
  sellerId: dto.sellerId,
  sellerNickname: dto.sellerNickname,
  orderPrice: dto.orderPrice,
  status: dto.status as OrderSummary['status'],
  createdAt: dto.createdAt,
})

const toShipmentInfo = (dto: BackendOrderShipmentDto): OrderShipmentInfo => ({
  recipientName: dto.recipientName,
  recipientPhone: dto.recipientPhone,
  zipcode: dto.zipcode,
  address1: dto.address1,
  address2: dto.address2,
  courierCode: dto.courierCode as OrderShipmentInfo['courierCode'],
  courierName: dto.courierName,
  trackingNumber: dto.trackingNumber,
  shippedAt: dto.shippedAt,
  deliveredAt: dto.deliveredAt,
})

/** 상시 판매 상품 즉시구매(SALE-001/002). 결제는 포인트로만 처리되며 실패 시 BE 에러 메시지를 던진다. */
export const createOrder = async (productId: number): Promise<OrderSummary> => {
  const response = await http.post<ApiResponse<BackendOrderSummaryDto>>('/orders', { productId })
  return toOrderSummary(unwrapApiData(response.data, '주문을 생성하지 못했습니다.'))
}

export const getOrderDetail = async (orderId: number): Promise<OrderSummary> => {
  const response = await http.get<ApiResponse<BackendOrderSummaryDto>>(`/orders/${orderId}`)
  return toOrderSummary(unwrapApiData(response.data, '주문 정보를 불러오지 못했습니다.'))
}

export const getOrderAddress = async (orderId: number): Promise<OrderShipmentInfo> => {
  const response = await http.get<ApiResponse<BackendOrderShipmentDto>>(
    `/orders/${orderId}/address`,
  )
  return toShipmentInfo(unwrapApiData(response.data, '배송지 정보를 불러오지 못했습니다.'))
}

export const updateOrderAddress = async (
  orderId: number,
  input: OrderAddressInput,
): Promise<OrderShipmentInfo> => {
  const response = await http.patch<ApiResponse<BackendOrderShipmentDto>>(
    `/orders/${orderId}/address`,
    input,
  )
  return toShipmentInfo(unwrapApiData(response.data, '배송지 정보를 저장하지 못했습니다.'))
}

/** 구매 확정(ORDER-002/003). 배송완료(DELIVERED) 상태에서만 호출 가능. */
export const confirmOrder = async (orderId: number): Promise<OrderSummary> => {
  const response = await http.post<ApiResponse<BackendOrderSummaryDto>>(
    `/orders/${orderId}/confirmation`,
  )
  return toOrderSummary(unwrapApiData(response.data, '구매 확정 처리를 하지 못했습니다.'))
}
