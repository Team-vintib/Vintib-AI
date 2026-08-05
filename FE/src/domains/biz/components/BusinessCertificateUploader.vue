<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'

interface Props {
  modelValue: File | null
  disabled?: boolean
  errorMessage?: string
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:modelValue': [file: File | null]
  'validation-error': [message: string]
}>()

const fileInputElement = ref<HTMLInputElement | null>(null)
const previewUrl = ref('')

const selectedFileName = computed(() => props.modelValue?.name ?? '')

const releasePreviewUrl = () => {
  if (!previewUrl.value) {
    return
  }

  URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = ''
}

const openFilePicker = () => {
  if (props.disabled) {
    return
  }

  fileInputElement.value?.click()
}

const handleFileChange = (event: Event) => {
  const inputElement = event.currentTarget as HTMLInputElement
  const selectedFile = inputElement.files?.[0] ?? null

  inputElement.value = ''

  if (!selectedFile) {
    return
  }

  if (!selectedFile.type.startsWith('image/')) {
    emit('validation-error', '이미지 형식의 파일만 등록할 수 있습니다.')
    return
  }

  emit('validation-error', '')
  emit('update:modelValue', selectedFile)
}

const handleDelete = () => {
  emit('validation-error', '')
  emit('update:modelValue', null)
}

watch(
  () => props.modelValue,
  (selectedFile) => {
    releasePreviewUrl()

    if (selectedFile) {
      previewUrl.value = URL.createObjectURL(selectedFile)
    }
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  releasePreviewUrl()
})
</script>

<template>
  <div class="certificate-uploader">
    <input
      ref="fileInputElement"
      class="certificate-uploader__input"
      type="file"
      accept="image/*"
      aria-label="사업자등록증 이미지 선택"
      :disabled="disabled"
      :aria-invalid="errorMessage ? 'true' : 'false'"
      aria-describedby="certificate-upload-description certificate-upload-error"
      @change="handleFileChange"
    />

    <div
      v-if="modelValue && previewUrl"
      class="certificate-preview"
      :class="{ 'certificate-preview--invalid': errorMessage }"
    >
      <img
        class="certificate-preview__image"
        :src="previewUrl"
        :alt="`선택한 사업자등록증 미리보기: ${selectedFileName}`"
      />

      <div class="certificate-preview__details" role="status">
        <div class="certificate-preview__file">
          <strong>사업자등록증을 선택했습니다.</strong>
          <span :title="selectedFileName">{{ selectedFileName }}</span>
        </div>

        <div class="certificate-preview__actions">
          <button
            type="button"
            class="certificate-uploader__button"
            :disabled="disabled"
            @click="openFilePicker"
          >
            이미지 변경
          </button>
          <button
            type="button"
            class="certificate-uploader__button certificate-uploader__button--danger"
            :disabled="disabled"
            @click="handleDelete"
          >
            삭제
          </button>
        </div>
      </div>
    </div>

    <button
      v-else
      type="button"
      class="certificate-upload-empty"
      :class="{ 'certificate-upload-empty--invalid': errorMessage }"
      :disabled="disabled"
      :aria-invalid="errorMessage ? 'true' : 'false'"
      aria-describedby="certificate-upload-description certificate-upload-error"
      @click="openFilePicker"
    >
      <span class="certificate-upload-empty__icon" aria-hidden="true">
        <svg viewBox="0 0 24 24" focusable="false">
          <path d="M12 16V4m0 0L7.5 8.5M12 4l4.5 4.5" />
          <path d="M5 14v4.25A1.75 1.75 0 0 0 6.75 20h10.5A1.75 1.75 0 0 0 19 18.25V14" />
        </svg>
      </span>
      <strong>이미지 등록</strong>
      <span id="certificate-upload-description">사업자등록증 이미지를 선택해 주세요.</span>
    </button>

    <p
      v-if="errorMessage"
      id="certificate-upload-error"
      class="certificate-uploader__error"
      role="alert"
    >
      {{ errorMessage }}
    </p>
  </div>
</template>

<style scoped lang="scss">
.certificate-uploader__input {
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

.certificate-upload-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  min-height: 220px;
  padding: var(--space-8);
  border: 1px dashed var(--color-border-strong);
  border-radius: var(--radius-media);
  background: var(--color-surface-secondary);
  color: var(--color-text-primary);
  cursor: pointer;
  flex-direction: column;
  font: inherit;
  text-align: center;
  transition:
    border-color 160ms ease,
    background 160ms ease;
}

.certificate-upload-empty:hover {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
}

.certificate-upload-empty--invalid,
.certificate-preview--invalid {
  border-color: var(--color-error);
}

.certificate-upload-empty:disabled {
  cursor: not-allowed;
  opacity: 0.64;
}

.certificate-upload-empty:focus-visible,
.certificate-uploader__button:focus-visible {
  outline: 1px solid var(--color-primary);
  outline-offset: 2px;
}

.certificate-upload-empty__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: var(--color-surface);
  color: var(--color-primary);
}

.certificate-upload-empty__icon svg {
  width: 26px;
  height: 26px;
  fill: none;
  stroke: currentcolor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.8;
}

.certificate-upload-empty strong {
  margin-top: var(--space-4);
  font-size: 15px;
  line-height: 20px;
}

.certificate-upload-empty > span:last-child {
  margin-top: var(--space-1);
  color: var(--color-text-secondary);
  font-size: 13px;
  line-height: 18px;
}

.certificate-preview {
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-media);
  background: var(--color-surface-secondary);
}

.certificate-preview__image {
  width: 100%;
  height: 280px;
  padding: var(--space-4);
  object-fit: contain;
}

.certificate-preview__details {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-4);
  border-top: 1px solid var(--color-border);
  background: var(--color-surface);
}

.certificate-preview__file {
  display: flex;
  min-width: 0;
  flex-direction: column;
}

.certificate-preview__file strong {
  font-size: 14px;
  line-height: 20px;
}

.certificate-preview__file span {
  max-width: 320px;
  overflow: hidden;
  margin-top: var(--space-1);
  color: var(--color-text-secondary);
  font-size: 13px;
  line-height: 18px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.certificate-preview__actions {
  display: flex;
  flex: 0 0 auto;
  gap: var(--space-2);
}

.certificate-uploader__button {
  min-height: var(--button-height-small);
  padding: 0 var(--space-4);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-primary);
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
}

.certificate-uploader__button:hover {
  border-color: var(--color-primary);
}

.certificate-uploader__button:disabled {
  cursor: not-allowed;
  opacity: 0.64;
}

.certificate-uploader__button--danger {
  border-color: var(--color-error);
  color: var(--color-error);
}

.certificate-uploader__error {
  margin-top: var(--space-2);
  color: var(--color-error);
  font-size: 13px;
  line-height: 18px;
}

@media (max-width: 640px) {
  .certificate-preview__details {
    align-items: stretch;
    flex-direction: column;
  }

  .certificate-preview__actions {
    width: 100%;
  }

  .certificate-uploader__button {
    flex: 1 1 0;
  }
}
</style>
