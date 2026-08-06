<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import NotificationCard from '@/domains/notification/components/NotificationCard.vue'
import NotificationCenterState from '@/domains/notification/components/NotificationCenterState.vue'
import { NOTIFICATION_TABS } from '@/domains/notification/constants/notificationOptions'
import { useNotificationStore } from '@/domains/notification/stores/notificationStore'
import { normalizeApiError } from '@/shared/api/http'
import DefaultLayout from '@/shared/layouts/DefaultLayout.vue'

import type {
  NotificationCategory,
  NotificationItem,
} from '@/domains/notification/types/notification.types'

const notificationStore = useNotificationStore()
const router = useRouter()
const selectedCategory = ref<NotificationCategory>('ALL')
const actionErrorMessage = ref('')
const isMarkingCurrentFilterAsRead = ref(false)

const filteredNotifications = computed(() =>
  selectedCategory.value === 'ALL'
    ? notificationStore.items
    : notificationStore.items.filter((item) => item.category === selectedCategory.value),
)

const isLoading = computed(() => notificationStore.isLoading)
const hasLoadError = computed(() => notificationStore.hasLoadError)
const isEmpty = computed(
  () => notificationStore.loadState === 'success' && notificationStore.items.length === 0,
)
const isFilterEmpty = computed(
  () =>
    notificationStore.loadState === 'success' &&
    notificationStore.items.length > 0 &&
    filteredNotifications.value.length === 0,
)
const canLoadMore = computed(
  () =>
    selectedCategory.value === 'ALL' &&
    notificationStore.loadState === 'success' &&
    notificationStore.hasNext,
)
const currentFilterUnreadCount = computed(() =>
  selectedCategory.value === 'ALL' ? notificationStore.unreadCount : filteredNotifications.value.length,
)
const readAllButtonLabel = computed(() => {
  if (notificationStore.isMarkingAllAsRead || isMarkingCurrentFilterAsRead.value) {
    return '처리 중'
  }

  return selectedCategory.value === 'ALL' ? '전체 읽음' : '전체 읽음'
})

const resultStatusMessage = computed(() => {
  if (isLoading.value) return '알림 목록을 불러오는 중입니다.'
  if (hasLoadError.value) return notificationStore.errorMessage

  return `${filteredNotifications.value.length}개의 읽지 않은 알림을 표시합니다.`
})

const selectCategory = (category: NotificationCategory) => {
  selectedCategory.value = category
  actionErrorMessage.value = ''
}

const handleRetry = () => {
  void notificationStore.loadNotifications({ page: 1 })
}

const handleMarkAllAsRead = async () => {
  if (currentFilterUnreadCount.value === 0 || isMarkingCurrentFilterAsRead.value) {
    return
  }

  actionErrorMessage.value = ''
  isMarkingCurrentFilterAsRead.value = true

  try {
    if (selectedCategory.value === 'ALL') {
      await notificationStore.markAllAsRead()
      return
    }

    const currentFilterItems = [...filteredNotifications.value]
    await Promise.all(
      currentFilterItems.map((notification) => notificationStore.markAsRead(notification.id)),
    )
  } catch (error) {
    actionErrorMessage.value = normalizeApiError(error).message
  } finally {
    isMarkingCurrentFilterAsRead.value = false
  }
}

const handleLoadMore = async () => {
  actionErrorMessage.value = ''

  try {
    await notificationStore.loadNextPage()
  } catch (error) {
    actionErrorMessage.value = normalizeApiError(error).message
  }
}

const handleSelectNotification = async (notification: NotificationItem) => {
  actionErrorMessage.value = ''

  try {
    await notificationStore.markAsRead(notification.id)

    if (!notification.route) {
      actionErrorMessage.value = '연결된 화면이 아직 준비되지 않았습니다.'
      return
    }

    await router.push(notification.route)
  } catch (error) {
    actionErrorMessage.value = normalizeApiError(error).message
  }
}

onMounted(() => {
  void notificationStore.loadNotifications({ page: 1 })
})
</script>

<template>
  <DefaultLayout content-max-width="960px">
    <section class="notification-page" aria-label="알림센터">
      <div class="notification-page__actions">
        <button
          class="notification-page__read-all"
          type="button"
          :disabled="
            isLoading ||
            currentFilterUnreadCount === 0 ||
            notificationStore.isMarkingAllAsRead ||
            isMarkingCurrentFilterAsRead
          "
          @click="handleMarkAllAsRead"
        >
          {{ readAllButtonLabel }}
        </button>
      </div>

      <div class="notification-page__tabs" role="tablist" aria-label="알림 카테고리">
        <button
          v-for="tab in NOTIFICATION_TABS"
          :key="tab.id"
          type="button"
          role="tab"
          :class="{ 'notification-page__tab--active': selectedCategory === tab.id }"
          :aria-selected="selectedCategory === tab.id"
          :aria-current="selectedCategory === tab.id ? 'page' : undefined"
          :disabled="isLoading"
          @click="selectCategory(tab.id)"
        >
          <span>{{ tab.label }}</span>
        </button>
      </div>

      <p class="sr-only" aria-live="polite">{{ resultStatusMessage }}</p>

      <p v-if="actionErrorMessage" class="notification-page__action-error" role="alert">
        {{ actionErrorMessage }}
      </p>

      <NotificationCenterState v-if="isLoading" variant="loading" />

      <NotificationCenterState
        v-else-if="hasLoadError"
        variant="error"
        title="알림을 불러오지 못했습니다"
        :description="notificationStore.errorMessage"
        @action="handleRetry"
      />

      <NotificationCenterState
        v-else-if="isEmpty"
        variant="empty"
        title="읽지 않은 알림이 없습니다"
        description="새로운 소식이 생기면 이곳에 알림이 표시됩니다."
      />

      <NotificationCenterState
        v-else-if="isFilterEmpty"
        variant="filter-empty"
        title="선택한 카테고리의 알림이 없습니다"
        description="전체 탭에서 다른 알림을 확인할 수 있습니다."
        @action="selectCategory('ALL')"
      />

      <div v-else class="notification-page__list" aria-label="알림 목록">
        <NotificationCard
          v-for="notification in filteredNotifications"
          :key="notification.id"
          :notification="notification"
          :disabled="notificationStore.readingIds.has(notification.id)"
          @select="handleSelectNotification"
        />

        <div v-if="canLoadMore" class="notification-page__pagination">
          <button
            type="button"
            :disabled="notificationStore.isLoadingMore"
            @click="handleLoadMore"
          >
            {{ notificationStore.isLoadingMore ? '불러오는 중' : '더 보기' }}
          </button>
          <p>
            {{ notificationStore.items.length }}개 표시 중 · 전체
            {{ notificationStore.totalElements }}개
          </p>
        </div>
      </div>
    </section>
  </DefaultLayout>
</template>

<style scoped lang="scss">
.notification-page {
  display: grid;
  gap: var(--space-6);
}

.notification-page__actions {
  display: flex;
  justify-content: flex-end;
}

.notification-page__read-all {
  min-height: var(--button-height-small);
  padding: 0 var(--space-4);
  border: 0;
  border-radius: var(--radius-control);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-bold);
  white-space: nowrap;
}

.notification-page__read-all:disabled {
  background: var(--color-surface-secondary);
  color: var(--color-text-muted);
}

.notification-page__tabs {
  display: flex;
  align-items: end;
  gap: var(--space-4);
  border-bottom: 1px solid var(--color-border);
}

.notification-page__tabs button {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 40px;
  padding: 0 2px;
  border: 0;
  background: transparent;
  color: var(--color-text-muted);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-semibold);
  transition:
    color var(--transition-base);
}

.notification-page__tabs button::after {
  position: absolute;
  bottom: -1px;
  right: 0;
  left: 0;
  height: 3px;
  border-radius: 0;
  background: transparent;
  content: '';
  transform: scaleX(0);
  transform-origin: center;
  transition:
    background-color var(--transition-base),
    transform var(--transition-base);
}

.notification-page__tabs button:hover:not(:disabled),
.notification-page__tabs button:focus-visible {
  color: var(--color-primary);
}

button.notification-page__tab--active {
  color: var(--color-primary);
  font-weight: var(--font-weight-extrabold);
}

button.notification-page__tab--active::after {
  background: var(--color-primary);
  transform: scaleX(1);
}

.notification-page__tabs button:focus-visible,
.notification-page__read-all:focus-visible {
  outline: 1px solid var(--color-primary);
  outline-offset: 2px;
}

.notification-page__action-error {
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-control);
  background: var(--color-error-soft);
  color: var(--color-error);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-relaxed);
}

.notification-page__list {
  display: grid;
  gap: var(--space-3);
}

.notification-page__pagination {
  display: grid;
  justify-items: center;
  gap: var(--space-2);
  padding: var(--space-4) 0 0;
}

.notification-page__pagination button {
  min-height: var(--button-height-standard);
  padding: 0 var(--space-6);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-bold);
}

.notification-page__pagination button:hover:not(:disabled),
.notification-page__pagination button:focus-visible {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.notification-page__pagination button:focus-visible {
  outline: 1px solid var(--color-primary);
  outline-offset: 2px;
}

.notification-page__pagination p {
  color: var(--color-text-muted);
  font-size: var(--font-size-caption);
  line-height: var(--line-height-control);
}

@media (max-width: 640px) {
  .notification-page__read-all {
    width: 100%;
  }

  .notification-page__tabs {
    overflow-x: auto;
    gap: var(--space-4);
  }

  .notification-page__tabs button {
    flex: 0 0 auto;
    min-height: 40px;
    font-size: var(--font-size-button-small);
  }
}
</style>
