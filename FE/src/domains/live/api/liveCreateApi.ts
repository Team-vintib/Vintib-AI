import { http } from '@/shared/api/http'

import type { ApiResponse } from '@/shared/types/api.types'

export type LiveCreateStatus = 'LIVE' | 'SCHEDULED' | 'ENDED' | 'CANCELED'

export interface LiveCreateResponse {
  id: number
  hostId: number
  title: string
  thumbnailUrl: string | null
  status: LiveCreateStatus
  scheduledAt: string | null
  startedAt: string | null
  createdAt: string
}

interface CreateLiveRequest {
  title: string
  thumbnailUrl: string | null
  productIds: number[]
}

interface ScheduleLiveRequest extends CreateLiveRequest {
  scheduledAt: string
}

export const createLiveNow = async (request: CreateLiveRequest) => {
  const { data } = await http.post<ApiResponse<LiveCreateResponse>>('/lives', request)

  return unwrapLiveCreateResponse(data)
}

export const scheduleLive = async (request: ScheduleLiveRequest) => {
  const { data } = await http.post<ApiResponse<LiveCreateResponse>>('/lives/schedule', request)

  return unwrapLiveCreateResponse(data)
}

const unwrapLiveCreateResponse = (response: ApiResponse<LiveCreateResponse>) => {
  if (!response.success || !response.data) {
    throw new Error(response.error?.message ?? '라이브를 생성하지 못했습니다.')
  }

  return response.data
}
