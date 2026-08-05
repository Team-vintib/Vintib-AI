import type { RefundReason, RefundStatus } from '@/domains/refund/types/refund.types'

export const REFUND_REASON_LABELS: Record<RefundReason, string> = {
  NOT_AS_DESCRIBED: '상품 설명과 다름',
  UNDISCLOSED_DEFECT: '미고지 하자',
  NOT_SHIPPED: '발송되지 않음',
  DUPLICATE_PAYMENT: '중복 결제',
  SYSTEM_ERROR: '시스템 오류',
}

export const REFUND_REASON_OPTIONS = (
  Object.keys(REFUND_REASON_LABELS) as RefundReason[]
).map((reason) => ({
  reason,
  label: REFUND_REASON_LABELS[reason],
}))

export const REFUND_STATUS_LABELS: Record<RefundStatus, string> = {
  REQUESTED: '검토 중',
  APPROVED: '승인 완료',
  REJECTED: '거절됨',
}
