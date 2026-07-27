<script setup lang="ts">
import GlobalNavigation from '@/shared/components/GlobalNavigation.vue'
</script>

<template>
  <div class="default-layout">
    <GlobalNavigation />
    <main class="default-layout__content">
      <slot />
    </main>
  </div>
</template>

<style scoped lang="scss">
.default-layout {
  min-height: 100vh;
  background: var(--color-page);
  color: var(--color-text-primary);
}

.default-layout__content {
  width: 100%;
  max-width: var(--layout-content-max-width);
  padding: var(--space-10) var(--space-12);
  margin-inline: auto;
}

@media (max-width: 1024px) {
  .default-layout__content {
    padding-right: var(--space-8);
    padding-left: var(--space-8);
  }
}

@media (max-width: 768px) {
  .default-layout__content {
    padding-right: var(--space-5);
    padding-left: var(--space-5);
  }
}
</style>
