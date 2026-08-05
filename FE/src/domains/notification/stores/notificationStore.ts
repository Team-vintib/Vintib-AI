import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import {
  getNotifications,
  getUnreadNotificationCount,
  markAllNotificationsAsRead,
  markNotificationAsRead,
} from '@/domains/notification/api/notificationApi'
import { useAuthStore } from '@/domains/auth/stores/authStore'
import { normalizeApiError } from '@/shared/api/http'

import type {
  NotificationItem,
  NotificationListResult,
  NotificationLoadState,
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
  const unreadCount = ref(0)
  const isMarkingAllAsRead = ref(false)
  const isLoadingMore = ref(false)
  const readingIds = ref<Set<number>>(new Set())
  let loadRequestId = 0

  const recentItems = computed(() => items.value.slice(0, POPUP_PAGE_SIZE))
  const isLoading = computed(() => loadState.value === 'loading')
  const hasLoadError = computed(() => loadState.value === 'error')

  const loadNotifications = async (
    options: { append?: boolean; page?: number; size?: number } = {},
  ) => {
    authStore.hydrateSession()

    const userId = authStore.user?.id
    if (!userId) {
      items.value = []
      unreadCount.value = 0
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
      const [result, nextUnreadCount] = await Promise.all([
        getNotifications(userId, {
          page: nextPage,
          size: nextSize,
          unreadOnly: true,
        }),
        getUnreadNotificationCount(userId),
      ])

      if (requestId !== loadRequestId) return

      applyListResult(result, shouldAppend)
      unreadCount.value = nextUnreadCount
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

  const markAsRead = async (notificationId: number) => {
    authStore.hydrateSession()

    const userId = authStore.user?.id
    if (!userId || readingIds.value.has(notificationId)) {
      return
    }

    readingIds.value = new Set(readingIds.value).add(notificationId)

    try {
      const previousItem = items.value.find((item) => item.id === notificationId)
      const response = await markNotificationAsRead(userId, notificationId)
      removeItemIfRead(response.id, response.isRead)
      if (previousItem && !previousItem.isRead && response.isRead) {
        unreadCount.value = Math.max(unreadCount.value - 1, 0)
        totalElements.value = Math.max(totalElements.value - 1, 0)
      }
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
      items.value = []
      unreadCount.value = 0
      totalElements.value = 0
      totalPages.value = 0
      hasNext.value = false
      return response.updatedCount
    } finally {
      isMarkingAllAsRead.value = false
    }
  }

  const removeItemIfRead = (notificationId: number, isRead: boolean) => {
    if (!isRead) {
      return
    }

    items.value = items.value.filter((item) => item.id !== notificationId)
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
    readingIds,
    loadNotifications,
    loadNextPage,
    markAsRead,
    markAllAsRead,
  }
})
