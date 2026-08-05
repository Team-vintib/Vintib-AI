export const COURIER_CODES = [
  'LOTTE',
  'CJ',
  'HANJIN',
  'POST',
  'KYUNGDONG',
  'DAESIN',
  'LOGEN',
  'HAPDONG',
  'COUPANG',
  'WOORI',
] as const

export type CourierCode = (typeof COURIER_CODES)[number]

/** 배송지·송장 정보. 주문 배송지 조회/등록, 송장 조회/등록 4개 API가 모두 이 형태를 응답한다. */
export interface OrderShipmentInfo {
  recipientName: string
  recipientPhone: string
  zipcode: string
  address1: string
  address2: string | null
  courierCode: CourierCode | null
  courierName: string | null
  trackingNumber: string | null
  shippedAt: string | null
  deliveredAt: string | null
}

export interface ShipmentRegisterInput {
  courierCode: CourierCode
  trackingNumber: string
}
