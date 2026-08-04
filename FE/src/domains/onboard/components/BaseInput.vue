<script setup lang="ts">
import { ref } from 'vue'

interface Props {
  id: string
  modelValue: string
  type?: 'text' | 'tel'
  placeholder?: string
  autocomplete?: string
  inputmode?: 'text' | 'tel' | 'numeric'
  maxlength?: number
  required?: boolean
  readonly?: boolean
  disabled?: boolean
  invalid?: boolean
  describedBy?: string
}

withDefaults(defineProps<Props>(), {
  type: 'text',
  placeholder: '',
  autocomplete: 'off',
  inputmode: 'text',
  required: false,
  readonly: false,
  disabled: false,
  invalid: false,
  describedBy: undefined,
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
  blur: []
}>()

const inputElement = ref<HTMLInputElement | null>(null)

const handleInput = (event: Event) => {
  emit('update:modelValue', (event.target as HTMLInputElement).value)
}

const focus = () => {
  inputElement.value?.focus()
}

defineExpose({ focus })
</script>

<template>
  <input
    :id="id"
    ref="inputElement"
    class="base-input"
    :class="{ 'base-input--invalid': invalid }"
    :type="type"
    :value="modelValue"
    :placeholder="placeholder"
    :autocomplete="autocomplete"
    :inputmode="inputmode"
    :maxlength="maxlength"
    :required="required"
    :readonly="readonly"
    :disabled="disabled"
    :aria-invalid="invalid ? 'true' : 'false'"
    :aria-describedby="describedBy"
    @input="handleInput"
    @blur="emit('blur')"
  />
</template>

<style scoped lang="scss">
.base-input {
  width: 100%;
  height: var(--button-height-standard);
  padding: 0 var(--space-4);
  border: 1px solid var(--color-border-input);
  border-radius: var(--radius-control);
  background: transparent;
  color: var(--color-text-primary);
  font-weight: 300;
  outline: none;
  transition: border-color 160ms ease;
}

.base-input::placeholder {
  color: var(--color-text-caption);
}

.base-input:hover:not(:read-only, :disabled) {
  border-color: var(--color-border-strong);
}

.base-input:focus {
  border-color: var(--color-primary);
}

.base-input--invalid {
  border-color: var(--color-error);
}

.base-input:read-only,
.base-input:disabled {
  border-color: var(--color-border-grid);
  background: var(--color-surface);
  color: var(--color-text-muted);
}

.base-input:disabled {
  cursor: not-allowed;
  opacity: 0.64;
}
</style>
