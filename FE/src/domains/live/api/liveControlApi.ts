import { http } from '@/shared/api/http'

import type { ApiResponse } from '@/shared/types/api.types'
import type { LiveWatchStatus } from '@/domains/live/types/liveWatch.types'

export interface LiveStatusUpdateResponse {
  id: number
  hostId: number
  title: string
  thumbnailUrl: string | null
  status: LiveWatchStatus
  scheduledAt: string | null
  startedAt: string | null
  createdAt: string
}

export interface LiveVideoTokenResponse {
  roomName: string
  token: string
  serverUrl: string
  role: 'PUBLISHER' | 'VIEWER'
  expiresAt: string
}

export interface AuctionConfigureRequest {
  productId: number
  startPrice: number
  bidUnit: number
  durationSeconds: number
}

export interface AuctionConfigureResponse {
  id: number
  liveId: number
  productId: number
  startPrice: number
  bidUnit: number
  durationSeconds: number
  status: 'READY' | 'RUNNING' | 'ENDED' | 'CANCELED'
  currentPrice: number
  createdAt: string
}

export const updateLiveStatus = async (liveId: number, status: LiveWatchStatus) => {
  const { data } = await http.patch<ApiResponse<LiveStatusUpdateResponse>>(
    `/lives/${liveId}/status`,
    { status },
  )

  return unwrapApiData(data, '방송 상태를 변경하지 못했습니다.')
}

export const issueLiveVideoToken = async (liveId: number) => {
  const { data } = await http.post<ApiResponse<LiveVideoTokenResponse>>(
    `/lives/${liveId}/video-token`,
    null,
    {
      skipAuth: true,
    },
  )

  return unwrapApiData(data, '영상 접속 토큰을 발급받지 못했습니다.')
}

export const configureLiveAuction = async (
  liveId: number,
  request: AuctionConfigureRequest,
) => {
  const { data } = await http.post<ApiResponse<AuctionConfigureResponse>>(
    `/lives/${liveId}/auctions`,
    request,
  )

  return unwrapApiData(data, '경매 조건을 저장하지 못했습니다.')
}

const unwrapApiData = <T>(response: ApiResponse<T>, fallbackMessage: string) => {
  if (!response.success || response.data === null) {
    throw new Error(response.error?.message ?? fallbackMessage)
  }

  return response.data
}
