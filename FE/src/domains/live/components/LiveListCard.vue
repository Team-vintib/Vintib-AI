<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '@/domains/auth/stores/authStore'
import { registerLiveReminder } from '@/domains/live/api/liveWatchApi'
import fallbackLiveThumbnail from '@/assets/images/products/product-denim-jacket.webp'
import { ROUTE_NAMES } from '@/shared/constants/routes'

import type { LiveListItem } from '@/domains/live/types/liveList.types'

const props = defineProps<{
  live: LiveListItem
}>()

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const isReminderPending = ref(false)
const isReminderSet = ref(false)
const actionMessage = ref('')
const displayThumbnailUrl = computed(() => props.live.thumbnailUrl || fallbackLiveThumbnail)
const handleThumbnailError = (event: Event) => {
  const target = event.target

  if (target instanceof HTMLImageElement) {
    target.onerror = null
    target.src = fallbackLiveThumbnail
  }
}

const statusLabel = computed(() => {
  if (props.live.status === 'LIVE') {
    return 'LIVE'
  }

  if (props.live.status === 'SCHEDULED') {
    return '예정'
  }

  return '종료'
})

const statusClass = computed(() => ({
  'live-list-card__badge--live': props.live.status === 'LIVE',
  'live-list-card__badge--scheduled': props.live.status === 'SCHEDULED',
  'live-list-card__badge--ended': props.live.status === 'ENDED',
}))

const broadcastLabel = computed(() => {
  const formattedDate = new Intl.DateTimeFormat('ko-KR', {
    month: 'long',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  }).format(new Date(props.live.broadcastAt))

  if (props.live.status === 'LIVE') {
    return `${formattedDate} 시작`
  }

  if (props.live.status === 'SCHEDULED') {
    return `${formattedDate} 예정`
  }

  return `${formattedDate} 종료`
})

const canEnterLive = computed(() => props.live.status === 'LIVE')
const isScheduledLive = computed(() => props.live.status === 'SCHEDULED')
const isEndedLive = computed(() => props.live.status === 'ENDED')
const actionLabel = computed(() => {
  if (canEnterLive.value) return '입장하기'
  if (isScheduledLive.value) return isReminderSet.value ? '예약 완료' : '예약하기'
  return '종료된 라이브'
})

const goToLive = async () => {
  if (!canEnterLive.value) {
    return
  }

  await router.push({ name: ROUTE_NAMES.LIVE_WATCH, params: { liveId: props.live.id } })
}

const reserveLive = async () => {
  if (!isScheduledLive.value || isReminderPending.value || isReminderSet.value) {
    return
  }

  await authStore.validateStoredSession()

  if (!authStore.isAuthenticated) {
    await router.push({
      name: ROUTE_NAMES.AUTH_LOGIN,
      query: { redirect: route.fullPath },
    })
    return
  }

  isReminderPending.value = true
  actionMessage.value = ''

  try {
    const result = await registerLiveReminder(props.live.id)
    isReminderSet.value = result.isReminderSet
    actionMessage.value = '예약 알림을 신청했습니다.'
  } catch {
    actionMessage.value = '예약하지 못했습니다.'
  } finally {
    isReminderPending.value = false
  }
}

const handleCardClick = () => {
  void goToLive()
}

const handleActionClick = () => {
  if (canEnterLive.value) {
    void goToLive()
    return
  }

  void reserveLive()
}
</script>

<template>
  <article
    class="live-list-card"
    :class="{
      'live-list-card--clickable': canEnterLive,
      'live-list-card--ended': isEndedLive,
    }"
    :role="canEnterLive ? 'link' : undefined"
    :tabindex="canEnterLive ? 0 : undefined"
    :aria-label="canEnterLive ? `${live.title}, ${statusLabel} 방송 입장` : undefined"
    @click="handleCardClick"
    @keydown.enter.prevent="handleCardClick"
    @keydown.space.prevent="handleCardClick"
  >
    <span class="live-list-card__media">
      <img
        class="live-list-card__image"
        :src="displayThumbnailUrl"
        :alt="`${live.title} 썸네일`"
        @error="handleThumbnailError"
      />
      <span class="live-list-card__badge" :class="statusClass">
        {{ statusLabel }}
      </span>
    </span>

    <span class="live-list-card__body">
      <strong class="live-list-card__title">{{ live.title }}</strong>
      <span class="live-list-card__seller">판매자 {{ live.sellerName }}</span>
      <span class="live-list-card__meta">{{ broadcastLabel }}</span>
      <span class="live-list-card__viewer">
        <span aria-hidden="true">●</span>
        시청자 {{ live.viewerCount.toLocaleString('ko-KR') }}명
      </span>
      <button
        class="live-list-card__action"
        type="button"
        :class="{
          'live-list-card__action--outline': isScheduledLive,
          'live-list-card__action--disabled': isEndedLive,
        }"
        :disabled="isEndedLive || isReminderPending || isReminderSet"
        @click.stop="handleActionClick"
      >
        {{ isReminderPending ? '처리 중' : actionLabel }}
      </button>
      <span v-if="actionMessage" class="live-list-card__message" role="status">
        {{ actionMessage }}
      </span>
    </span>
  </article>
</template>

<style scoped lang="scss">
.live-list-card {
  display: grid;
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
  transition:
    border-color 220ms ease,
    background-color 220ms ease,
    transform 620ms cubic-bezier(0.22, 1, 0.36, 1);
}

.live-list-card--clickable {
  cursor: pointer;
}

.live-list-card--clickable:hover {
  border-color: var(--color-border-strong);
  transform: translateY(-3px);
}

.live-list-card--clickable:focus-visible {
  outline: 1px solid var(--color-primary);
  outline-offset: 2px;
}

.live-list-card--ended {
  opacity: 0.5;
}

.live-list-card__media {
  position: relative;
  display: block;
  overflow: hidden;
  aspect-ratio: 4 / 3;
  background: var(--color-image-frame);
}

.live-list-card__image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  filter: saturate(0.86) contrast(1.05) brightness(0.94);
  transition: transform 620ms cubic-bezier(0.22, 1, 0.36, 1);
}

.live-list-card--clickable:hover .live-list-card__image {
  transform: scale(1.045);
}

.live-list-card__badge {
  position: absolute;
  top: 0;
  left: 0;
  display: inline-flex;
  align-items: center;
  padding: 6px 9px;
  border-radius: 0 0 var(--radius-badge) 0;
  color: var(--color-text-primary);
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 500;
  letter-spacing: 0.16em;
  line-height: 1;
}

.live-list-card__badge--live {
  gap: 5px;
  background: var(--color-accent);
  color: var(--color-primary-strong);
}

.live-list-card__badge--live::before {
  width: 4px;
  height: 4px;
  background: currentColor;
  content: '';
  animation: vtPulse 1.7s ease-in-out infinite;
}

.live-list-card__badge--scheduled {
  background: rgba(10, 10, 10, 0.82);
  color: var(--color-text-primary);
}

.live-list-card__badge--ended {
  background: rgba(10, 10, 10, 0.82);
  color: var(--color-text-caption);
}

.live-list-card__body {
  display: grid;
  gap: var(--space-2);
  padding: var(--space-5);
}

.live-list-card__title {
  display: -webkit-box;
  overflow: hidden;
  color: var(--color-text-primary);
  font-size: 16px;
  font-weight: 500;
  line-height: 1.35;
  letter-spacing: -0.02em;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.live-list-card__seller,
.live-list-card__meta {
  color: var(--color-text-muted);
  font-size: 12px;
  font-weight: 300;
  line-height: 18px;
}

.live-list-card__viewer {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: var(--color-text-secondary);
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.02em;
  line-height: 18px;
  font-variant-numeric: tabular-nums;
}

.live-list-card__viewer span {
  color: var(--color-accent);
  font-size: 8px;
}

.live-list-card__action {
  justify-self: start;
  min-width: 104px;
  height: 40px;
  margin-top: var(--space-2);
  padding: 0 var(--space-4);
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-control);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-medium);
  transition:
    background-color 160ms ease,
    border-color 160ms ease,
    color 160ms ease;
}

.live-list-card__action:hover:not(:disabled) {
  border-color: var(--color-primary-hover);
  background: var(--color-primary-hover);
  color: var(--color-primary-strong);
}

.live-list-card__action--outline {
  border-color: var(--color-border-input);
  background: transparent;
  color: var(--color-text-muted);
}

.live-list-card__action--outline:hover:not(:disabled) {
  border-color: var(--color-primary);
  background: transparent;
  color: var(--color-primary);
}

.live-list-card__action--disabled,
.live-list-card__action:disabled {
  border-color: var(--color-border);
  background: var(--color-surface-secondary);
  color: var(--color-text-muted);
  cursor: not-allowed;
}

.live-list-card__message {
  color: var(--color-text-secondary);
  font-size: var(--font-size-caption);
  line-height: 20px;
}

@media (max-width: 640px) {
  .live-list-card__body {
    padding: var(--space-4);
  }

  .live-list-card__title {
    font-size: 16px;
    line-height: 24px;
  }
}
</style>
