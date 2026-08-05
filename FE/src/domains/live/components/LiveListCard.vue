<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '@/domains/auth/stores/authStore'
import { registerLiveReminder } from '@/domains/live/api/liveWatchApi'
import fallbackLiveThumbnail from '@/assets/images/products/product-denim-jacket.webp'
import { ROUTE_NAMES } from '@/shared/constants/routes'

import type { LiveListItem } from '@/domains/live/types/liveList.types'

const props = withDefaults(
  defineProps<{
    live: LiveListItem
    variant?: 'default' | 'profile'
  }>(),
  {
    variant: 'default',
  },
)

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
      'live-list-card--profile': variant === 'profile',
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
      <span v-if="variant !== 'profile'" class="live-list-card__badge" :class="statusClass">
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
  grid-template-rows: auto 1fr;
  overflow: hidden;
  height: 100%;
  border: 1px solid var(--color-border);
  border-radius: 15px;
  background: var(--color-surface);
  transition:
    border-color var(--transition-standard),
    background-color var(--transition-standard),
    transform var(--transition-emphasized);
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
  aspect-ratio: 4 / 5;
  background: var(--color-image-frame);
}

.live-list-card__image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  filter: saturate(0.86) contrast(1.05) brightness(0.94);
  transition: transform var(--transition-emphasized);
}

.live-list-card--clickable:hover .live-list-card__image {
  transform: scale(1.045);
}

// 프로필 화면 전용 모양: 홈 라이브 카드(LiveCard.vue)와 같은 박스 없는 카드 — 이미지 프레임에만
// 얇은 border를 두고, hover도 뜨는 대신 이미지 밝기만 미세하게 바뀐다. 글씨 크기/구성(뱃지 숨김,
// 큰 폰트)은 위 --profile 규칙을 그대로 따른다.
.live-list-card--profile {
  gap: var(--space-3);
  border: 0;
  border-radius: 0;
  background: transparent;
}

.live-list-card--profile.live-list-card--clickable:hover {
  border-color: transparent;
  transform: none;
}

.live-list-card--profile .live-list-card__media {
  aspect-ratio: 4 / 3;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-media);
  transition: border-color var(--transition-standard);
}

.live-list-card--profile.live-list-card--clickable:hover .live-list-card__media {
  border-color: var(--color-border-strong);
}

.live-list-card--profile .live-list-card__media::after {
  position: absolute;
  inset: 0;
  background: linear-gradient(0deg, var(--overlay-scrim-medium), transparent 42%);
  content: '';
}

.live-list-card--profile.live-list-card--clickable:hover .live-list-card__image {
  filter: saturate(0.86) contrast(1.05) brightness(1.02);
  transform: none;
}

.live-list-card__badge {
  position: absolute;
  top: var(--space-2);
  left: var(--space-2);
  display: inline-flex;
  align-items: center;
  padding: 5px var(--space-2);
  border: 1px solid var(--color-border-strong);
  border-radius: 10px;
  color: var(--color-text-primary);
  font-size: calc(var(--font-size-caption) - 1px);
  font-weight: var(--font-weight-semibold);
  letter-spacing: 0.03em;
  line-height: var(--line-height-xs);
  backdrop-filter: blur(4px);
}

.live-list-card__badge--live {
  gap: 5px;
  background: var(--color-accent);
  color: var(--color-primary-strong);
}

.live-list-card__badge--live::before {
  width: var(--space-1);
  height: var(--space-1);
  background: currentColor;
  content: '';
  animation: vtPulse var(--duration-pulse) ease-in-out infinite;
}

.live-list-card__badge--scheduled {
  background: var(--overlay-scrim-strong);
  color: var(--color-text-primary);
}

.live-list-card__badge--ended {
  background: var(--overlay-scrim-strong);
  color: var(--color-text-caption);
}

.live-list-card__body {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-4);
}

.live-list-card--profile .live-list-card__body {
  padding: 0;
}

.live-list-card__title {
  display: -webkit-box;
  overflow: hidden;
  min-height: 2.7em;
  color: var(--color-text-primary);
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-medium);
  line-height: 1.35;
  letter-spacing: -0.02em;
  overflow-wrap: anywhere;
  word-break: keep-all;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.live-list-card__seller,
.live-list-card__meta {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-light);
  line-height: var(--line-height-snug);
  overflow-wrap: anywhere;
  word-break: keep-all;
}

.live-list-card__viewer {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: var(--color-text-secondary);
  font-family: var(--font-mono);
  font-size: var(--font-size-2xs);
  letter-spacing: 0.02em;
  line-height: var(--line-height-snug);
  font-variant-numeric: tabular-nums;
}

.live-list-card__viewer span {
  color: var(--color-accent);
  font-size: var(--font-size-4xs);
}

// 프로필 화면 전용: 예정/LIVE 뱃지를 숨기는 대신(variant prop) 판매자·예약일·시청자 수 글씨를 키운다.
.live-list-card--profile .live-list-card__seller,
.live-list-card--profile .live-list-card__meta {
  font-size: var(--font-size-body);
}

.live-list-card--profile .live-list-card__viewer {
  font-size: var(--font-size-caption);
}

.live-list-card__action {
  justify-self: start;
  min-width: 104px;
  height: var(--button-height-sm);
  margin-top: auto;
  padding: 0 var(--space-4);
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-control);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-medium);
  transition:
    background-color var(--transition-base),
    border-color var(--transition-base),
    color var(--transition-base);
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
  line-height: var(--line-height-control);
}

@media (max-width: 640px) {
  .live-list-card__body {
    padding: var(--space-4);
  }

  .live-list-card__title {
    font-size: var(--font-size-md);
    line-height: var(--line-height-body);
  }
}
</style>
