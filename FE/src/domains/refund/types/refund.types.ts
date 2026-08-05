export type RefundReason =
  | 'NOT_AS_DESCRIBED'
  | 'UNDISCLOSED_DEFECT'
  | 'NOT_SHIPPED'
  | 'DUPLICATE_PAYMENT'
  | 'SYSTEM_ERROR'

export type RefundStatus = 'REQUESTED' | 'APPROVED' | 'REJECTED'
export type RefundDecision = 'APPROVED' | 'REJECTED'

export interface RefundRequestInfo {
  refundId: number
  orderId: number
  reason: RefundReason
  detailReason: string
  status: RefundStatus
  rejectionReason: string | null
  requestedAt: string
  reviewedAt: string | null
}

export interface RefundCreateInput {
  reason: RefundReason
  detailReason: string
}

export interface RefundReviewInput {
  decision: RefundDecision
  rejectionReason?: string
}
