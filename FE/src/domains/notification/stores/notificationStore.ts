import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import {
  getNotifications,
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
  const isMarkingAllAsRead = ref(false)
  const readingIds = ref<Set<number>>(new Set())
  let loadRequestId = 0

  const unreadCount = computed(() => items.value.filter((item) => !item.isRead).length)
  const recentItems = computed(() => items.value.slice(0, POPUP_PAGE_SIZE))
  const isLoading = computed(() => loadState.value === 'loading')
  const hasLoadError = computed(() => loadState.value === 'error')

  const loadNotifications = async (options: { page?: number; size?: number } = {}) => {
    authStore.hydrateSession()

    const userId = authStore.user?.id
    if (!userId) {
      items.value = []
      loadState.value = 'error'
      errorMessage.value = '로그인 정보를 확인하지 못했습니다. 다시 로그인해 주세요.'
      return
    }

    const requestId = ++loadRequestId
    const nextPage = options.page ?? page.value
    const nextSize = options.size ?? size.value

    loadState.value = 'loading'
    errorMessage.value = ''

    try {
      const result = await getNotifications(userId, {
        page: nextPage,
        size: nextSize,
      })

      if (requestId !== loadRequestId) return

      applyListResult(result)
      loadState.value = 'success'
    } catch (error) {
      if (requestId !== loadRequestId) return

      const apiError = normalizeApiError(error)
      errorMessage.value = apiError.message
      loadState.value = 'error'
    }
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

  const applyListResult = (result: NotificationListResult) => {
    items.value = result.items
    page.value = result.meta.page
    size.value = result.meta.size
    totalElements.value = result.meta.totalElements
    totalPages.value = result.meta.totalPages
    hasNext.value = result.hasNext
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
    readingIds,
    loadNotifications,
    markAsRead,
    markAllAsRead,
  }
})
