import type { OrderShipmentInfo, ShipmentRegisterInput } from '@/domains/shipping/types/shipping.types'
import { http } from '@/shared/api/http'
import type { ApiResponse } from '@/shared/types/api.types'

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

export const getShipment = async (orderId: number): Promise<OrderShipmentInfo> => {
  const response = await http.get<ApiResponse<BackendOrderShipmentDto>>(
    `/orders/${orderId}/shipment`,
  )
  return toShipmentInfo(unwrapApiData(response.data, '배송 정보를 불러오지 못했습니다.'))
}

/** 송장 등록(SHIP-001). 판매자만 호출 가능. */
export const registerShipment = async (
  orderId: number,
  input: ShipmentRegisterInput,
): Promise<OrderShipmentInfo> => {
  const response = await http.post<ApiResponse<BackendOrderShipmentDto>>(
    `/orders/${orderId}/shipment`,
    input,
  )
  return toShipmentInfo(unwrapApiData(response.data, '송장 정보를 등록하지 못했습니다.'))
}
