<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'

import BaseButton from '@/domains/onboard/components/BaseButton.vue'

interface Props {
  modelValue: File | null
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:modelValue': [file: File | null]
}>()

const fileInputElement = ref<HTMLInputElement | null>(null)
const captureInputElement = ref<HTMLInputElement | null>(null)
const previewUrl = ref('')
const fileError = ref('')

const selectedFileName = computed(() => props.modelValue?.name ?? '')

const releasePreviewUrl = () => {
  if (!previewUrl.value) {
    return
  }

  URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = ''
}

const resetFileInputs = () => {
  if (fileInputElement.value) {
    fileInputElement.value.value = ''
  }

  if (captureInputElement.value) {
    captureInputElement.value.value = ''
  }
}

const openFilePicker = () => {
  fileError.value = ''
  fileInputElement.value?.click()
}

const openCameraPicker = () => {
  fileError.value = ''
  captureInputElement.value?.click()
}

const handleFileChange = (event: Event) => {
  const inputElement = event.currentTarget as HTMLInputElement
  const selectedFile = inputElement.files?.[0]

  inputElement.value = ''

  if (!selectedFile) {
    return
  }

  if (!selectedFile.type.startsWith('image/')) {
    fileError.value = '이미지 파일만 등록할 수 있습니다.'
    return
  }

  fileError.value = ''
  emit('update:modelValue', selectedFile)
}

const handleDelete = () => {
  fileError.value = ''
  resetFileInputs()
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
  <div class="full-body-photo-uploader">
    <input
      ref="fileInputElement"
      class="full-body-photo-uploader__input"
      type="file"
      accept="image/*"
      aria-label="전신 사진 파일 선택"
      @change="handleFileChange"
    />

    <input
      ref="captureInputElement"
      class="full-body-photo-uploader__input"
      type="file"
      accept="image/*"
      capture="environment"
      aria-label="전신 사진 촬영"
      @change="handleFileChange"
    />

    <div v-if="modelValue && previewUrl" class="photo-preview">
      <div class="photo-preview__media">
        <img :src="previewUrl" :alt="`선택한 전신 사진 미리보기: ${selectedFileName}`" />
      </div>

      <div class="photo-preview__details" role="status">
        <div class="photo-preview__file">
          <strong>전신 사진을 등록했습니다.</strong>
          <span :title="selectedFileName">{{ selectedFileName }}</span>
        </div>

        <div class="photo-preview__actions">
          <BaseButton variant="secondary" @click="openFilePicker">
            <svg
              class="full-body-photo-uploader__button-icon"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path
                d="M12 16V4m0 0L7.5 8.5M12 4l4.5 4.5M5 14v4.25A1.75 1.75 0 0 0 6.75 20h10.5A1.75 1.75 0 0 0 19 18.25V14"
              />
            </svg>
            사진 변경
          </BaseButton>

          <BaseButton class="photo-preview__delete" variant="secondary" @click="handleDelete">
            <svg
              class="full-body-photo-uploader__button-icon"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path d="M4.5 7h15M9 7V4.75h6V7m-8 0 .75 13h8.5L17 7M10 10.5v6m4-6v6" />
            </svg>
            사진 삭제
          </BaseButton>
        </div>
      </div>
    </div>

    <div v-else class="photo-upload-empty" role="status">
      <span class="photo-upload-empty__icon" aria-hidden="true">
        <svg viewBox="0 0 24 24" focusable="false">
          <path
            d="M4 5.75A1.75 1.75 0 0 1 5.75 4h12.5A1.75 1.75 0 0 1 20 5.75v12.5A1.75 1.75 0 0 1 18.25 20H5.75A1.75 1.75 0 0 1 4 18.25V5.75Z"
          />
          <path d="m6.5 17 3.2-3.8 2.25 2.35 1.85-2.15L17.5 17" />
          <circle cx="15.75" cy="8.25" r="1.25" />
        </svg>
      </span>

      <strong>등록된 전신 사진이 없습니다.</strong>
      <p>이미지 파일을 선택하거나 카메라로 촬영해 주세요.</p>

      <div class="photo-upload-empty__actions" aria-label="전신 사진 등록 방법">
        <BaseButton variant="secondary" @click="openFilePicker">
          <svg class="full-body-photo-uploader__button-icon" viewBox="0 0 24 24" aria-hidden="true">
            <path
              d="M12 16V4m0 0L7.5 8.5M12 4l4.5 4.5M5 14v4.25A1.75 1.75 0 0 0 6.75 20h10.5A1.75 1.75 0 0 0 19 18.25V14"
            />
          </svg>
          사진 등록
        </BaseButton>

        <BaseButton variant="secondary" @click="openCameraPicker">
          <svg class="full-body-photo-uploader__button-icon" viewBox="0 0 24 24" aria-hidden="true">
            <path
              d="M4 8.75A1.75 1.75 0 0 1 5.75 7h2l1.1-2h6.3l1.1 2h2A1.75 1.75 0 0 1 20 8.75v8.5A1.75 1.75 0 0 1 18.25 19H5.75A1.75 1.75 0 0 1 4 17.25v-8.5Z"
            />
            <circle cx="12" cy="13" r="3.25" />
          </svg>
          즉시 촬영
        </BaseButton>
      </div>
    </div>

    <p v-if="fileError" class="full-body-photo-uploader__error" role="alert">
      {{ fileError }}
    </p>
  </div>
</template>

<style scoped lang="scss">
.full-body-photo-uploader {
  min-width: 0;
}

.full-body-photo-uploader__input {
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

.photo-upload-empty,
.photo-preview {
  min-height: 320px;
  border: 1px dashed var(--color-border-strong);
  border-radius: var(--radius-media);
  background: var(--color-surface-secondary);
}

.photo-upload-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-8);
  flex-direction: column;
  text-align: center;
}

.photo-upload-empty strong {
  margin-top: var(--space-4);
  font-size: 17px;
  line-height: 24px;
}

.photo-upload-empty p {
  margin-top: var(--space-1);
  color: var(--color-text-secondary);
  font-size: 13px;
}

.photo-upload-empty__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: var(--color-ai-soft);
  color: var(--color-ai);
}

.photo-upload-empty__icon svg {
  width: 30px;
  height: 30px;
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.7;
}

.photo-upload-empty__actions,
.photo-preview__actions {
  display: flex;
  gap: var(--space-3);
}

.photo-upload-empty__actions {
  justify-content: center;
  margin-top: var(--space-6);
}

.full-body-photo-uploader__button-icon {
  width: 20px;
  height: 20px;
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.8;
}

.photo-preview {
  display: grid;
  overflow: hidden;
  grid-template-rows: minmax(240px, 1fr) auto;
}

.photo-preview__media {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 240px;
  padding: var(--space-4);
  background: var(--color-page);
}

.photo-preview__media img {
  width: 100%;
  height: 100%;
  max-height: 420px;
  object-fit: contain;
}

.photo-preview__details {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-4);
  border-top: 1px solid var(--color-border);
  background: var(--color-surface);
}

.photo-preview__file {
  display: flex;
  min-width: 0;
  flex-direction: column;
}

.photo-preview__file strong {
  font-size: 14px;
  line-height: 20px;
}

.photo-preview__file span {
  max-width: 280px;
  overflow: hidden;
  margin-top: var(--space-1);
  color: var(--color-text-secondary);
  font-size: 13px;
  line-height: 18px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.photo-preview__delete {
  border-color: var(--color-error);
  color: var(--color-error);
}

.photo-preview__delete:hover {
  background: var(--color-error-soft);
}

.full-body-photo-uploader__error {
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-control);
  margin-top: var(--space-3);
  background: var(--color-error-soft);
  color: var(--color-error);
  font-size: 13px;
  font-weight: 600;
  line-height: 20px;
}

@media (max-width: 720px) {
  .photo-preview__details {
    align-items: stretch;
    flex-direction: column;
  }

  .photo-preview__file span {
    max-width: 100%;
  }

  .photo-preview__actions :deep(.base-button) {
    flex: 1 1 0;
    min-width: 0;
  }
}

@media (max-width: 560px) {
  .photo-upload-empty {
    min-height: 280px;
    padding: var(--space-5);
  }

  .photo-upload-empty__actions,
  .photo-preview__actions {
    align-items: stretch;
    width: 100%;
    flex-direction: column;
  }

  .photo-upload-empty__actions :deep(.base-button),
  .photo-preview__actions :deep(.base-button) {
    width: 100%;
  }
}
</style>
