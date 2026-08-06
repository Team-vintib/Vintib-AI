<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'

import {
  type BackendChatMessage,
  type BackendReaction,
  type BackendReactionType,
  type BackendViewerCount,
  getLiveChatMessages,
} from '@/domains/chat/api/liveChatApi'
import { LIVE_REACTION_EMOJIS } from '@/domains/chat/constants/liveChatMockData'
import { useAuthStore } from '@/domains/auth/stores/authStore'
import {
  isLiveRealtimeApiEnabled,
  LiveRealtimeClient,
} from '@/domains/live/api/liveRealtimeClient'

import type {
  LiveChatMessage,
  LiveReactionEmoji,
} from '@/domains/chat/types/liveChat.types'
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
let realtimeClient: LiveRealtimeClient | null = null
let mockMessageSequence = 0
let reactionSequence = 0
let reactionTimer: number | null = null
const reactionParticleTimers = new Map<number, number>()

const canPublishRealtime = computed(
  () => REALTIME_ENABLED && isConnected.value && isAuthenticated.value,
)

const composerPlaceholder = computed(() => {
  if (props.status !== 'LIVE') return '방송 중에만 채팅할 수 있습니다'
  if (REALTIME_ENABLED && !isAuthenticated.value) return '로그인 후 채팅할 수 있습니다'
  if (REALTIME_ENABLED && !isConnected.value) return '채팅 연결 중...'
  return '채팅...'
})

const canSubmitMessage = computed(
  () => props.status === 'LIVE' && draft.value.trim().length > 0 && canPublishRealtime.value,
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

  if (!body || props.status !== 'LIVE') return

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

  reactionParticleTimers.forEach((timer) => {
    window.clearTimeout(timer)
  })
  reactionParticleTimers.clear()
})

function mapChatMessage(message: BackendChatMessage, hostId: number): LiveChatMessage {
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
</script>

<template>
  <div class="live-chat-overlay" aria-label="라이브 채팅과 반응">
    <div class="live-chat-overlay__reactions" aria-label="라이브 반응">
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

    <div class="live-chat-overlay__reaction-burst" aria-hidden="true">
      <span
        v-for="particle in reactionParticles"
        :key="particle.id"
        :style="{ left: `${particle.offset}px` }"
      >
        {{ particle.emoji }}
      </span>
    </div>

    <section class="live-chat-overlay__panel" aria-label="라이브 채팅">
      <ul ref="messageList" class="live-chat-overlay__messages" aria-live="polite">
        <li v-for="message in messages" :key="message.id">
          <span
            class="live-chat-overlay__author"
            :class="{ 'live-chat-overlay__author--host': message.role === 'HOST' }"
          >
            {{ message.author }}
          </span>
          <span class="live-chat-overlay__message">{{ message.body }}</span>
        </li>
      </ul>

      <p v-if="errorMessage" class="live-chat-overlay__error" role="status">
        {{ errorMessage }}
      </p>

      <form class="live-chat-overlay__composer" @submit.prevent="submitMessage">
        <input
          v-model="draft"
          type="text"
          maxlength="200"
          :disabled="status !== 'LIVE' || (REALTIME_ENABLED && !canPublishRealtime)"
          :placeholder="composerPlaceholder"
          aria-label="채팅 메시지"
        />
        <button
          type="submit"
          :disabled="!canSubmitMessage"
          aria-label="채팅 보내기"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="m22 2-7 20-4-9-9-4 20-7Z" />
            <path d="M22 2 11 13" />
          </svg>
        </button>
      </form>
    </section>
  </div>
</template>

<style scoped lang="scss">
.live-chat-overlay {
  position: absolute;
  z-index: var(--z-layer-1);
  inset: 0;
  pointer-events: none;
}

.live-chat-overlay__reactions {
  display: flex;
  position: absolute;
  bottom: 20px;
  left: 372px;
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
  bottom: 20px;
  left: 372px;
  width: 76px;
  height: 156px;
  pointer-events: none;
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

.live-chat-overlay__panel {
  position: absolute;
  bottom: 20px;
  left: 20px;
  width: 340px;
  padding: 14px;
  border: 1px solid var(--overlay-hairline);
  border-radius: var(--radius-control);
  background: rgba(8, 8, 8, 0.68);
  backdrop-filter: blur(12px);
  pointer-events: auto;
}

.live-chat-overlay__messages {
  height: 168px;
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

.live-chat-overlay__author {
  flex: 0 0 auto;
  color: var(--color-live-text-secondary);
  font-family: var(--font-mono);
  font-size: var(--font-size-badge);
  font-weight: var(--font-weight-medium);
  letter-spacing: 0.06em;
  line-height: 1.5;
  text-transform: uppercase;
}

.live-chat-overlay__author--host {
  color: var(--color-live-text-primary);
}

.live-chat-overlay__message {
  color: #d8d4d0;
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-light);
  line-height: 1.5;
  overflow-wrap: anywhere;
}

.live-chat-overlay__error {
  margin: 0 0 6px;
  color: var(--color-accent);
  font-size: var(--font-size-2xs);
  line-height: var(--line-height-tight);
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
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-light);
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
    width: min(288px, calc(100% - 96px));
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
