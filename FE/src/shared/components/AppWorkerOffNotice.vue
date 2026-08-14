<script setup lang="ts"></script>

<template>
  <div class="worker-off-notice" role="status">
    <p class="worker-off-notice__text">
      [공지] &lt; 가상 시착 / 상품 분류 / 품질 검수 &gt; 세 기능의 로컬 워커가 꺼져있는 상태입니다.
      테스트를 원하시는 경우, A108 팀장에게 mm 부탁드립니다. 감사합니다.
    </p>
  </div>
</template>

<style scoped lang="scss">
.worker-off-notice {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  padding: var(--space-2) var(--layout-gutter);
  background: var(--color-accent);
  text-align: center;
}

.worker-off-notice__text {
  margin: 0;
  color: var(--color-primary-strong);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-control);
}

@media (max-width: 640px) {
  .worker-off-notice {
    padding: var(--space-2) var(--space-5);
  }

  .worker-off-notice__text {
    font-size: var(--font-size-3xs);
  }
}
</style>
