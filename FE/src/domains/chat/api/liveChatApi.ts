import { http } from '@/shared/api/http'

import type { ApiResponse } from '@/shared/types/api.types'

export type BackendChatSenderType = 'USER' | 'SYSTEM' | 'AI'
export type BackendReactionType = 'HEART' | 'FIRE' | 'CLAP' | 'WOW'

export interface BackendChatMessage {
  messageId: number
  senderId: number | null
  senderNickname: string
  senderProfileImageUrl: string | null
  senderType: BackendChatSenderType
  content: string
  createdAt: string
  clientMessageId: string | null
}

export interface BackendReaction {
  liveId: number
  type: BackendReactionType
  senderId: number | null
  senderNickname: string
  sentAt: string
}

export interface BackendViewerCount {
  liveId: number
  viewerCount: number
}

interface BackendCursorPageResponse<T> {
  content: T[]
  nextCursor: number | null
  hasNext: boolean
}

export const getLiveChatMessages = async (liveId: number, size = 50) => {
  const response = await http.get<ApiResponse<BackendCursorPageResponse<BackendChatMessage>>>(
    `/lives/${liveId}/chat-messages`,
    {
      params: { size },
      skipAuth: true,
    },
  )
  const responseBody = response.data

  if (!responseBody.success || !responseBody.data) {
    throw new Error(responseBody.error?.message ?? '채팅 내역을 불러오지 못했습니다.')
  }

  return responseBody.data
}
