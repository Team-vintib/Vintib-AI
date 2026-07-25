<script setup lang="ts">
</script>

<template>
  <main class="min-h-screen bg-[var(--color-page)] px-6 py-10 text-[var(--color-text-primary)]">
    <section class="mx-auto flex min-h-[calc(100vh-80px)] w-full max-w-[480px] flex-col justify-center">
      <slot />
    </section>
  </main>
</template>
