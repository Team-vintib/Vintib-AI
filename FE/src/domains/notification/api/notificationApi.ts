import {
  getNotificationCategory,
  getNotificationRoute,
} from '@/domains/notification/constants/notificationOptions'
import type {
  NotificationCategory,
  NotificationItem,
  NotificationItemDto,
  NotificationListResult,
  NotificationReadAllResult,
} from '@/domains/notification/types/notification.types'
import { http } from '@/shared/api/http'
import type { ApiResponse, PageMeta, PageResponse } from '@/shared/types/api.types'

interface BackendPageResponse<T> {
  content: T[]
  page: number
  size: number
  totalElements: number
  totalPages: number
  hasNext: boolean
}

interface NotificationReadResponse {
  id: number
  isRead: boolean
}

interface NotificationUnreadCountResponse {
  unreadCount: number
}

/** 'ALL'은 BE가 모르는 값이다(생략 = 전체) — 쿼리 파라미터로 보낼 카테고리 타입은 그 값을 뺀다. */
export type NotificationApiCategory = Exclude<NotificationCategory, 'ALL'>

interface NotificationListParams {
  page?: number
  size?: number
  unreadOnly?: boolean
  category?: NotificationApiCategory
}

export const getNotifications = async (
  userId: number,
  { page = 1, size = 20, unreadOnly = false, category }: NotificationListParams = {},
): Promise<NotificationListResult> => {
  const response = await http.get<
    ApiResponse<PageResponse<NotificationItemDto> | BackendPageResponse<NotificationItemDto>>
  >(`/users/${userId}/alerts`, {
    params: {
      page: Math.max(page - 1, 0),
      size,
      unreadOnly,
      category,
    },
  })
  const pageResponse = normalizePageResponse(unwrapApiData(response.data))

  return {
    items: pageResponse.items.map(toNotificationItem),
    meta: pageResponse.meta,
    hasNext:
      pageResponse.hasNext ??
      pageResponse.meta.page < pageResponse.meta.totalPages,
  }
}

export const getUnreadNotificationCount = async (
  userId: number,
  category?: NotificationApiCategory,
) => {
  const response = await http.get<ApiResponse<NotificationUnreadCountResponse>>(
    `/users/${userId}/alerts/unread-count`,
    { params: { category } },
  )

  return unwrapApiData(response.data).unreadCount
}

export const markNotificationAsRead = async (userId: number, notificationId: number) => {
  const response = await http.patch<ApiResponse<NotificationReadResponse>>(
    `/users/${userId}/alerts/${notificationId}`,
  )

  return unwrapApiData(response.data)
}

export const markAllNotificationsAsRead = async (
  userId: number,
  category?: NotificationApiCategory,
): Promise<NotificationReadAllResult> => {
  const response = await http.patch<ApiResponse<NotificationReadAllResult>>(
    `/users/${userId}/alerts/read-all`,
    undefined,
    { params: { category } },
  )

  return unwrapApiData(response.data)
}

const unwrapApiData = <T>(response: ApiResponse<T>) => {
  if (!response.success || !response.data) {
    throw new Error(response.error?.message ?? '알림 API 요청에 실패했습니다.')
  }

  return response.data
}

const normalizePageResponse = <T>(
  response: PageResponse<T> | BackendPageResponse<T>,
): PageResponse<T> & { hasNext?: boolean } => {
  if ('items' in response) {
    return response
  }

  return {
    items: response.content,
    meta: {
      page: response.page + 1,
      size: response.size,
      totalElements: response.totalElements,
      totalPages: response.totalPages,
    } satisfies PageMeta,
    hasNext: response.hasNext,
  }
}

const toNotificationItem = (notification: NotificationItemDto): NotificationItem => ({
  id: notification.id,
  type: notification.type,
  title: notification.title,
  body: notification.body ?? '',
  refType: notification.refType,
  refId: notification.refId,
  isRead: notification.isRead,
  createdAt: notification.createdAt,
  category: getNotificationCategory(notification.type, notification.refType),
  route: getNotificationRoute(notification),
})
