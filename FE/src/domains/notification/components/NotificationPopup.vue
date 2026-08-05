<script setup lang="ts">
import NotificationCard from '@/domains/notification/components/NotificationCard.vue'
import { useNotificationStore } from '@/domains/notification/stores/notificationStore'
import { normalizeApiError } from '@/shared/api/http'

import type { NotificationItem } from '@/domains/notification/types/notification.types'

defineProps<{
  isOpen: boolean
}>()

const emit = defineEmits<{
  close: []
  openCenter: []
  select: [notification: NotificationItem]
}>()

const notificationStore = useNotificationStore()

const handleMarkAllAsRead = async () => {
  try {
    await notificationStore.markAllAsRead()
  } catch (error) {
    notificationStore.errorMessage = normalizeApiError(error).message
  }
}
</script>

<template>
  <section v-if="isOpen" class="notification-popup" aria-label="최근 알림">
    <header class="notification-popup__header">
      <div>
        <h2>알림</h2>
        <p>안 읽음 {{ notificationStore.unreadCount }}개</p>
      </div>
      <button
        type="button"
        :disabled="
          notificationStore.unreadCount === 0 || notificationStore.isMarkingAllAsRead
        "
        @click="handleMarkAllAsRead"
      >
        {{ notificationStore.isMarkingAllAsRead ? '처리 중' : '모두 읽음' }}
      </button>
    </header>

    <div v-if="notificationStore.isLoading" class="notification-popup__message" role="status">
      알림을 불러오는 중입니다.
    </div>

    <div v-else-if="notificationStore.hasLoadError" class="notification-popup__message" role="alert">
      <p>{{ notificationStore.errorMessage }}</p>
      <button type="button" @click="notificationStore.loadNotifications({ page: 1 })">
        다시 시도
      </button>
    </div>

    <div v-else-if="notificationStore.recentItems.length === 0" class="notification-popup__message">
      읽지 않은 알림이 없습니다.
    </div>

    <div v-else class="notification-popup__list">
      <NotificationCard
        v-for="notification in notificationStore.recentItems"
        :key="notification.id"
        :notification="notification"
        :disabled="notificationStore.readingIds.has(notification.id)"
        @select="emit('select', notification)"
      />
    </div>

    <footer class="notification-popup__footer">
      <button type="button" @click="emit('openCenter')">알림센터 보기</button>
    </footer>
  </section>
</template>

<style scoped lang="scss">
.notification-popup {
  position: absolute;
  top: calc(100% + 10px);
  right: 0;
  z-index: 70;
  display: grid;
  width: min(420px, calc(100vw - 32px));
  max-height: min(680px, calc(100vh - 92px));
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  box-shadow: none;
}

.notification-popup__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-4);
  border-bottom: 1px solid var(--color-border);
}

.notification-popup__header h2 {
  color: var(--color-text-primary);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-lg);
}

.notification-popup__header p {
  color: var(--color-text-secondary);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-control);
}

.notification-popup__header button,
.notification-popup__message button,
.notification-popup__footer button {
  min-height: var(--button-height-small);
  padding: 0 var(--space-3);
  border: 0;
  border-radius: var(--radius-control);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-bold);
  white-space: nowrap;
}

.notification-popup__header button:disabled {
  background: var(--color-surface-secondary);
  color: var(--color-text-muted);
}

.notification-popup__list {
  display: grid;
  max-height: 464px;
  overflow-y: auto;
  gap: var(--space-2);
  padding: var(--space-3);
}

.notification-popup__list :deep(.notification-card) {
  grid-template-columns: 38px minmax(0, 1fr);
  padding: var(--space-3);
}

.notification-popup__list :deep(.notification-card__icon) {
  width: 38px;
  height: 38px;
}

.notification-popup__message {
  display: grid;
  min-height: 156px;
  padding: var(--space-6);
  color: var(--color-text-secondary);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-semibold);
  text-align: center;
  place-items: center;
  gap: var(--space-3);
}

.notification-popup__footer {
  padding: var(--space-3);
  border-top: 1px solid var(--color-border);
}

.notification-popup__footer button {
  width: 100%;
}

@media (max-width: 640px) {
  .notification-popup {
    position: fixed;
    top: 68px;
    right: var(--space-4);
    left: var(--space-4);
    width: auto;
  }
}
</style>
