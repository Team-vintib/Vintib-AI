import {
  getNotificationCategory,
  getNotificationRoute,
} from '@/domains/notification/constants/notificationOptions'
import type {
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

interface NotificationListParams {
  page?: number
  size?: number
  unreadOnly?: boolean
}

export const getNotifications = async (
  userId: number,
  { page = 1, size = 20, unreadOnly = false }: NotificationListParams = {},
): Promise<NotificationListResult> => {
  const response = await http.get<
    ApiResponse<PageResponse<NotificationItemDto> | BackendPageResponse<NotificationItemDto>>
  >(`/users/${userId}/alerts`, {
    params: {
      page: Math.max(page - 1, 0),
      size,
      unreadOnly,
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

export const getUnreadNotificationCount = async (userId: number) => {
  const result = await getNotifications(userId, {
    page: 1,
    size: 1,
    unreadOnly: true,
  })

  return result.meta.totalElements
}

export const markNotificationAsRead = async (userId: number, notificationId: number) => {
  const response = await http.patch<ApiResponse<NotificationReadResponse>>(
    `/users/${userId}/alerts/${notificationId}`,
  )

  return unwrapApiData(response.data)
}

export const markAllNotificationsAsRead = async (
  userId: number,
): Promise<NotificationReadAllResult> => {
  const response = await http.patch<ApiResponse<NotificationReadAllResult>>(
    `/users/${userId}/alerts/read-all`,
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
