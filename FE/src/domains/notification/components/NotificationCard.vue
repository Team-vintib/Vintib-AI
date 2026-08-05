<script setup lang="ts">
import {
  NOTIFICATION_CATEGORY_ICONS,
  NOTIFICATION_CATEGORY_LABELS,
} from '@/domains/notification/constants/notificationOptions'

import type { NotificationItem } from '@/domains/notification/types/notification.types'

const props = defineProps<{
  notification: NotificationItem
  disabled?: boolean
}>()

const emit = defineEmits<{
  select: [notification: NotificationItem]
}>()

const formatCreatedAt = (createdAt: string) => {
  const date = new Date(createdAt)

  if (Number.isNaN(date.getTime())) {
    return createdAt
  }

  const diffMs = Date.now() - date.getTime()
  const diffMinutes = Math.floor(diffMs / 60_000)

  if (diffMinutes < 1) return '방금 전'
  if (diffMinutes < 60) return `${diffMinutes}분 전`

  const diffHours = Math.floor(diffMinutes / 60)
  if (diffHours < 24) return `${diffHours}시간 전`

  const diffDays = Math.floor(diffHours / 24)
  if (diffDays < 7) return `${diffDays}일 전`

  return new Intl.DateTimeFormat('ko-KR', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

const getCategoryIcon = (notification: NotificationItem) =>
  notification.category === 'ALL' ? 'receipt' : NOTIFICATION_CATEGORY_ICONS[notification.category]
</script>

<template>
  <button
    class="notification-card"
    :class="{ 'notification-card--read': notification.isRead }"
    type="button"
    :disabled="disabled"
    @click="emit('select', props.notification)"
  >
    <span
      class="notification-card__icon"
      :class="`notification-card__icon--${notification.category.toLowerCase()}`"
      aria-hidden="true"
    >
      <svg
        v-if="getCategoryIcon(notification) === 'broadcast'"
        viewBox="0 0 24 24"
      >
        <path d="M6 8.5 12 5l6 3.5v7L12 19l-6-3.5v-7Z" />
        <path d="M12 9v6m-3-3h6" />
      </svg>
      <svg v-else-if="getCategoryIcon(notification) === 'bid'" viewBox="0 0 24 24">
        <path d="m7 7 4 4m-2-6 6 6m-8 2 4 4" />
        <path d="m14 4 6 6-3 3-6-6 3-3Z" />
        <path d="M4 20h8" />
      </svg>
      <svg
        v-else-if="getCategoryIcon(notification) === 'receipt'"
        viewBox="0 0 24 24"
      >
        <path d="M7 4h10v16l-2-1.2-2 1.2-2-1.2-2 1.2-2-1.2V4Z" />
        <path d="M9.5 9h5m-5 4h5" />
      </svg>
      <svg v-else-if="getCategoryIcon(notification) === 'truck'" viewBox="0 0 24 24">
        <path d="M4 6h10v9H4V6Zm10 3h3.5L20 12v3h-6V9Z" />
        <path d="M7.5 18h.01M17 18h.01" />
      </svg>
      <svg v-else viewBox="0 0 24 24">
        <path d="M12 3v18m5-14.5H9.8a3 3 0 0 0 0 6H14a3 3 0 0 1 0 6H7" />
      </svg>
    </span>

    <span class="notification-card__content">
      <span class="notification-card__meta">
        <span class="notification-card__category">
          {{ NOTIFICATION_CATEGORY_LABELS[notification.category] }}
        </span>
        <time :datetime="notification.createdAt">{{ formatCreatedAt(notification.createdAt) }}</time>
      </span>
      <span class="notification-card__title">
        <span v-if="!notification.isRead" class="notification-card__unread" aria-label="읽지 않음" />
        {{ notification.title }}
      </span>
      <span v-if="notification.body" class="notification-card__body">{{ notification.body }}</span>
    </span>
  </button>
</template>

<style scoped lang="scss">
.notification-card {
  display: grid;
  grid-template-columns: 44px minmax(0, 1fr);
  width: 100%;
  gap: var(--space-4);
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-primary);
  text-align: left;
  transition:
    border-color var(--transition-fast),
    box-shadow var(--transition-fast),
    transform var(--transition-fast);
}

.notification-card:hover:not(:disabled),
.notification-card:focus-visible {
  border-color: var(--color-border-strong);
  box-shadow: none;
  transform: translateY(-1px);
}

.notification-card:focus-visible {
  outline: 1px solid var(--color-primary);
  outline-offset: 2px;
}

.notification-card:disabled {
  cursor: wait;
  opacity: 0.72;
}

.notification-card--read {
  background: transparent;
}

.notification-card__icon {
  display: grid;
  width: 44px;
  height: 44px;
  border-radius: var(--radius-control);
  background: var(--color-primary-soft);
  color: var(--color-primary);
  place-items: center;
}

.notification-card__icon--live {
  background: var(--color-error-soft);
  color: var(--color-live);
}

.notification-card__icon--auction {
  background: var(--color-auction-soft);
  color: var(--color-auction);
}

.notification-card__icon--point {
  background: var(--color-ai-soft);
  color: var(--color-ai);
}

.notification-card__icon svg {
  width: 22px;
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.8;
}

.notification-card__content {
  display: grid;
  min-width: 0;
  gap: var(--space-1);
}

.notification-card__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-width: 0;
  gap: var(--space-3);
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-snug);
}

.notification-card__category {
  color: var(--color-primary);
}

.notification-card__title {
  display: flex;
  align-items: center;
  min-width: 0;
  gap: var(--space-2);
  color: var(--color-text-primary);
  font-size: var(--font-size-body);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-relaxed);
}

.notification-card__unread {
  flex: 0 0 auto;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--color-live);
}

.notification-card__body {
  overflow: hidden;
  color: var(--color-text-secondary);
  font-size: var(--font-size-button-small);
  line-height: var(--line-height-relaxed);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.notification-card--read .notification-card__title,
.notification-card--read .notification-card__body {
  color: var(--color-text-muted);
}

@media (max-width: 640px) {
  .notification-card {
    grid-template-columns: 38px minmax(0, 1fr);
    gap: var(--space-3);
    padding: var(--space-3);
  }

  .notification-card__icon {
    width: 38px;
    height: 38px;
  }

  .notification-card__meta {
    align-items: start;
    flex-direction: column;
    gap: 0;
  }
}
</style>
