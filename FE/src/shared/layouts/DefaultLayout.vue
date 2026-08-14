<script setup lang="ts">
import AppFooter from '@/shared/components/AppFooter.vue'
import AppWorkerOffNotice from '@/shared/components/AppWorkerOffNotice.vue'
import GlobalNavigation from '@/shared/components/GlobalNavigation.vue'

withDefaults(
  defineProps<{
    contentMaxWidth?: string
  }>(),
  {
    contentMaxWidth: 'var(--layout-content-max-width)',
  },
)
</script>

<template>
  <div class="default-layout">
    <div class="default-layout__sticky-header">
      <GlobalNavigation />
      <AppWorkerOffNotice />
    </div>
    <main
      class="default-layout__content"
      :style="{ '--default-layout-content-max-width': contentMaxWidth }"
    >
      <slot />
    </main>
    <AppFooter />
  </div>
</template>

<style scoped lang="scss">
.default-layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: var(--color-page);
  color: var(--color-text-primary);
}

.default-layout__sticky-header {
  position: sticky;
  top: 0;
  z-index: var(--z-top);
}

.default-layout__content {
  flex: 1 0 auto;
  width: 100%;
  max-width: var(--default-layout-content-max-width);
  padding: var(--space-8) var(--layout-gutter);
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
