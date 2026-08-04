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
  // 종료 전이 응답의 종료 시각(오프셋 없는 KST 벽시계) — BE 016 §2.3에서 LiveResponse에 추가됨.
  endedAt: string | null
  createdAt: string
}

// PATCH /lives/{liveId}/current-product 응답(BE CurrentProductResponse).
// STOMP /topic/lives/{liveId}/product payload와 같은 모양이다.
export interface CurrentProductUpdateResponse {
  liveId: number
  currentProductId: number | null
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
  // skipAuth 없음: 로그인 토큰이 실려야 호스트가 PUBLISHER 토큰을 받는다(BE 013 #1).
  // 토큰이 없으면 서버가 VIEWER로 발급한다(비회원은 애초에 방송 페이지에 진입하지 못한다).
  const { data } = await http.post<ApiResponse<LiveVideoTokenResponse>>(
    `/lives/${liveId}/video-token`,
    null,
  )

  return unwrapApiData(data, '영상 접속 토큰을 발급받지 못했습니다.')
}

export const patchCurrentProduct = async (liveId: number, productId: number) => {
  const { data } = await http.patch<ApiResponse<CurrentProductUpdateResponse>>(
    `/lives/${liveId}/current-product`,
    { productId },
  )

  return unwrapApiData(data, '현재 상품을 전환하지 못했습니다.')
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
