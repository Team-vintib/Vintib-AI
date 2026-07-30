<script setup lang="ts">
import { computed } from 'vue'

import type { LiveWatchStatus } from '@/domains/live/types/liveWatch.types'

const props = defineProps<{
  title: string
  posterUrl: string | null
  status: LiveWatchStatus
}>()

const stageMessage = computed(() => {
  if (props.status === 'SCHEDULED') return '방송 시작 전입니다'
  if (props.status === 'ENDED') return '종료된 라이브입니다'
  if (props.status === 'CANCELED') return '취소된 라이브입니다'
  return '스트리밍 연결 전 미리보기'
})
</script>

<template>
  <section class="live-video-stage" aria-label="라이브 영상 영역">
    <img v-if="posterUrl" :src="posterUrl" :alt="`${title} 방송 미리보기`" />
    <div v-else class="live-video-stage__fallback" aria-hidden="true">
      <svg viewBox="0 0 24 24">
        <path d="m15 10 5-3v10l-5-3v-4Z" />
        <rect x="3" y="5" width="12" height="14" rx="2" />
      </svg>
    </div>

    <div class="live-video-stage__shade" aria-hidden="true"></div>
    <div class="live-video-stage__overlay">
      <slot name="overlay"></slot>
    </div>

    <div v-if="status !== 'LIVE'" class="live-video-stage__notice" role="status">
      <span aria-hidden="true"></span>
      {{ stageMessage }}
    </div>

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
      class="live-video-stage__try-on"
      type="button"
      aria-label="선택한 상품 AI 시착"
      title="AI 시착 상세 기능은 후속 작업에서 연결됩니다."
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
.live-video-stage__fallback {
  position: absolute;
  z-index: -3;
  inset: 0;
  width: 100%;
  height: 100%;
}

.live-video-stage > img {
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
  height: 48px;
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
  z-index: 1;
  inset: 0;
  pointer-events: none;
}

.live-video-stage__notice {
  display: inline-flex;
  position: absolute;
  top: var(--space-4);
  right: var(--space-4);
  align-items: center;
  min-height: 28px;
  padding: 0 10px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: var(--radius-chip);
  background: rgba(10, 12, 11, 0.68);
  gap: 6px;
  color: rgba(255, 255, 255, 0.76);
  font-size: 10px;
  backdrop-filter: blur(8px);
}

.live-video-stage__notice span {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--color-live);
}

.live-video-stage__controls {
  display: flex;
  position: absolute;
  top: var(--space-4);
  right: var(--space-4);
  align-items: center;
  gap: var(--space-2);
  color: rgba(255, 255, 255, 0.88);
  z-index: 2;
}

.live-video-stage__controls > span {
  display: grid;
  width: 30px;
  height: 30px;
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
  z-index: 2;
  right: var(--space-4);
  bottom: var(--space-4);
  min-height: 45px;
  width: 102px;
  align-items: center;
  justify-content: center;
  padding: 0;
  border: 0;
  border-radius: 9px;
  background: var(--color-ai);
  box-shadow: 0 2px 16px rgba(111, 91, 211, 0.45);
  gap: var(--space-2);
  color: #fff;
  font-size: 14px;
  font-weight: 600;
}

.live-video-stage__try-on:hover {
  opacity: 0.9;
}

.live-video-stage__try-on:focus-visible {
  outline: 3px solid #fff;
  outline-offset: 2px;
}

.live-video-stage__try-on svg {
  width: 18px;
  height: 18px;
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
    min-height: 320px;
  }
}
</style>
