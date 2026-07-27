<script setup lang="ts"></script>

<template>
  <main class="auth-layout">
    <section class="auth-layout__container">
      <slot />
    </section>
  </main>
</template>

<style scoped lang="scss">
.auth-layout {
  display: flex;
  align-items: center;
  min-height: 100vh;
  padding: var(--space-10) var(--space-6);
  background: var(--color-page);
  color: var(--color-text-primary);
}

.auth-layout__container {
  display: flex;
  flex-direction: column;
  justify-content: center;
  width: 100%;
  max-width: 520px;
  margin: 0 auto;
}

@media (max-width: 560px) {
  .auth-layout {
    align-items: flex-start;
    padding: var(--space-6) var(--space-4);
  }
}
</style>
