<script setup lang="ts">
defineProps<{
  winnerNickname: string
  winningBid: number
  productTitle?: string | null
}>()

const emit = defineEmits<{
  close: []
}>()

// 팝업 뒤에서 위로 터지는 불꽃놀이 파티클.
// 몇 개의 버스트 지점에서 파티클이 방사형으로 퍼지며 사라진다.
const FIREWORK_BURSTS = [
  { x: 30, y: 32, hue: 280, delay: 0 },
  { x: 70, y: 26, hue: 45, delay: 0.5 },
  { x: 50, y: 42, hue: 330, delay: 1 },
]
const PARTICLES_PER_BURST = 14
const fireworks = FIREWORK_BURSTS.flatMap((burst, burstIndex) =>
  Array.from({ length: PARTICLES_PER_BURST }, (_, particleIndex) => {
    const angle = (particleIndex / PARTICLES_PER_BURST) * Math.PI * 2
    const distance = 66 + (particleIndex % 3) * 16

    return {
      key: `${burstIndex}-${particleIndex}`,
      x: burst.x,
      y: burst.y,
      dx: Math.round(Math.cos(angle) * distance),
      dy: Math.round(Math.sin(angle) * distance),
      hue: (burst.hue + particleIndex * 12) % 360,
      delay: burst.delay,
    }
  }),
)
</script>

<template>
  <div
    class="auction-result"
    role="alertdialog"
    aria-labelledby="auction-result-title"
    aria-live="assertive"
  >
    <div class="auction-result__fireworks" aria-hidden="true">
      <span
        v-for="particle in fireworks"
        :key="particle.key"
        :style="{
          left: `${particle.x}%`,
          top: `${particle.y}%`,
          '--dx': `${particle.dx}px`,
          '--dy': `${particle.dy}px`,
          '--hue': particle.hue,
          animationDelay: `${particle.delay}s`,
        }"
      ></span>
    </div>

    <div class="auction-result__card">
      <p class="auction-result__eyebrow">경매 낙찰</p>

      <p class="auction-result__label">낙찰자</p>
      <h2 id="auction-result-title" class="auction-result__winner">
        <span aria-hidden="true">🎉</span>{{ winnerNickname }}
      </h2>

      <p class="auction-result__label auction-result__label--price">낙찰가</p>
      <strong class="auction-result__price">{{ winningBid.toLocaleString('ko-KR') }}P</strong>

      <p v-if="productTitle" class="auction-result__product">{{ productTitle }}</p>

      <button type="button" class="auction-result__close" @click="emit('close')">확인</button>
    </div>
  </div>
</template>

<style scoped lang="scss">
.auction-result {
  display: grid;
  position: absolute;
  z-index: 6;
  inset: 0;
  overflow: hidden;
  background: radial-gradient(circle at 50% 36%, rgba(126, 87, 194, 0.36), rgba(4, 6, 5, 0.84) 62%);
  place-items: center;
  backdrop-filter: blur(3px);
  animation: auction-result-fade 240ms ease-out;
}

.auction-result__card {
  display: flex;
  position: relative;
  z-index: var(--z-layer-1);
  max-width: min(360px, 84%);
  padding: var(--space-6) var(--space-5);
  border: 1px solid var(--color-live-border);
  border-radius: var(--radius-media);
  background: rgba(17, 21, 20, 0.88);
  box-shadow: none;
  text-align: center;
  flex-direction: column;
  align-items: center;
  animation: auction-result-pop 340ms cubic-bezier(0.2, 0.9, 0.3, 1.25);
}

.auction-result__eyebrow {
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

.auction-result__label {
  margin-top: var(--space-4);
  color: var(--color-live-text-secondary);
  font-size: var(--font-size-2xs);
  line-height: var(--line-height-xs);
}

.auction-result__label--price {
  margin-top: var(--space-5);
}

.auction-result__winner {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-top: 4px;
  color: var(--color-live-text-primary);
  font-family: var(--font-display);
  font-size: var(--font-size-3xl);
  font-weight: var(--font-weight-semibold);
  letter-spacing: -0.03em;
  line-height: 1.15;
  word-break: break-all;
}

.auction-result__price {
  margin-top: var(--space-2);
  color: var(--color-accent);
  font-family: var(--font-mono);
  font-size: 38px;
  font-variant-numeric: tabular-nums;
  font-weight: var(--font-weight-medium);
  letter-spacing: -0.03em;
  line-height: 1.1;
}

.auction-result__product {
  max-width: 280px;
  margin-top: var(--space-3);
  color: var(--color-live-text-secondary);
  font-size: var(--font-size-xs);
  line-height: var(--line-height-snug);
}

.auction-result__close {
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

.auction-result__close:hover {
  background: var(--color-accent-hover);
  border-color: var(--color-accent-hover);
}

.auction-result__close:focus-visible {
  outline: 1px solid var(--color-primary-strong);
  outline-offset: 2px;
}

.auction-result__fireworks {
  position: absolute;
  z-index: 0;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
}

.auction-result__fireworks span {
  position: absolute;
  width: 7px;
  height: 7px;
  margin: -3px 0 0 -3px;
  border-radius: 50%;
  background: hsl(var(--hue) 92% 64%);
  box-shadow: none;
  opacity: 0;
  animation: auction-firework var(--duration-pulse) ease-out infinite;
}

@keyframes auction-firework {
  0% {
    transform: translate(0, 0) scale(0.6);
    opacity: 0;
  }
  12% {
    opacity: 1;
  }
  70% {
    opacity: 0.85;
  }
  100% {
    transform: translate(var(--dx), var(--dy)) scale(0.3);
    opacity: 0;
  }
}

@keyframes auction-result-pop {
  from {
    transform: scale(0.86);
    opacity: 0;
  }
  to {
    transform: scale(1);
    opacity: 1;
  }
}

@keyframes auction-result-fade {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@media (prefers-reduced-motion: reduce) {
  .auction-result,
  .auction-result__card {
    animation: none;
  }

  .auction-result__fireworks {
    display: none;
  }
}
</style>
