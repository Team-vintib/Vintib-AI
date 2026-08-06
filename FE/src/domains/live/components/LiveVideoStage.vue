<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { connectLiveVideo, type LiveVideoSession } from '@/domains/live/api/liveVideoRoom'

import type { LiveWatchStatus } from '@/domains/live/types/liveWatch.types'

const props = withDefaults(
  defineProps<{
    title: string
    posterUrl: string | null
    status: LiveWatchStatus
    liveId?: number | null
    tryOnDisabled?: boolean
    tryOnOpen?: boolean
    showTryOn?: boolean
    connectionLabel?: string
    showReminder?: boolean
    reminderActive?: boolean
  }>(),
  {
    liveId: null,
    tryOnDisabled: false,
    tryOnOpen: false,
    showTryOn: true,
    connectionLabel: '',
    showReminder: false,
    reminderActive: false,
  },
)

const emit = defineEmits<{
  openTryOn: []
  toggleReminder: []
}>()

const videoEl = ref<HTMLVideoElement | null>(null)
const videoState = ref<'idle' | 'connecting' | 'connected' | 'failed'>('idle')
let session: LiveVideoSession | null = null
let connectSeq = 0

const isStreaming = computed(() => videoState.value === 'connected')

const startVideo = async () => {
  if (
    props.status !== 'LIVE' ||
    !props.liveId ||
    !videoEl.value ||
    session ||
    videoState.value === 'connecting'
  ) {
    return
  }

  const seq = ++connectSeq
  videoState.value = 'connecting'

  try {
    const nextSession = await connectLiveVideo(props.liveId, videoEl.value, () => {
      if (session === nextSession) {
        session = null
        videoState.value = 'idle'
      }
    })

    // 연결하는 사이 status가 바뀌었으면(예: 종료) 방금 붙은 세션을 즉시 정리한다.
    if (seq !== connectSeq) {
      void nextSession.disconnect()
      return
    }

    session = nextSession
    videoState.value = 'connected'
  } catch {
    if (seq === connectSeq) {
      videoState.value = 'failed'
    }
  }
}

const stopVideo = async () => {
  connectSeq += 1
  const current = session
  session = null
  videoState.value = 'idle'

  if (current) {
    await current.disconnect()
  }
}

watch(
  () => props.status,
  (status) => {
    if (status === 'LIVE') {
      void startVideo()
    } else {
      void stopVideo()
    }
  },
)

onMounted(() => {
  if (props.status === 'LIVE') {
    void startVideo()
  }
})

onBeforeUnmount(() => {
  void stopVideo()
})

const stageMessage = computed(() => {
  if (props.status === 'LIVE') {
    if (videoState.value === 'connecting') return '영상 연결 중'
    if (videoState.value === 'failed') return '영상을 불러오지 못했습니다'
    if (videoState.value !== 'connected' && props.connectionLabel) return props.connectionLabel
    return ''
  }

  if (props.status === 'SCHEDULED') return '방송 시작 전입니다'
  if (props.status === 'ENDED') return '종료된 라이브입니다'
  if (props.status === 'CANCELED') return '취소된 라이브입니다'
  return '스트리밍 연결 전 미리보기'
})
</script>

<template>
  <section class="live-video-stage" aria-label="라이브 영상 영역">
    <video
      v-show="isStreaming"
      ref="videoEl"
      class="live-video-stage__media"
      autoplay
      playsinline
    ></video>
    <img
      v-if="posterUrl"
      v-show="!isStreaming"
      :src="posterUrl"
      :alt="`${title} 방송 미리보기`"
    />
    <div v-else v-show="!isStreaming" class="live-video-stage__fallback" aria-hidden="true">
      <svg viewBox="0 0 24 24">
        <path d="m15 10 5-3v10l-5-3v-4Z" />
        <rect x="3" y="5" width="12" height="14" rx="2" />
      </svg>
    </div>

    <div class="live-video-stage__shade" aria-hidden="true"></div>
    <div class="live-video-stage__overlay">
      <slot name="overlay"></slot>
    </div>

    <div v-if="stageMessage" class="live-video-stage__notice" role="status">
      <span aria-hidden="true"></span>
      {{ stageMessage }}
    </div>

    <button
      v-if="showReminder"
      class="live-video-stage__reminder"
      :class="{ 'live-video-stage__reminder--active': reminderActive }"
      type="button"
      :aria-pressed="reminderActive"
      @click="emit('toggleReminder')"
    >
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
        <path d="M10.3 21a2 2 0 0 0 3.4 0" />
      </svg>
      {{ reminderActive ? '알림 받는 중' : '시작 알림 받기' }}
    </button>

    <div class="live-video-stage__controls" aria-hidden="true">
      <span>
        <svg viewBox="0 0 24 24">
          <path d="M11 5 6 9H3v6h3l5 4V5ZM15 9a4 4 0 0 1 0 6M18 6a8 8 0 0 1 0 12" />
        </svg>
      </span>
      <span>
        <svg viewBox="0 0 24 24">
          <path d="M8 3H5a2 2 0 0 0-2 2v3M16 3h3a2 2 0 0 1 2 2v3M8 21H5a2 2 0 0 1-2-2v-3M16 21h3a2 2 0 0 0 2-2v-3" />
        </svg>
      </span>
    </div>

    <button
      v-if="showTryOn && !tryOnOpen"
      class="live-video-stage__try-on"
      type="button"
      :disabled="tryOnDisabled"
      aria-label="선택한 상품 AI 시착"
      :title="
        tryOnDisabled
          ? '라이브 중 선택한 상품이 있을 때 AI 시착을 이용할 수 있습니다.'
          : '선택한 상품 AI 시착 열기'
      "
      @click="emit('openTryOn')"
    >
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="m12 3 1.35 4.15L17.5 8.5l-4.15 1.35L12 14l-1.35-4.15L6.5 8.5l4.15-1.35L12 3Z" />
        <path d="m18.5 14 0.8 2.2 2.2 0.8-2.2 0.8-0.8 2.2-0.8-2.2-2.2-0.8 2.2-0.8 0.8-2.2Z" />
      </svg>
      AI 시착
    </button>
  </section>
</template>

<style scoped lang="scss">
.live-video-stage {
  display: grid;
  position: relative;
  min-width: 0;
  min-height: 420px;
  overflow: hidden;
  background: #080a09;
  isolation: isolate;
  place-items: center;
}

.live-video-stage > img,
.live-video-stage__fallback,
.live-video-stage__media {
  position: absolute;
  z-index: -3;
  inset: 0;
  width: 100%;
  height: 100%;
}

.live-video-stage > img,
.live-video-stage__media {
  object-fit: cover;
}

.live-video-stage__fallback {
  display: grid;
  background:
    radial-gradient(circle at 50% 30%, rgba(255, 255, 255, 0.08), transparent 40%),
    var(--color-live-background);
  color: var(--color-live-text-secondary);
  place-items: center;
}

.live-video-stage__fallback svg {
  width: 48px;
  height: var(--button-height-standard);
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.4;
}

.live-video-stage__shade {
  position: absolute;
  z-index: -2;
  inset: 0;
  background:
    linear-gradient(180deg, rgba(0, 0, 0, 0.08) 45%, rgba(0, 0, 0, 0.74) 100%),
    linear-gradient(90deg, rgba(0, 0, 0, 0.18), transparent 30%);
}

.live-video-stage__overlay {
  position: absolute;
  z-index: var(--z-layer-1);
  inset: 0;
  pointer-events: none;
}

.live-video-stage__notice {
  display: inline-flex;
  position: absolute;
  top: var(--space-4);
  right: var(--space-4);
  align-items: center;
  min-height: var(--badge-height-md);
  padding: 0 12px;
  border: 1px solid rgba(242, 240, 237, 0.12);
  border-radius: var(--radius-badge);
  background: rgba(8, 8, 8, 0.7);
  gap: 6px;
  color: var(--color-live-text-secondary);
  font-family: var(--font-mono);
  font-size: var(--font-size-badge);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  backdrop-filter: blur(8px);
}

.live-video-stage__notice span {
  width: var(--space-1);
  height: var(--space-1);
  background: var(--color-accent);
  animation: vtPulse var(--duration-pulse) ease-in-out infinite;
}

.live-video-stage__reminder {
  display: inline-flex;
  position: relative;
  z-index: var(--z-layer-2);
  align-items: center;
  min-height: var(--button-height-compact);
  padding: 0 var(--space-5);
  border: 1px solid var(--color-accent);
  border-radius: var(--radius-control);
  background: var(--overlay-scrim-medium);
  gap: var(--space-2);
  color: var(--color-accent);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-medium);
  backdrop-filter: blur(6px);
}

.live-video-stage__reminder--active {
  background: var(--color-accent);
  color: var(--color-primary-strong);
}

.live-video-stage__reminder svg {
  width: var(--icon-size-sm);
  height: var(--icon-size-sm);
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.7;
}

.live-video-stage__reminder:focus-visible {
  outline: 1px solid var(--color-primary-strong);
  outline-offset: 2px;
}

.live-video-stage__controls {
  display: flex;
  position: absolute;
  top: var(--space-4);
  right: var(--space-4);
  align-items: center;
  gap: var(--space-2);
  color: rgba(255, 255, 255, 0.88);
  z-index: var(--z-layer-2);
}

.live-video-stage__controls > span {
  display: grid;
  width: 30px;
  height: var(--badge-height-lg);
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.5);
  place-items: center;
}

.live-video-stage__controls svg {
  width: 17px;
  height: 17px;
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.8;
}

.live-video-stage__try-on {
  display: inline-flex;
  position: absolute;
  z-index: var(--z-layer-2);
  right: var(--space-4);
  bottom: var(--space-4);
  min-height: var(--button-height-compact);
  width: 108px;
  align-items: center;
  justify-content: center;
  padding: 0;
  border: 1px solid var(--color-accent);
  border-radius: var(--radius-control);
  background: var(--overlay-scrim-medium);
  gap: var(--space-2);
  color: var(--color-accent);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-medium);
  backdrop-filter: blur(6px);
  transition:
    background-color var(--transition-base),
    color var(--transition-base);
}

.live-video-stage__try-on:hover:not(:disabled) {
  background: var(--color-accent);
  color: var(--color-primary-strong);
}

.live-video-stage__try-on:disabled {
  cursor: not-allowed;
  border-color: var(--color-border-input);
  background: var(--overlay-scrim-medium);
  color: var(--color-live-text-secondary);
  opacity: 0.72;
}

.live-video-stage__try-on:focus-visible {
  outline: 1px solid var(--color-primary-strong);
  outline-offset: 2px;
}

.live-video-stage__try-on svg {
  width: var(--icon-size-sm);
  height: var(--icon-size-sm);
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.6;
}

@media (max-width: 960px) {
  .live-video-stage {
    min-height: 380px;
  }
}

@media (max-width: 720px) {
  .live-video-stage {
    min-height: var(--surface-min-height-lg);
  }
}
</style>
