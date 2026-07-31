import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import {
  getNotifications,
  markAllNotificationsAsRead,
  markNotificationAsRead,
} from '@/domains/notification/api/notificationApi'
import { NOTIFICATION_MOCK_DATA } from '@/domains/notification/constants/notificationMockData'
import {
  getNotificationCategory,
  getNotificationRoute,
} from '@/domains/notification/constants/notificationOptions'
import { useAuthStore } from '@/domains/auth/stores/authStore'
import { normalizeApiError } from '@/shared/api/http'

import type {
  NotificationItemDto,
  NotificationItem,
  NotificationListResult,
  NotificationLoadState,
  NotificationMockScenario,
} from '@/domains/notification/types/notification.types'

const DEFAULT_PAGE_SIZE = 20
const POPUP_PAGE_SIZE = 6

export const useNotificationStore = defineStore('notification', () => {
  const authStore = useAuthStore()
  const items = ref<NotificationItem[]>([])
  const loadState = ref<NotificationLoadState>('idle')
  const errorMessage = ref('')
  const page = ref(1)
  const size = ref(DEFAULT_PAGE_SIZE)
  const totalElements = ref(0)
  const totalPages = ref(0)
  const hasNext = ref(false)
  const isMarkingAllAsRead = ref(false)
  const isLoadingMore = ref(false)
  const activeMockScenario = ref<NotificationMockScenario | null>(null)
  const readingIds = ref<Set<number>>(new Set())
  let loadRequestId = 0

  const unreadCount = computed(() => items.value.filter((item) => !item.isRead).length)
  const recentItems = computed(() => items.value.slice(0, POPUP_PAGE_SIZE))
  const isLoading = computed(() => loadState.value === 'loading')
  const hasLoadError = computed(() => loadState.value === 'error')

  const loadNotifications = async (
    options: { append?: boolean; page?: number; size?: number } = {},
  ) => {
    if (activeMockScenario.value) {
      loadMockNotifications(activeMockScenario.value, options)
      return
    }

    authStore.hydrateSession()

    const userId = authStore.user?.id
    if (!userId) {
      items.value = []
      loadState.value = 'error'
      errorMessage.value = '로그인 정보를 확인하지 못했습니다. 다시 로그인해 주세요.'
      return
    }

    const requestId = ++loadRequestId
    const shouldAppend = options.append === true
    const nextPage = options.page ?? page.value
    const nextSize = options.size ?? size.value

    if (shouldAppend) {
      isLoadingMore.value = true
    } else {
      loadState.value = 'loading'
    }
    errorMessage.value = ''

    try {
      const result = await getNotifications(userId, {
        page: nextPage,
        size: nextSize,
      })

      if (requestId !== loadRequestId) return

      applyListResult(result, shouldAppend)
      loadState.value = 'success'
    } catch (error) {
      if (requestId !== loadRequestId) return

      const apiError = normalizeApiError(error)
      errorMessage.value = apiError.message
      loadState.value = 'error'
    } finally {
      if (requestId === loadRequestId) {
        isLoadingMore.value = false
      }
    }
  }

  const loadNextPage = async () => {
    if (!hasNext.value || isLoading.value || isLoadingMore.value) {
      return
    }

    await loadNotifications({
      append: true,
      page: page.value + 1,
      size: size.value,
    })
  }

  const loadMockNotifications = (
    scenario: NotificationMockScenario,
    options: { append?: boolean; page?: number; size?: number } = {},
  ) => {
    activeMockScenario.value = scenario
    errorMessage.value = ''

    if (scenario === 'loading') {
      items.value = []
      loadState.value = 'loading'
      return
    }

    if (scenario === 'error') {
      items.value = []
      loadState.value = 'error'
      errorMessage.value = '수동 확인용 알림 오류 상태입니다.'
      return
    }

    const nextPage = options.page ?? 1
    const nextSize = options.size ?? size.value
    const shouldAppend = options.append === true
    const sourceItems = scenario === 'empty' ? [] : NOTIFICATION_MOCK_DATA
    const pageStartIndex = (nextPage - 1) * nextSize
    const pageItems = sourceItems.slice(pageStartIndex, pageStartIndex + nextSize)

    applyListResult(
      {
        items: pageItems.map(toMockNotificationItem),
        meta: {
          page: nextPage,
          size: nextSize,
          totalElements: sourceItems.length,
          totalPages: Math.ceil(sourceItems.length / nextSize),
        },
        hasNext: pageStartIndex + nextSize < sourceItems.length,
      },
      shouldAppend,
    )
    loadState.value = 'success'
  }

  const clearMockMode = () => {
    activeMockScenario.value = null
  }

  const markAsRead = async (notificationId: number) => {
    authStore.hydrateSession()

    const userId = authStore.user?.id
    if (!userId || readingIds.value.has(notificationId)) {
      return
    }

    readingIds.value = new Set(readingIds.value).add(notificationId)

    try {
      const response = await markNotificationAsRead(userId, notificationId)
      updateItemReadState(response.id, response.isRead)
    } finally {
      const nextReadingIds = new Set(readingIds.value)
      nextReadingIds.delete(notificationId)
      readingIds.value = nextReadingIds
    }
  }

  const markAllAsRead = async () => {
    authStore.hydrateSession()

    const userId = authStore.user?.id
    if (!userId || isMarkingAllAsRead.value) {
      return 0
    }

    isMarkingAllAsRead.value = true

    try {
      const response = await markAllNotificationsAsRead(userId)
      items.value = items.value.map((item) => ({ ...item, isRead: true }))
      return response.updatedCount
    } finally {
      isMarkingAllAsRead.value = false
    }
  }

  const updateItemReadState = (notificationId: number, isRead: boolean) => {
    items.value = items.value.map((item) =>
      item.id === notificationId ? { ...item, isRead } : item,
    )
  }

  const applyListResult = (result: NotificationListResult, append = false) => {
    items.value = append ? mergeNotificationItems(items.value, result.items) : result.items
    page.value = result.meta.page
    size.value = result.meta.size
    totalElements.value = result.meta.totalElements
    totalPages.value = result.meta.totalPages
    hasNext.value = result.hasNext
  }

  const mergeNotificationItems = (
    previousItems: NotificationItem[],
    nextItems: NotificationItem[],
  ) => {
    const itemMap = new Map<number, NotificationItem>()

    for (const item of previousItems) {
      itemMap.set(item.id, item)
    }

    for (const item of nextItems) {
      itemMap.set(item.id, item)
    }

    return Array.from(itemMap.values())
  }

  return {
    items,
    recentItems,
    unreadCount,
    loadState,
    errorMessage,
    page,
    size,
    totalElements,
    totalPages,
    hasNext,
    isLoading,
    hasLoadError,
    isMarkingAllAsRead,
    isLoadingMore,
    activeMockScenario,
    readingIds,
    loadNotifications,
    loadMockNotifications,
    clearMockMode,
    loadNextPage,
    markAsRead,
    markAllAsRead,
  }
})

const toMockNotificationItem = (notification: NotificationItemDto): NotificationItem => ({
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
