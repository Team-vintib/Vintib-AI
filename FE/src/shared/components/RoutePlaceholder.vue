<script setup lang="ts">
import { useRoute } from 'vue-router'

import DefaultLayout from '@/shared/layouts/DefaultLayout.vue'

const route = useRoute()
</script>

<template>
  <DefaultLayout>
    <section class="route-placeholder" aria-labelledby="route-placeholder-title">
      <p class="route-placeholder__eyebrow">준비 중</p>
      <h1 id="route-placeholder-title" class="route-placeholder__title">
        {{ String(route.meta.title || '화면') }}
      </h1>
      <p class="route-placeholder__description">
        해당 화면은 라우팅 연결을 먼저 완료했고, 세부 UI는 별도 작업에서 구현합니다.
      </p>
    </section>
  </DefaultLayout>
</template>

<style scoped lang="scss">
.route-placeholder {
  display: grid;
  min-height: 360px;
  align-content: center;
  gap: var(--space-4);
}

.route-placeholder__eyebrow {
  color: var(--color-primary);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-bold);
}

.route-placeholder__title {
  color: var(--color-text-primary);
  font-size: 36px;
  font-weight: var(--font-weight-extrabold);
  line-height: 1.2;
}

.route-placeholder__description {
  max-width: 520px;
  color: var(--color-text-secondary);
  font-size: var(--font-size-md);
  line-height: 1.7;
}

@media (max-width: 768px) {
  .route-placeholder {
    min-height: 300px;
  }

  .route-placeholder__title {
    font-size: 28px;
  }
}
</style>
