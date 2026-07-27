<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  id: string
  label: string
  required?: boolean
  hint?: string
  error?: string
}

const props = withDefaults(defineProps<Props>(), {
  required: false,
  hint: '',
  error: '',
})

const descriptionId = computed(() => {
  if (props.error) {
    return `${props.id}-error`
  }

  if (props.hint) {
    return `${props.id}-hint`
  }

  return undefined
})
</script>

<template>
  <div class="base-field">
    <label class="base-field__label" :for="id">
      {{ label }}
      <span v-if="required" class="base-field__required" aria-hidden="true"> * </span>
      <span v-if="required" class="base-field__required-text"> 필수 입력 </span>
    </label>

    <slot :description-id="descriptionId" :is-invalid="Boolean(error)" />

    <p
      v-if="error"
      :id="`${id}-error`"
      class="base-field__message base-field__message--error"
      role="alert"
    >
      {{ error }}
    </p>

    <p v-else-if="hint" :id="`${id}-hint`" class="base-field__message">
      {{ hint }}
    </p>
  </div>
</template>

<style scoped lang="scss">
.base-field {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  min-width: 0;
}

.base-field__label {
  color: var(--color-text-primary);
  font-size: 14px;
  font-weight: 600;
  line-height: 20px;
}

.base-field__required {
  margin-left: 2px;
  color: var(--color-error);
}

.base-field__required-text {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  overflow: hidden;
  border: 0;
  margin: -1px;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
}

.base-field__message {
  min-height: 20px;
  color: var(--color-text-secondary);
  font-size: 13px;
  line-height: 20px;
}

.base-field__message--error {
  color: var(--color-error);
}
</style>
