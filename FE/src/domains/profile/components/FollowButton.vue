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
    return props.isFollowing ? '해제 중' : '팔로우 중'
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
  min-width: 88px;
  height: var(--button-height-small);
  padding: 0 var(--space-4);
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-control);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-bold);
}

.follow-button--active {
  background: var(--color-surface);
  color: var(--color-primary);
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

