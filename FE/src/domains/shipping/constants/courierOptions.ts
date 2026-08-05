import type { CourierCode } from '@/domains/shipping/types/shipping.types'
import { COURIER_CODES } from '@/domains/shipping/types/shipping.types'

export const COURIER_CODE_LABELS: Record<CourierCode, string> = {
  LOTTE: '롯데택배',
  CJ: 'CJ대한통운',
  HANJIN: '한진택배',
  POST: '우체국택배',
  KYUNGDONG: '경동택배',
  DAESIN: '대신택배',
  LOGEN: '로젠택배',
  HAPDONG: '합동택배',
  COUPANG: '쿠팡택배',
  WOORI: '우리택배',
}

export const COURIER_OPTIONS = COURIER_CODES.map((code) => ({
  code,
  label: COURIER_CODE_LABELS[code],
}))
