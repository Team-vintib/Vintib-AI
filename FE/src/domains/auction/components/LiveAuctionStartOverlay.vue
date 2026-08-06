<script setup lang="ts">
defineProps<{
  productTitle?: string | null
}>()

const emit = defineEmits<{
  close: []
}>()
</script>

<template>
  <div
    class="auction-start"
    role="alertdialog"
    aria-labelledby="auction-start-title"
    aria-live="assertive"
  >
    <div class="auction-start__card">
      <p class="auction-start__eyebrow">경매 시작</p>

      <h2 id="auction-start-title" class="auction-start__title">
        <span aria-hidden="true">🔨</span>{{ productTitle || '상품' }}
      </h2>

      <p class="auction-start__desc">지금 입찰할 수 있습니다.</p>

      <button type="button" class="auction-start__close" @click="emit('close')">확인</button>
    </div>
  </div>
</template>

<style scoped lang="scss">
/* LiveAuctionResultOverlay(낙찰 알림)와 동일한 오버레이·카드 디자인 — 불꽃놀이만 뺀 시작 알림용 */
.auction-start {
  display: grid;
  position: absolute;
  z-index: 6;
  inset: 0;
  overflow: hidden;
  background: radial-gradient(circle at 50% 36%, rgba(126, 87, 194, 0.36), rgba(4, 6, 5, 0.84) 62%);
  place-items: center;
  backdrop-filter: blur(3px);
  animation: auction-start-fade 240ms ease-out;
}

.auction-start__card {
  display: flex;
  position: relative;
  z-index: var(--z-layer-1);
  max-width: min(360px, 84%);
  padding: var(--space-6) var(--space-5);
  border: 1px solid var(--color-live-border);
  border-radius: var(--radius-media);
  background: rgba(17, 21, 20, 0.88);
  text-align: center;
  flex-direction: column;
  align-items: center;
  animation: auction-start-pop 340ms cubic-bezier(0.2, 0.9, 0.3, 1.25);
}

.auction-start__eyebrow {
  padding: 4px 12px;
  border: 1px solid var(--color-accent);
  border-radius: var(--radius-badge);
  color: var(--color-accent);
  font-family: var(--font-mono);
  font-size: var(--font-size-badge);
  font-weight: var(--font-weight-medium);
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.auction-start__title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-top: var(--space-4);
  color: var(--color-live-text-primary);
  font-family: var(--font-display);
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-semibold);
  letter-spacing: -0.03em;
  line-height: 1.15;
  word-break: break-all;
}

.auction-start__desc {
  max-width: 280px;
  margin-top: var(--space-3);
  color: var(--color-live-text-secondary);
  font-size: var(--font-size-xs);
  line-height: var(--line-height-snug);
}

.auction-start__close {
  height: var(--button-height-tight);
  margin-top: var(--space-5);
  padding: 0 var(--space-6);
  border: 1px solid var(--color-accent);
  border-radius: var(--radius-control);
  background: var(--color-accent);
  color: var(--color-primary-strong);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-medium);
  transition: background-color var(--transition-base);
}

.auction-start__close:hover {
  background: var(--color-accent-hover);
  border-color: var(--color-accent-hover);
}

.auction-start__close:focus-visible {
  outline: 1px solid var(--color-primary-strong);
  outline-offset: 2px;
}

@keyframes auction-start-pop {
  from {
    transform: scale(0.86);
    opacity: 0;
  }
  to {
    transform: scale(1);
    opacity: 1;
  }
}

@keyframes auction-start-fade {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@media (prefers-reduced-motion: reduce) {
  .auction-start,
  .auction-start__card {
    animation: none;
  }
}
</style>
