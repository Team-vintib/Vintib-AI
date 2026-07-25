<script setup lang="ts">
interface Props {
  type?: 'button' | 'submit' | 'reset'
  variant?: 'primary' | 'secondary'
  size?: 'standard' | 'major'
  disabled?: boolean
}

const {
  type = 'button',
  variant = 'primary',
  size = 'standard',
  disabled = false,
} = defineProps<Props>()
</script>

<template>
  <button
    class="base-button"
    :class="[`base-button--${variant}`, `base-button--${size}`]"
    :type="type"
    :disabled="disabled"
  >
    <slot />
  </button>
</template>

<style scoped lang="scss">
.base-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  min-width: 120px;
  height: var(--button-height-standard);
  padding: 0 var(--space-6);
  border: 1px solid transparent;
  border-radius: var(--radius-control);
  font-weight: 600;
  line-height: 1;
  cursor: pointer;
  transition:
    background-color 160ms ease,
    border-color 160ms ease,
    color 160ms ease,
    transform 160ms ease;
}

.base-button:focus-visible {
  outline: 3px solid var(--color-primary);
  outline-offset: 3px;
}

.base-button:active:not(:disabled) {
  transform: translateY(1px);
}

.base-button--primary {
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

.base-button--primary:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.base-button--secondary {
  border-color: var(--color-border-strong);
  background: var(--color-surface);
  color: var(--color-text-primary);
}

.base-button--secondary:hover:not(:disabled) {
  background: var(--color-surface-secondary);
}

.base-button--major {
  height: var(--button-height-major);
}

.base-button:disabled {
  cursor: not-allowed;
  opacity: 0.48;
}
</style>
