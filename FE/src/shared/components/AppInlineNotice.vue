<script setup lang="ts">
/**
 * 화면 안에 한 줄로 뜨는 안내(오류·완료·정보) 공용 컴포넌트.
 *
 * 라이브·채팅·경매·구매·시착 화면마다 크기(10~15px)·색(토큰/하드코딩 혼재)·모양(민텍스트/
 * 테두리박스)이 제각각이라, 같은 성격의 알림이 화면마다 다르게 보였다. 규격을 여기 한 곳에 둔다.
 *
 * 어두운 라이브 계열 화면 기준으로 색을 잡았다(`--color-status-*`는 그 용도로 이미 정의돼 있다).
 */
withDefaults(
  defineProps<{
    variant?: 'error' | 'success' | 'info'
  }>(),
  {
    variant: 'info',
  },
)
</script>

<template>
  <p
    class="app-inline-notice"
    :class="`app-inline-notice--${variant}`"
    :role="variant === 'error' ? 'alert' : 'status'"
  >
    <svg v-if="variant === 'error'" viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7.5v5" />
      <path d="M12 16.2v.3" />
    </svg>
    <svg v-else-if="variant === 'success'" viewBox="0 0 24 24" aria-hidden="true">
      <path d="m5 12.5 4.5 4.5L19 7.5" />
    </svg>
    <svg v-else viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="9" />
      <path d="M12 11v5.5" />
      <path d="M12 7.5v.3" />
    </svg>
    <span><slot /></span>
  </p>
</template>

<style scoped lang="scss">
.app-inline-notice {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 7px 10px;
  border-left: 2px solid currentColor;
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-medium);
  line-height: var(--line-height-snug);
}

.app-inline-notice svg {
  width: 15px;
  height: 15px;
  flex-shrink: 0;
  margin-top: 1px;
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.8;
}

.app-inline-notice--error {
  border-left-color: var(--color-error);
  background: var(--color-status-error-bg);
  color: var(--color-status-error-text);
}

.app-inline-notice--success {
  background: var(--color-status-success-bg);
  color: var(--color-status-success-text);
}

.app-inline-notice--info {
  background: rgba(242, 240, 237, 0.06);
  color: var(--color-live-text-secondary);
  font-weight: var(--font-weight-regular);
}
</style>
