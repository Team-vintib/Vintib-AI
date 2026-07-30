<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref } from 'vue'

import {
  LIVE_CHAT_MOCK_MESSAGES,
  LIVE_REACTION_EMOJIS,
} from '@/domains/chat/constants/liveChatMockData'

import type {
  LiveChatMessage,
  LiveReactionEmoji,
} from '@/domains/chat/types/liveChat.types'
import type { LiveWatchStatus } from '@/domains/live/types/liveWatch.types'

const props = defineProps<{
  status: LiveWatchStatus
}>()

const messages = ref<LiveChatMessage[]>([...LIVE_CHAT_MOCK_MESSAGES])
const draft = ref('')
const activeReaction = ref<LiveReactionEmoji | null>(null)
const messageList = ref<HTMLElement | null>(null)
let mockMessageSequence = 0
let reactionTimer: number | null = null

const scrollToLatestMessage = async () => {
  await nextTick()

  if (messageList.value) {
    messageList.value.scrollTop = messageList.value.scrollHeight
  }
}

const submitMessage = () => {
  const body = draft.value.trim()

  if (!body || props.status !== 'LIVE') return

  mockMessageSequence += 1
  messages.value.push({
    id: `local-chat-${mockMessageSequence}`,
    author: '나',
    body,
    role: 'VIEWER',
  })
  draft.value = ''
  void scrollToLatestMessage()
}

const react = (emoji: LiveReactionEmoji) => {
  if (props.status !== 'LIVE') return

  activeReaction.value = emoji

  if (reactionTimer !== null) {
    window.clearTimeout(reactionTimer)
  }

  reactionTimer = window.setTimeout(() => {
    activeReaction.value = null
    reactionTimer = null
  }, 420)
}

onBeforeUnmount(() => {
  if (reactionTimer !== null) {
    window.clearTimeout(reactionTimer)
  }
})
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

      <form class="live-chat-overlay__composer" @submit.prevent="submitMessage">
        <input
          v-model="draft"
          type="text"
          maxlength="200"
          :disabled="status !== 'LIVE'"
          :placeholder="status === 'LIVE' ? '채팅...' : '방송 중에만 채팅할 수 있습니다'"
          aria-label="채팅 메시지"
        />
        <button
          type="submit"
          :disabled="status !== 'LIVE' || draft.trim().length === 0"
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
  z-index: 1;
  inset: 0;
  pointer-events: none;
}

.live-chat-overlay__reactions {
  display: flex;
  position: absolute;
  top: 50%;
  left: 12px;
  flex-direction: column;
  gap: var(--space-2);
  pointer-events: auto;
  transform: translateY(-50%);
}

.live-chat-overlay__reactions button {
  width: 24px;
  height: 26px;
  padding: 0;
  border: 0;
  background: transparent;
  color: #fff;
  font-size: 18px;
  line-height: 26px;
  transition:
    opacity 150ms ease,
    transform 150ms ease;
}

.live-chat-overlay__reactions button:hover:not(:disabled),
.live-chat-overlay__reaction--active {
  transform: scale(1.16);
}

.live-chat-overlay__reactions button:disabled {
  cursor: not-allowed;
  opacity: 0.38;
}

.live-chat-overlay__reactions button:focus-visible,
.live-chat-overlay__composer button:focus-visible,
.live-chat-overlay__composer input:focus-visible {
  outline: 2px solid #fff;
  outline-offset: 2px;
}

.live-chat-overlay__panel {
  position: absolute;
  bottom: 15px;
  left: 15px;
  width: 288px;
  pointer-events: auto;
}

.live-chat-overlay__messages {
  height: 160px;
  margin: 0 0 var(--space-2);
  overflow-y: auto;
  padding: 0 6px 0 0;
  list-style: none;
  scrollbar-color: rgba(255, 255, 255, 0.38) transparent;
  scrollbar-width: thin;
}

.live-chat-overlay__messages::-webkit-scrollbar {
  width: 4px;
}

.live-chat-overlay__messages::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.38);
}

.live-chat-overlay__messages li {
  display: flex;
  align-items: flex-end;
  gap: 6px;
}

.live-chat-overlay__messages li + li {
  margin-top: 6px;
}

.live-chat-overlay__author {
  flex: 0 0 auto;
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(32, 37, 34, 0.8);
  color: var(--color-live-text-secondary);
  font-size: 9px;
  font-weight: 700;
  line-height: 14px;
}

.live-chat-overlay__author--host {
  background: rgba(31, 89, 62, 0.82);
  color: #a9d4b8;
}

.live-chat-overlay__message {
  padding: 6px 10px;
  border-radius: 13px;
  background: rgba(32, 37, 34, 0.75);
  color: var(--color-live-text-primary);
  font-size: 11px;
  line-height: 15px;
  overflow-wrap: anywhere;
}

.live-chat-overlay__composer {
  display: flex;
  width: 288px;
  height: 36px;
  box-sizing: border-box;
  align-items: center;
  padding: 4px 5px 4px var(--space-2);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: var(--radius-control);
  background: rgba(14, 17, 16, 0.78);
  gap: 6px;
  backdrop-filter: blur(8px);
}

.live-chat-overlay__composer input {
  min-width: 0;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--color-live-text-primary);
  font-size: 12px;
  line-height: 18px;
  flex: 1;
}

.live-chat-overlay__composer input::placeholder {
  color: var(--color-live-text-secondary);
}

.live-chat-overlay__composer button {
  display: grid;
  flex: 0 0 auto;
  width: 26px;
  height: 26px;
  padding: 0;
  border: 0;
  border-radius: var(--radius-control);
  background: transparent;
  color: #7db892;
  place-items: center;
}

.live-chat-overlay__composer button:disabled {
  cursor: not-allowed;
  color: var(--color-live-text-secondary);
  opacity: 0.5;
}

.live-chat-overlay__composer svg {
  width: 15px;
  height: 15px;
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.8;
}

@media (max-width: 720px) {
  .live-chat-overlay__panel {
    width: min(288px, calc(100% - 96px));
  }

  .live-chat-overlay__composer {
    width: 100%;
  }
}

@media (prefers-reduced-motion: reduce) {
  .live-chat-overlay__reactions button {
    transition: none;
  }
}
</style>
