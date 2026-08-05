import type {
  RefundCreateInput,
  RefundRequestInfo,
  RefundReviewInput,
} from '@/domains/refund/types/refund.types'
import { http } from '@/shared/api/http'
import type { ApiResponse } from '@/shared/types/api.types'

interface BackendRefundDto {
  refundId: number
  orderId: number
  reason: string
  detailReason: string
  status: string
  rejectionReason: string | null
  requestedAt: string
  reviewedAt: string | null
}

const unwrapApiData = <T>(response: ApiResponse<T>, fallbackMessage: string): T => {
  if (!response.success || response.data === null) {
    throw new Error(response.error?.message ?? fallbackMessage)
  }

  return response.data
}

const toRefundRequestInfo = (dto: BackendRefundDto): RefundRequestInfo => ({
  refundId: dto.refundId,
  orderId: dto.orderId,
  reason: dto.reason as RefundRequestInfo['reason'],
  detailReason: dto.detailReason,
  status: dto.status as RefundRequestInfo['status'],
  rejectionReason: dto.rejectionReason,
  requestedAt: dto.requestedAt,
  reviewedAt: dto.reviewedAt,
})

/** 환불 요청 등록(REFUND-001). 구매자만 호출 가능. */
export const createRefund = async (
  orderId: number,
  input: RefundCreateInput,
): Promise<RefundRequestInfo> => {
  const response = await http.post<ApiResponse<BackendRefundDto>>(
    `/orders/${orderId}/refunds`,
    input,
  )
  return toRefundRequestInfo(unwrapApiData(response.data, '환불을 요청하지 못했습니다.'))
}

export const getRefunds = async (orderId: number): Promise<RefundRequestInfo[]> => {
  const response = await http.get<ApiResponse<BackendRefundDto[]>>(`/orders/${orderId}/refunds`)
  return unwrapApiData(response.data, '환불 요청 내역을 불러오지 못했습니다.').map(
    toRefundRequestInfo,
  )
}

/** 환불 승인/거절(REFUND-002). 판매자만 호출 가능. */
export const reviewRefund = async (
  refundId: number,
  input: RefundReviewInput,
): Promise<RefundRequestInfo> => {
  const response = await http.patch<ApiResponse<BackendRefundDto>>(`/refunds/${refundId}`, input)
  return toRefundRequestInfo(unwrapApiData(response.data, '환불 처리를 하지 못했습니다.'))
}
