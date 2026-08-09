import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import {
  getNotifications,
  getUnreadNotificationCount,
  markAllNotificationsAsRead,
  markNotificationAsRead,
  type NotificationApiCategory,
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

  /**
   * 알림센터 탭(카테고리) 전용 상태 — 위 items/unreadCount는 헤더 배지·팝업(GlobalNavigation,
   * NotificationPopup)이 항상 "전체" 기준으로 쓰므로, 탭 전환이 그쪽에 영향을 주지 않도록 별도로 둔다.
   */
  const categoryItems = ref<NotificationItem[]>([])
  const categoryLoadState = ref<NotificationLoadState>('idle')
  const categoryErrorMessage = ref('')
  const categoryPage = ref(1)
  const categorySize = ref(DEFAULT_PAGE_SIZE)
  const categoryTotalElements = ref(0)
  const categoryHasNext = ref(false)
  const categoryUnreadCount = ref(0)
  const categoryIsLoadingMore = ref(false)
  let categoryLoadRequestId = 0

  const recentItems = computed(() => items.value.slice(0, POPUP_PAGE_SIZE))
  const isLoading = computed(() => loadState.value === 'loading')
  const hasLoadError = computed(() => loadState.value === 'error')
  const isCategoryLoading = computed(() => categoryLoadState.value === 'loading')
  const hasCategoryLoadError = computed(() => categoryLoadState.value === 'error')

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
      const previousCategoryItem = categoryItems.value.find((item) => item.id === notificationId)
      const response = await markNotificationAsRead(userId, notificationId)
      removeItemIfRead(response.id, response.isRead)

      if (previousItem && !previousItem.isRead && response.isRead) {
        unreadCount.value = Math.max(unreadCount.value - 1, 0)
        totalElements.value = Math.max(totalElements.value - 1, 0)
      }
      if (previousCategoryItem && !previousCategoryItem.isRead && response.isRead) {
        categoryUnreadCount.value = Math.max(categoryUnreadCount.value - 1, 0)
        categoryTotalElements.value = Math.max(categoryTotalElements.value - 1, 0)
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

  /** 알림센터 탭 전용 "전체 읽음" — category가 null이면 전체, 아니면 그 카테고리만 읽음 처리한다. */
  const markCategoryAsRead = async (category: NotificationApiCategory | null) => {
    authStore.hydrateSession()

    const userId = authStore.user?.id
    if (!userId || isMarkingAllAsRead.value) {
      return 0
    }

    isMarkingAllAsRead.value = true

    try {
      const response = await markAllNotificationsAsRead(userId, category ?? undefined)
      categoryItems.value = []
      categoryUnreadCount.value = 0
      categoryTotalElements.value = 0
      categoryHasNext.value = false
      // 헤더 배지(전체 기준)도 방금 읽음 처리된 건수만큼 같이 줄여준다.
      unreadCount.value = Math.max(unreadCount.value - response.updatedCount, 0)
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
    categoryItems.value = categoryItems.value.filter((item) => item.id !== notificationId)
  }

  /** 알림센터 탭 전용 목록 조회 — category가 null이면 전체. */
  const loadCategoryNotifications = async (
    category: NotificationApiCategory | null,
    options: { append?: boolean; page?: number } = {},
  ) => {
    authStore.hydrateSession()

    const userId = authStore.user?.id
    if (!userId) {
      categoryItems.value = []
      categoryUnreadCount.value = 0
      categoryLoadState.value = 'error'
      categoryErrorMessage.value = '로그인 정보를 확인하지 못했습니다. 다시 로그인해 주세요.'
      return
    }

    const requestId = ++categoryLoadRequestId
    const shouldAppend = options.append === true
    const nextPage = options.page ?? categoryPage.value
    const apiCategory = category ?? undefined

    if (shouldAppend) {
      categoryIsLoadingMore.value = true
    } else {
      categoryLoadState.value = 'loading'
    }
    categoryErrorMessage.value = ''

    try {
      const [result, nextUnreadCount] = await Promise.all([
        getNotifications(userId, {
          page: nextPage,
          size: categorySize.value,
          unreadOnly: true,
          category: apiCategory,
        }),
        getUnreadNotificationCount(userId, apiCategory),
      ])

      if (requestId !== categoryLoadRequestId) return

      categoryItems.value = shouldAppend
        ? mergeNotificationItems(categoryItems.value, result.items)
        : result.items
      categoryPage.value = result.meta.page
      categorySize.value = result.meta.size
      categoryTotalElements.value = result.meta.totalElements
      categoryHasNext.value = result.hasNext
      categoryUnreadCount.value = nextUnreadCount
      categoryLoadState.value = 'success'
    } catch (error) {
      if (requestId !== categoryLoadRequestId) return

      const apiError = normalizeApiError(error)
      categoryErrorMessage.value = apiError.message
      categoryLoadState.value = 'error'
    } finally {
      if (requestId === categoryLoadRequestId) {
        categoryIsLoadingMore.value = false
      }
    }
  }

  const loadNextCategoryPage = async (category: NotificationApiCategory | null) => {
    if (!categoryHasNext.value || isCategoryLoading.value || categoryIsLoadingMore.value) {
      return
    }

    await loadCategoryNotifications(category, {
      append: true,
      page: categoryPage.value + 1,
    })
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
    categoryItems,
    categoryLoadState,
    categoryErrorMessage,
    categoryTotalElements,
    categoryHasNext,
    categoryUnreadCount,
    categoryIsLoadingMore,
    isCategoryLoading,
    hasCategoryLoadError,
    loadCategoryNotifications,
    loadNextCategoryPage,
    markCategoryAsRead,
  }
})
