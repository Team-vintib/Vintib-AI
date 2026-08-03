<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  isFollowing: boolean
  isPending?: boolean
  isSelf?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  isPending: false,
  isSelf: false,
})

const emit = defineEmits<{
  toggle: []
}>()

const label = computed(() => {
  if (props.isPending) {
    return '처리 중'
  }

  return props.isFollowing ? '팔로잉' : '팔로우'
})
</script>

<template>
  <button
    v-if="!isSelf"
    class="follow-button"
    :class="{ 'follow-button--active': isFollowing }"
    type="button"
    :aria-pressed="isFollowing"
    :disabled="isPending"
    @click="emit('toggle')"
  >
    {{ label }}
  </button>
</template>

<style scoped lang="scss">
.follow-button {
  min-width: 108px;
  height: 40px;
  padding: 0 var(--space-4);
  border: 1px solid var(--color-primary);
  border-radius: 10px;
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-bold);
  transition:
    border-color 160ms ease,
    background-color 160ms ease,
    color 160ms ease,
    opacity 160ms ease;
}

.follow-button:hover:not(:disabled) {
  border-color: var(--color-primary-hover);
  background: var(--color-primary-hover);
}

.follow-button--active {
  border-color: var(--color-primary);
  background: var(--color-surface);
  color: var(--color-primary);
}

.follow-button--active:hover:not(:disabled) {
  border-color: var(--color-primary-hover);
  background: var(--color-primary-soft);
  color: var(--color-primary-hover);
}

.follow-button:disabled {
  cursor: wait;
  opacity: 0.7;
}

.follow-button:focus-visible {
  outline: 3px solid var(--color-primary-soft);
  outline-offset: 2px;
}
</style>
