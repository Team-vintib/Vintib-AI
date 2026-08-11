<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'

import {
  type BackendChatBlockedNotice,
  type BackendChatMessage,
  type BackendReaction,
  type BackendReactionType,
  type BackendViewerCount,
  getLiveChatMessages,
} from '@/domains/chat/api/liveChatApi'
import { LIVE_REACTION_EMOJIS } from '@/domains/chat/constants/liveChatMockData'
import { useAuthStore } from '@/domains/auth/stores/authStore'
import { isLiveRealtimeApiEnabled, LiveRealtimeClient } from '@/domains/live/api/liveRealtimeClient'
import AppInlineNotice from '@/shared/components/AppInlineNotice.vue'

import type { LiveChatMessage, LiveReactionEmoji } from '@/domains/chat/types/liveChat.types'
import type { LiveWatchStatus } from '@/domains/live/types/liveWatch.types'

const props = defineProps<{
  liveId: number
  hostId: number
  status: LiveWatchStatus
}>()

const emit = defineEmits<{
  viewerCount: [count: number]
  realtimeReady: [client: LiveRealtimeClient]
}>()

interface LiveReactionParticle {
  id: number
  emoji: LiveReactionEmoji
  offset: number
}

const REACTION_TYPES: BackendReactionType[] = ['HEART', 'FIRE', 'CLAP', 'WOW']
const REALTIME_ENABLED = isLiveRealtimeApiEnabled()

const authStore = useAuthStore()
const { isAuthenticated } = storeToRefs(authStore)
const messages = ref<LiveChatMessage[]>([])
const draft = ref('')
const activeReaction = ref<LiveReactionEmoji | null>(null)
const reactionParticles = ref<LiveReactionParticle[]>([])
const messageList = ref<HTMLElement | null>(null)
const isConnected = ref(false)
const errorMessage = ref('')
// 차단 안내는 시청자가 반드시 보고 넘어가야 하는 알림이라, 채팅 패널 안 배너로 잠깐
// 스쳤다 사라지게 두지 않는다 — 화면 한가운데 띄우고 X를 눌러야만 닫힌다.
// 자동 소멸 타이머도, 재전송 성공 시 자동으로 걷어내던 처리도 두지 않는다.
const isBlockedNoticeOpen = ref(false)
const isMuteNoticeOpen = ref(false)
const isChatCollapsed = ref(false)
const muteRemainingSeconds = ref<number | null>(null)
let realtimeClient: LiveRealtimeClient | null = null
let mockMessageSequence = 0
let reactionSequence = 0
let reactionTimer: number | null = null
let muteCountdownTimer: number | null = null
let blockedNoticeTimer: number | null = null
let muteNoticeTimer: number | null = null

// 중앙 안내(차단·음소거)가 떠 있는 시간. 15초가 지나면 스스로 사라지고, 그 전에 X를 눌러도
// 사라진다. 채팅 잠금 시간은 서버가 주는 muteRemainingSeconds를 따로 따라간다.
const CENTER_NOTICE_DURATION_MS = 15000
const reactionParticleTimers = new Map<number, number>()

const isMuted = computed(() => muteRemainingSeconds.value !== null)

const closeBlockedNotice = () => {
  isBlockedNoticeOpen.value = false

  if (blockedNoticeTimer !== null) {
    window.clearTimeout(blockedNoticeTimer)
    blockedNoticeTimer = null
  }
}

const closeMuteNotice = () => {
  isMuteNoticeOpen.value = false

  if (muteNoticeTimer !== null) {
    window.clearTimeout(muteNoticeTimer)
    muteNoticeTimer = null
  }
}

const openBlockedNotice = () => {
  closeBlockedNotice()
  isBlockedNoticeOpen.value = true
  blockedNoticeTimer = window.setTimeout(closeBlockedNotice, CENTER_NOTICE_DURATION_MS)
}

const openMuteNotice = () => {
  closeMuteNotice()
  isMuteNoticeOpen.value = true
  muteNoticeTimer = window.setTimeout(closeMuteNotice, CENTER_NOTICE_DURATION_MS)
}

// 음소거 배너/입력창 잠금은 "풀릴 때"가 명확히 보여야 한다 — 서버가 다시 알려주지 않으므로
// 로컬에서 1초마다 스스로 카운트다운하다가 0이 되면 잠금을 해제한다.
const startMuteCountdown = (seconds: number) => {
  if (muteCountdownTimer !== null) {
    window.clearInterval(muteCountdownTimer)
  }
  // 음소거는 "차단이 반복돼 이제 아예 막혔다"는 상위 안내다 — 아직 안 사라진 차단 안내가
  // 남아 있으면 같이 겹쳐 뜨므로 여기서 걷어낸다.
  closeBlockedNotice()
  openMuteNotice()
  muteRemainingSeconds.value = Math.max(1, Math.ceil(seconds))
  muteCountdownTimer = window.setInterval(() => {
    if (muteRemainingSeconds.value === null) return
    const next = muteRemainingSeconds.value - 1
    if (next <= 0) {
      muteRemainingSeconds.value = null
      // 잠금이 안내보다 먼저 풀리는 경우(서버가 15초보다 짧게 줄 때)엔 안내도 같이 걷는다.
      closeMuteNotice()
      if (muteCountdownTimer !== null) {
        window.clearInterval(muteCountdownTimer)
        muteCountdownTimer = null
      }
    } else {
      muteRemainingSeconds.value = next
    }
  }, 1000)
}

const canPublishRealtime = computed(
  () => REALTIME_ENABLED && isConnected.value && isAuthenticated.value,
)

const composerPlaceholder = computed(() => {
  if (props.status !== 'LIVE') return '방송 중에만 채팅할 수 있습니다'
  if (isMuted.value) return `도배·욕설 반복으로 ${muteRemainingSeconds.value}초간 채팅이 제한됩니다`
  if (REALTIME_ENABLED && !isAuthenticated.value) return '로그인 후 채팅할 수 있습니다'
  if (REALTIME_ENABLED && !isConnected.value) return '채팅 연결 중...'
  return '채팅...'
})

const canSubmitMessage = computed(
  () =>
    props.status === 'LIVE' &&
    !isMuted.value &&
    draft.value.trim().length > 0 &&
    canPublishRealtime.value,
)

const scrollToLatestMessage = async () => {
  await nextTick()

  if (messageList.value) {
    messageList.value.scrollTop = messageList.value.scrollHeight
  }
}

const loadChatHistory = async () => {
  if (!REALTIME_ENABLED) {
    messages.value = []
    return
  }

  try {
    const response = await getLiveChatMessages(props.liveId)
    messages.value = response.content
      .slice()
      .reverse()
      .map((message) => mapChatMessage(message, props.hostId))
    void scrollToLatestMessage()
  } catch {
    messages.value = []
    errorMessage.value = '채팅 내역을 불러오지 못했습니다.'
  }
}

const connectRealtime = () => {
  disconnectRealtime()

  if (!REALTIME_ENABLED || props.status !== 'LIVE') {
    isConnected.value = false
    return
  }

  realtimeClient = new LiveRealtimeClient({
    onConnect: () => {
      isConnected.value = true
      errorMessage.value = ''
      subscribeRealtime()

      // 시청 화면(LiveWatchPage)이 이 연결에 방송 상태·현재 상품 구독을 얹을 수 있도록
      // 연결된 클라이언트를 부모에 넘긴다(연결을 하나로 합쳐 시청자수 중복 집계 방지).
      if (realtimeClient) {
        emit('realtimeReady', realtimeClient)
      }
    },
    onDisconnect: () => {
      isConnected.value = false
    },
    onError: () => {
      errorMessage.value = '실시간 연결을 확인해 주세요.'
    },
  })
  realtimeClient.connect()
}

const subscribeRealtime = () => {
  if (!realtimeClient) return

  realtimeClient.subscribe(`/topic/lives/${props.liveId}/chat`, (body) => {
    if (!isBackendChatMessage(body)) return

    const nextMessage = mapChatMessage(body, props.hostId)
    const existingIndex = body.clientMessageId
      ? messages.value.findIndex((message) => message.id === body.clientMessageId)
      : -1

    if (existingIndex >= 0) {
      messages.value.splice(existingIndex, 1, nextMessage)
    } else {
      messages.value.push(nextMessage)
    }

    void scrollToLatestMessage()
  })

  realtimeClient.subscribe(`/topic/lives/${props.liveId}/reactions`, (body) => {
    if (!isBackendReaction(body)) return

    const emoji = reactionEmojiOf(body.type)

    if (emoji) {
      showReactionParticle(emoji)
    }
  })

  realtimeClient.subscribe(`/topic/lives/${props.liveId}/viewers`, (body) => {
    if (isBackendViewerCount(body)) {
      emit('viewerCount', body.viewerCount)
    }
  })

  realtimeClient.subscribe('/user/queue/errors', (body) => {
    // AI 판정(HIDE/BLOCK)으로 브로드캐스트가 생략된 내 메시지는, 브로드캐스트로 오는 "진짜
    // 메시지 치환" 신호를 영영 못 받는다 — 낙관적 렌더로 먼저 그려둔 말풍선이 내 화면에만
    // 유령처럼 계속 남아있던 문제(실측으로 확인, -571 후속)를 여기서 지워서 해소한다.
    if (isBackendChatBlockedNotice(body)) {
      messages.value = messages.value.filter((message) => message.id !== body.clientMessageId)
      if (typeof body.muteRemainingSeconds === 'number') {
        // 반복 위반으로 방송 내 임시 음소거(CH025) — 몇 초 남았는지 계속 보여야 해서 이건
        // 중앙 안내가 아니라 채팅 패널 안 배너로 두고, 잠금이 풀릴 때까지 입력창을 막는다.
        startMuteCountdown(body.muteRemainingSeconds)
      } else {
        openBlockedNotice()
      }
      return
    }

    // 반응을 너무 빠르게 눌렀을 때(L011)는 사용자에게 표시하지 않고 조용히 무시한다.
    if (isSuppressedRealtimeError(body)) return
    errorMessage.value = getRealtimeErrorMessage(body)
  })
}

const disconnectRealtime = () => {
  realtimeClient?.disconnect()
  realtimeClient = null
  isConnected.value = false
}

const submitMessage = () => {
  const body = draft.value.trim()

  if (!body || props.status !== 'LIVE' || isMuted.value) return

  if (!REALTIME_ENABLED) {
    mockMessageSequence += 1
    messages.value.push({
      id: `local-chat-${mockMessageSequence}`,
      author: '나',
      body,
      role: 'VIEWER',
    })
    draft.value = ''
    void scrollToLatestMessage()
    return
  }

  if (!realtimeClient?.connected() || !isAuthenticated.value) {
    errorMessage.value = '로그인 후 채팅할 수 있습니다.'
    return
  }

  const clientMessageId = `local-chat-${Date.now()}-${mockMessageSequence++}`
  messages.value.push({
    id: clientMessageId,
    author: authStore.user?.name || authStore.user?.email || '나',
    body,
    role: authStore.user?.id === props.hostId ? 'HOST' : 'VIEWER',
  })
  realtimeClient.publish(`/app/lives/${props.liveId}/chat`, {
    content: body,
    clientMessageId,
  })
  draft.value = ''
  void scrollToLatestMessage()
}

const react = (emoji: LiveReactionEmoji) => {
  if (props.status !== 'LIVE') return

  if (!REALTIME_ENABLED) {
    return
  }

  if (!realtimeClient?.connected() || !isAuthenticated.value) {
    errorMessage.value = '로그인 후 반응할 수 있습니다.'
    return
  }

  const reactionType = reactionTypeOf(emoji)

  if (reactionType) {
    realtimeClient.publish(`/app/lives/${props.liveId}/reactions`, {
      type: reactionType,
    })
  }
}

const showReactionParticle = (emoji: LiveReactionEmoji) => {
  activeReaction.value = emoji
  reactionSequence += 1

  const particleId = reactionSequence

  reactionParticles.value.push({
    id: particleId,
    emoji,
    offset: ((particleId - 1) % 3) * 18,
  })

  const particleTimer = window.setTimeout(() => {
    reactionParticles.value = reactionParticles.value.filter(
      (particle) => particle.id !== particleId,
    )
    reactionParticleTimers.delete(particleId)
  }, 950)

  reactionParticleTimers.set(particleId, particleTimer)

  if (reactionTimer !== null) {
    window.clearTimeout(reactionTimer)
  }

  reactionTimer = window.setTimeout(() => {
    activeReaction.value = null
    reactionTimer = null
  }, 420)
}

watch(
  () => [props.liveId, props.status],
  () => {
    errorMessage.value = ''
    // 방송이 바뀌면 이전 방송에서 뜬 안내는 의미가 없다.
    closeBlockedNotice()
    closeMuteNotice()
    if (muteCountdownTimer !== null) {
      window.clearInterval(muteCountdownTimer)
      muteCountdownTimer = null
    }
    muteRemainingSeconds.value = null
    void loadChatHistory()
    connectRealtime()
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  disconnectRealtime()

  if (reactionTimer !== null) {
    window.clearTimeout(reactionTimer)
  }

  if (muteCountdownTimer !== null) {
    window.clearInterval(muteCountdownTimer)
  }

  if (blockedNoticeTimer !== null) {
    window.clearTimeout(blockedNoticeTimer)
  }

  if (muteNoticeTimer !== null) {
    window.clearTimeout(muteNoticeTimer)
  }

  reactionParticleTimers.forEach((timer) => {
    window.clearTimeout(timer)
  })
  reactionParticleTimers.clear()
})

function mapChatMessage(message: BackendChatMessage, hostId: number): LiveChatMessage {
  // AI 자동답변(CHAT-002)은 특정 발신자를 지칭하지 않는 공통 안내라, 실제 사람 메시지와
  // 시각적으로 구분한다(요청 문서 032 — "판매자가 직접 답한 것"처럼 보이면 오해 소지가 있음).
  if (message.senderType === 'AI') {
    return {
      id: String(message.messageId),
      author: 'AI 채팅 도우미',
      body: message.content,
      role: 'AI',
    }
  }

  return {
    id: String(message.messageId),
    author: message.senderNickname || (message.senderType === 'SYSTEM' ? '시스템' : '사용자'),
    body: message.content,
    role: message.senderId === hostId ? 'HOST' : 'VIEWER',
  }
}

function reactionTypeOf(emoji: LiveReactionEmoji): BackendReactionType | null {
  const index = LIVE_REACTION_EMOJIS.indexOf(emoji)
  return REACTION_TYPES[index] ?? null
}

function reactionEmojiOf(type: BackendReactionType): LiveReactionEmoji | null {
  const index = REACTION_TYPES.indexOf(type)
  return LIVE_REACTION_EMOJIS[index] ?? null
}

function isBackendChatMessage(body: unknown): body is BackendChatMessage {
  return Boolean(
    body &&
    typeof body === 'object' &&
    'messageId' in body &&
    'content' in body &&
    typeof (body as BackendChatMessage).content === 'string',
  )
}

function isBackendReaction(body: unknown): body is BackendReaction {
  return Boolean(
    body &&
    typeof body === 'object' &&
    'type' in body &&
    typeof (body as BackendReaction).type === 'string',
  )
}

function isBackendViewerCount(body: unknown): body is BackendViewerCount {
  return Boolean(
    body &&
    typeof body === 'object' &&
    'viewerCount' in body &&
    typeof (body as BackendViewerCount).viewerCount === 'number',
  )
}

function isBackendChatBlockedNotice(body: unknown): body is BackendChatBlockedNotice {
  return Boolean(
    body &&
    typeof body === 'object' &&
    'clientMessageId' in body &&
    typeof (body as BackendChatBlockedNotice).clientMessageId === 'string' &&
    !('error' in body),
  )
}

function getRealtimeErrorMessage(body: unknown) {
  if (
    body &&
    typeof body === 'object' &&
    'error' in body &&
    (body as { error?: { message?: unknown } }).error?.message
  ) {
    return String((body as { error: { message: unknown } }).error.message)
  }

  return '메시지를 보내지 못했습니다.'
}

// 반응 속도 제한(L011)처럼 사용자에게 굳이 노출하지 않을 실시간 에러를 걸러낸다.
function isSuppressedRealtimeError(body: unknown) {
  if (!body || typeof body !== 'object' || !('error' in body)) return false

  const error = (body as { error?: { code?: unknown; message?: unknown } }).error
  const code = error?.code ? String(error.code) : ''
  const message = error?.message ? String(error.message) : ''

  return code === 'L011' || message.includes('반응을 너무 빠르게')
}
</script>

<template>
  <div class="live-chat-overlay" aria-label="라이브 채팅과 반응">
    <div v-show="!isChatCollapsed" class="live-chat-overlay__reactions" aria-label="라이브 반응">
      <button
        v-for="emoji in LIVE_REACTION_EMOJIS"
        :key="emoji"
        type="button"
        :class="{ 'live-chat-overlay__reaction--active': activeReaction === emoji }"
        :disabled="status !== 'LIVE'"
        :aria-label="`${emoji} 반응 보내기`"
        @click="react(emoji)"
      >
        {{ emoji }}
      </button>
    </div>

    <div
      class="live-chat-overlay__reaction-burst"
      :class="{ 'live-chat-overlay__reaction-burst--collapsed': isChatCollapsed }"
      aria-hidden="true"
    >
      <span
        v-for="particle in reactionParticles"
        :key="particle.id"
        :style="{ left: `${particle.offset}px` }"
      >
        {{ particle.emoji }}
      </span>
    </div>

    <section v-show="!isChatCollapsed" class="live-chat-overlay__panel" aria-label="라이브 채팅">
      <button
        type="button"
        class="live-chat-overlay__close"
        aria-label="채팅 창 줄이기"
        title="채팅 창 줄이기"
        @click="isChatCollapsed = true"
      >
        ×
      </button>
      <ul ref="messageList" class="live-chat-overlay__messages" aria-live="polite">
        <li v-for="message in messages" :key="message.id">
          <!-- 아이디는 누구든 같은 서체·크기·굵기·색으로 그린다(판매자·AI 강조 없음).
               AI 자동답변은 작성자 이름이 'AI 채팅 도우미'라 이름 자체로 구분된다. -->
          <span class="live-chat-overlay__author">{{ message.author }}</span>
          <span class="live-chat-overlay__message">{{ message.body }}</span>
        </li>
      </ul>

      <AppInlineNotice v-if="errorMessage" class="live-chat-overlay__notice" variant="info">
        {{ errorMessage }}
      </AppInlineNotice>

      <form class="live-chat-overlay__composer" @submit.prevent="submitMessage">
        <input
          v-model="draft"
          type="text"
          maxlength="200"
          :disabled="status !== 'LIVE' || (REALTIME_ENABLED && !canPublishRealtime) || isMuted"
          :placeholder="composerPlaceholder"
          aria-label="채팅 메시지"
        />
        <button type="submit" :disabled="!canSubmitMessage" aria-label="채팅 보내기">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="m22 2-7 20-4-9-9-4 20-7Z" />
            <path d="M22 2 11 13" />
          </svg>
        </button>
      </form>
    </section>

    <div v-show="isChatCollapsed" class="live-chat-overlay__collapsed" aria-label="라이브 반응">
      <button
        v-for="emoji in LIVE_REACTION_EMOJIS"
        :key="`collapsed-${emoji}`"
        type="button"
        :class="{ 'live-chat-overlay__reaction--active': activeReaction === emoji }"
        :disabled="status !== 'LIVE'"
        :aria-label="`${emoji} 반응 보내기`"
        @click="react(emoji)"
      >
        {{ emoji }}
      </button>
      <button
        type="button"
        class="live-chat-overlay__reopen"
        aria-label="채팅 창 다시 열기"
        @click="isChatCollapsed = false"
      >
        채팅
      </button>
    </div>

    <!-- 차단·음소거처럼 "지금 내 채팅이 막혔다"를 알리는 안내만 화면 한가운데 모아 쌓는다.
         연결·전송 오류는 채팅창 안 배너로 남긴다(자주 뜨는 상태 안내라 화면을 가리면 거슬린다).
         뒤를 덮는 배경막은 두지 않는다 — 안내가 떠 있어도 라이브는 계속 볼 수 있어야 한다. -->
    <div v-if="isBlockedNoticeOpen || isMuteNoticeOpen" class="live-chat-overlay__notices">
      <!-- 차단: 15초 뒤 스스로 사라지고, 그 전에 X로도 닫을 수 있다. -->
      <div
        v-if="isBlockedNoticeOpen"
        class="live-chat-overlay__notice-card live-chat-overlay__notice-card--error"
        role="alertdialog"
        aria-labelledby="live-chat-blocked-title"
      >
        <button
          type="button"
          class="live-chat-overlay__notice-close"
          aria-label="차단 안내 닫기"
          title="차단 안내 닫기"
          @click="closeBlockedNotice"
        >
          ×
        </button>
        <strong id="live-chat-blocked-title">메시지가 차단되었습니다.</strong>
        <p>부적절한 표현으로 판단되어 전송되지 않았습니다.</p>
      </div>

      <!-- 음소거: 안내는 15초 뒤(또는 X로) 사라지지만 채팅 잠금은 서버가 준 시간만큼 그대로다. -->
      <div
        v-if="isMuteNoticeOpen"
        class="live-chat-overlay__notice-card live-chat-overlay__notice-card--error"
        role="alert"
      >
        <button
          type="button"
          class="live-chat-overlay__notice-close"
          aria-label="채팅 제한 안내 닫기"
          title="채팅 제한 안내 닫기"
          @click="closeMuteNotice"
        >
          ×
        </button>
        <strong>{{ muteRemainingSeconds }}초간 채팅이 제한됩니다</strong>
        <p>도배·욕설이 반복돼 잠시 채팅을 보낼 수 없습니다.</p>
      </div>

    </div>
  </div>
</template>

<style scoped lang="scss">
.live-chat-overlay {
  position: absolute;
  z-index: var(--z-layer-1);
  inset: 0;
  pointer-events: none;
}

.live-chat-overlay__close {
  display: grid;
  position: absolute;
  z-index: var(--z-layer-2);
  top: 8px;
  right: 8px;
  width: var(--badge-height-lg);
  height: var(--badge-height-lg);
  border: 0;
  border-radius: 50%;
  background: rgba(8, 8, 8, 0.7);
  color: var(--color-live-text-primary);
  font-size: var(--font-size-lg);
  line-height: 1;
  pointer-events: auto;
  place-items: center;
  backdrop-filter: blur(8px);
}

/* 채팅 창을 줄인 상태: 감정 이모지와 다시 열기 버튼을 가로로 배치한다. */
.live-chat-overlay__collapsed {
  display: flex;
  position: absolute;
  bottom: 12px;
  left: 20px;
  align-items: center;
  gap: var(--space-2);
  pointer-events: auto;
}

.live-chat-overlay__collapsed button:not(.live-chat-overlay__reopen) {
  width: 24px;
  height: var(--badge-height-sm);
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--color-live-text-primary);
  font-size: var(--font-size-lg);
  line-height: var(--line-height-lg);
}

.live-chat-overlay__collapsed button:not(.live-chat-overlay__reopen):disabled {
  cursor: not-allowed;
  opacity: 0.38;
}

.live-chat-overlay__reopen {
  min-height: var(--badge-height-lg);
  margin-left: var(--space-1);
  padding: 0 12px;
  border: 1px solid var(--color-live-border);
  border-radius: var(--radius-badge);
  background: rgba(8, 8, 8, 0.7);
  color: var(--color-live-text-primary);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-medium);
  backdrop-filter: blur(8px);
}

.live-chat-overlay__close:focus-visible,
.live-chat-overlay__reopen:focus-visible,
.live-chat-overlay__collapsed button:focus-visible {
  outline: 2px solid var(--color-primary-strong);
  outline-offset: 2px;
}

.live-chat-overlay__reactions {
  display: flex;
  position: absolute;
  bottom: 12px;
  left: 432px;
  flex-direction: column;
  gap: var(--space-2);
  pointer-events: auto;
}

.live-chat-overlay__reactions button {
  width: 24px;
  height: var(--badge-height-sm);
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--color-live-text-primary);
  font-size: var(--font-size-lg);
  line-height: var(--line-height-lg);
  transition:
    background-color 150ms ease,
    opacity 150ms ease,
    transform 150ms ease;
}

.live-chat-overlay__reactions button:hover:not(:disabled) {
  transform: scale(1.16);
}

.live-chat-overlay__reaction--active {
  border-radius: var(--radius-badge);
  background: rgba(242, 240, 237, 0.14) !important;
  transform: scale(0.84) !important;
}

.live-chat-overlay__reactions button:disabled {
  cursor: not-allowed;
  opacity: 0.38;
}

.live-chat-overlay__reactions button:focus-visible,
.live-chat-overlay__composer button:focus-visible,
.live-chat-overlay__composer input:focus-visible {
  outline: 2px solid var(--color-primary-strong);
  outline-offset: 2px;
}

.live-chat-overlay__reaction-burst {
  position: absolute;
  bottom: 12px;
  left: 432px;
  width: 76px;
  height: 156px;
  pointer-events: none;
}

/* 채팅 꺼짐: 가로 반응 바(좌하단)에서 버스트가 올라오도록 위치를 맞춘다 */
.live-chat-overlay__reaction-burst--collapsed {
  left: 20px;
}

.live-chat-overlay__reaction-burst span {
  position: absolute;
  bottom: 0;
  font-size: var(--font-size-2xl);
  line-height: 28px;
  opacity: 0;
  filter: drop-shadow(0 5px 7px rgba(0, 0, 0, 0.45));
  animation: live-reaction-float 900ms ease-out forwards;
  will-change: opacity, transform;
}

/* 채팅은 라이브에서 가장 자주 읽는 영역이라 창·글씨를 키워 잡았다. 폭을 바꾸면 아래
   `__reactions`·`__reaction-burst`의 left(= 20 + 폭 + 12)도 같이 맞춰야 이모지 열이
   패널 오른쪽에 붙는다. */
.live-chat-overlay__panel {
  position: absolute;
  bottom: 12px;
  left: 20px;
  width: 400px;
  padding: 16px;
  border: 1px solid var(--overlay-hairline);
  border-radius: var(--radius-control);
  background: rgba(8, 8, 8, 0.68);
  backdrop-filter: blur(12px);
  pointer-events: auto;
}

.live-chat-overlay__messages {
  height: 220px;
  margin: 0 0 var(--space-2);
  overflow-y: auto;
  padding: 0 6px 0 0;
  list-style: none;
  scrollbar-color: var(--overlay-scrollbar) transparent;
  scrollbar-width: thin;
}

.live-chat-overlay__messages::-webkit-scrollbar {
  width: 4px;
}

.live-chat-overlay__messages::-webkit-scrollbar-thumb {
  background: var(--overlay-scrollbar);
}

.live-chat-overlay__messages li {
  display: flex;
  align-items: baseline;
  gap: 9px;
}

.live-chat-overlay__messages li + li {
  margin-top: 9px;
}

/* 아이디는 본문과 같은 서체를 쓰고, 누구의 아이디든 완전히 같게 그린다 — 모노
   (IBM Plex Mono)에는 한글 글리프가 없어 한글 닉네임이 대체 폰트로 떨어지며 본문과
   서체가 달라 보였다. 자간·대문자 변환도 한글에는 효과가 없어 함께 걷어냈다. */
.live-chat-overlay__author {
  flex: 0 0 auto;
  color: var(--color-live-text-secondary);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-bold);
  line-height: 1.5;
}

.live-chat-overlay__message {
  color: #d8d4d0;
  font-size: var(--font-size-body);
  font-weight: var(--font-weight-regular);
  line-height: 1.5;
  overflow-wrap: anywhere;
}

/* 연결·전송 오류 안내는 채팅창 안에 그대로 둔다(공용 AppInlineNotice 규격). */
.live-chat-overlay__notice {
  margin: 0 0 6px;
  font-variant-numeric: tabular-nums;
}

/* 차단·음소거 안내는 영상 영역이 아니라 뷰포트 정중앙에 띄운다 — 채팅창을 접어둬도, 화면 어디를
   보고 있어도 눈에 걸려야 하는 안내다. 오버레이 루트가 pointer-events:none이라 카드에서
   다시 켠다(컨테이너는 꺼둔 채로 둬서 카드 사이 빈 공간은 영상 클릭을 막지 않는다). */
.live-chat-overlay__notices {
  display: grid;
  position: fixed;
  z-index: var(--z-top);
  top: 50%;
  left: 50%;
  width: min(360px, calc(100vw - 32px));
  gap: var(--space-2);
  pointer-events: none;
  transform: translate(-50%, -50%);
}

.live-chat-overlay__notice-card {
  display: grid;
  position: relative;
  padding: 20px 44px 20px 22px;
  border: 1px solid var(--color-live-border);
  border-radius: var(--radius-card);
  background: var(--overlay-scrim-strong);
  gap: 6px;
  pointer-events: auto;
  backdrop-filter: blur(12px);
}

.live-chat-overlay__notice-card strong {
  color: var(--color-live-text-primary);
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-comfortable);
  font-variant-numeric: tabular-nums;
}

.live-chat-overlay__notice-card p {
  color: var(--color-live-text-secondary);
  font-size: var(--font-size-caption);
  line-height: var(--line-height-snug);
}

.live-chat-overlay__notice-card--error {
  border-color: var(--color-error);
}

.live-chat-overlay__notice-card--error strong {
  color: var(--color-error);
}

.live-chat-overlay__notice-close {
  display: grid;
  position: absolute;
  top: 10px;
  right: 10px;
  width: var(--badge-height-lg);
  height: var(--badge-height-lg);
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: var(--color-live-text-primary);
  font-size: var(--font-size-lg);
  line-height: 1;
  place-items: center;
}

.live-chat-overlay__notice-close:hover {
  background: rgba(242, 240, 237, 0.12);
}

.live-chat-overlay__notice-close:focus-visible {
  outline: 2px solid var(--color-primary-strong);
  outline-offset: 2px;
}

.live-chat-overlay__composer {
  display: flex;
  width: 100%;
  box-sizing: border-box;
  align-items: center;
  padding: 4px 0 0;
  border-top: 1px solid var(--overlay-hairline);
  gap: 6px;
}

.live-chat-overlay__composer input {
  min-width: 0;
  padding: 9px 0;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--color-live-text-primary);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-regular);
  line-height: var(--line-height-snug);
  flex: 1;
}

.live-chat-overlay__composer input::placeholder {
  color: var(--color-live-text-secondary);
}

.live-chat-overlay__composer button {
  display: grid;
  flex: 0 0 auto;
  width: 26px;
  height: var(--badge-height-sm);
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--color-live-text-primary);
  place-items: center;
}

.live-chat-overlay__composer button:disabled {
  cursor: not-allowed;
  color: var(--color-live-text-secondary);
  opacity: 0.5;
}

.live-chat-overlay__composer svg {
  width: var(--icon-size-xs);
  height: var(--icon-size-xs);
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.8;
}

@media (max-width: 720px) {
  .live-chat-overlay__reactions {
    top: 12px;
    bottom: auto;
    left: 15px;
    flex-direction: row;
  }

  .live-chat-overlay__panel {
    width: min(340px, calc(100% - 88px));
  }

  .live-chat-overlay__messages {
    height: 180px;
  }

  .live-chat-overlay__reaction-burst {
    top: 45px;
    bottom: auto;
    left: 15px;
    width: 180px;
    height: var(--button-height-tight);
  }

  .live-chat-overlay__reaction-burst span {
    top: 0;
    bottom: auto;
    animation-name: live-reaction-float-side;
  }

  .live-chat-overlay__composer {
    width: 100%;
  }
}

@keyframes live-reaction-float {
  0% {
    opacity: 0;
    transform: translateY(8px) scale(0.7) rotate(-8deg);
  }

  18% {
    opacity: 1;
    transform: translateY(0) scale(1.08) rotate(4deg);
  }

  100% {
    opacity: 0;
    transform: translateY(-132px) scale(1.34) rotate(12deg);
  }
}

@keyframes live-reaction-float-side {
  0% {
    opacity: 0;
    transform: translate(0, 4px) scale(0.7);
  }

  18% {
    opacity: 1;
    transform: translate(8px, 0) scale(1.05);
  }

  100% {
    opacity: 0;
    transform: translate(128px, -6px) scale(1.2);
  }
}

@media (prefers-reduced-motion: reduce) {
  .live-chat-overlay__reactions button {
    transition: none;
  }

  .live-chat-overlay__reaction-burst span {
    animation-duration: 1ms;
  }
}
</style>
