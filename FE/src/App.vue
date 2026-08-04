<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { RouterView, useRouter } from 'vue-router'

import movingLogoImage from '@/assets/images/vintib_moving_logo.gif'
import { setupScrollReveal } from '@/shared/utils/scrollReveal'

const router = useRouter()

const SPLASH_SEEN_KEY = 'vintib_initial_splash_seen'
const SPLASH_DURATION_MS = 3690

const shouldShowSplash = () => {
  if (typeof window === 'undefined') {
    return false
  }

  return window.sessionStorage.getItem(SPLASH_SEEN_KEY) !== 'true'
}

const isSplashVisible = ref(shouldShowSplash())
let splashTimer: ReturnType<typeof window.setTimeout> | undefined

onMounted(() => {
  setupScrollReveal(router)

  if (!isSplashVisible.value) {
    return
  }

  splashTimer = window.setTimeout(() => {
    window.sessionStorage.setItem(SPLASH_SEEN_KEY, 'true')
    isSplashVisible.value = false
  }, SPLASH_DURATION_MS)
})

onUnmounted(() => {
  if (splashTimer) {
    window.clearTimeout(splashTimer)
  }
})
</script>

<template>
  <RouterView />
  <main v-if="isSplashVisible" class="app-splash" aria-label="VinTib 로딩 화면">
    <img class="app-splash__logo" :src="movingLogoImage" alt="VinTib" />
  </main>
</template>

<style scoped lang="scss">
.app-splash {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  min-height: 100vh;
  min-height: 100dvh;
  background: var(--color-surface, #ffffff);
}

.app-splash__logo {
  width: min(82vw, 720px);
  height: auto;
  object-fit: contain;
}

@media (max-width: 480px) {
  .app-splash__logo {
    width: min(88vw, 560px);
  }
}
</style>
