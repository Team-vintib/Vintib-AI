import { http } from '@/shared/api/http'
import { normalizeApiError } from '@/shared/api/http'

import type {
  AuctionBidPage,
  AuctionConfigureRequest,
  AuctionConfigured,
  AuctionEventMessage,
  AuctionSnapshot,
  AuctionWinner,
  BroadcastEndSummary,
  LiveUnsoldProduct,
} from '@/domains/auction/types/liveAuction.types'
import type { ApiResponse } from '@/shared/types/api.types'

export const getCurrentAuction = async (liveId: number) => {
  const { data } = await http.get<ApiResponse<AuctionSnapshot | null>>(
    `/lives/${liveId}/auctions/current`,
    { skipAuth: true },
  )

  if (!data.success) {
    throw new Error(data.error?.message ?? '현재 경매 정보를 불러오지 못했습니다.')
  }

  return data.data
}

export const configureAuction = async (liveId: number, request: AuctionConfigureRequest) => {
  const { data } = await http.post<ApiResponse<AuctionConfigured>>(
    `/lives/${liveId}/auctions`,
    request,
  )

  return unwrapApiData(data, '경매 조건을 저장하지 못했습니다.')
}

export const startAuction = async (auctionId: number) => {
  const { data } = await http.post<ApiResponse<AuctionSnapshot>>(`/auctions/${auctionId}/start`)

  return unwrapApiData(data, '경매를 시작하지 못했습니다.')
}

export const placeAuctionBid = async (auctionId: number, amount: number) => {
  const { data } = await http.post<ApiResponse<AuctionSnapshot>>(`/auctions/${auctionId}/bids`, {
    amount,
  })

  return unwrapApiData(data, '입찰하지 못했습니다.')
}

export const getAuctionBids = async (auctionId: number, cursor?: number, size = 20) => {
  const { data } = await http.get<ApiResponse<AuctionBidPage>>(`/auctions/${auctionId}/bids`, {
    params: {
      ...(cursor === undefined ? {} : { cursor }),
      size,
    },
  })

  return unwrapApiData(data, '입찰 내역을 불러오지 못했습니다.')
}

export const getAuctionWinner = async (auctionId: number) => {
  const { data } = await http.get<ApiResponse<AuctionWinner>>(`/auctions/${auctionId}/winner`, {
    skipAuth: true,
  })

  return unwrapApiData(data, '경매 결과를 불러오지 못했습니다.')
}

export const getBroadcastSummary = async (liveId: number) => {
  const { data } = await http.get<ApiResponse<BroadcastEndSummary>>(`/lives/${liveId}/summary`)

  return unwrapApiData(data, '방송 결과를 불러오지 못했습니다.')
}

export const getLiveUnsoldProducts = async (liveId: number) => {
  const { data } = await http.get<ApiResponse<LiveUnsoldProduct[]>>(
    `/lives/${liveId}/unsold-products`,
  )

  return unwrapApiData(data, '유찰 상품을 불러오지 못했습니다.')
}

export const isAuctionEventMessage = (body: unknown): body is AuctionEventMessage => {
  if (!body || typeof body !== 'object' || !('type' in body) || !('auction' in body)) {
    return false
  }

  const event = body as Partial<AuctionEventMessage>
  const snapshot = event.auction

  return Boolean(
    ['AUCTION_STARTED', 'BID_PLACED', 'AUCTION_CLOSED'].includes(String(event.type)) &&
    snapshot &&
    typeof snapshot === 'object' &&
    Number.isInteger(snapshot.auctionId) &&
    Number.isInteger(snapshot.liveId) &&
    Number.isInteger(snapshot.productId) &&
    typeof snapshot.status === 'string',
  )
}

export const getAuctionErrorMessage = (error: unknown) => {
  const apiError = normalizeApiError(error)
  const messages: Record<string, string> = {
    A001: '경매가 종료되었거나 현재 입찰할 수 없는 상태입니다.',
    A002: '입찰가가 변경되었습니다. 최신 금액을 다시 확인해 주세요.',
    A005: '경매를 찾을 수 없습니다.',
    A006: '이미 시작했거나 종료된 경매입니다.',
    A007: '이 방송에서 다른 경매가 진행 중입니다.',
    A008: '다른 사용자가 먼저 입찰했습니다. 최신 금액으로 다시 시도해 주세요.',
    A009: '현재 최고 입찰자는 연속으로 입찰할 수 없습니다.',
    A010: '같은 금액의 입찰이 이미 처리되었습니다.',
    A011: '다른 경매에서 최고 입찰자로 참여 중입니다.',
    W001: '사용 가능한 포인트가 부족합니다.',
  }

  return messages[apiError.code] ?? apiError.message
}

const unwrapApiData = <T>(response: ApiResponse<T>, fallbackMessage: string) => {
  if (!response.success || response.data === null) {
    throw new Error(response.error?.message ?? fallbackMessage)
  }

  return response.data
}
