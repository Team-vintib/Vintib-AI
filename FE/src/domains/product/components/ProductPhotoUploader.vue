<script setup lang="ts">
import type {
  ProductRegistrationPhotoDraft,
  ProductRegistrationPhotoRole,
} from '@/domains/product/types/productRegistration.types'

interface Props {
  id: string
  title: string
  description: string
  role: ProductRegistrationPhotoRole
  photos: ProductRegistrationPhotoDraft[]
  representativePhotoId: string
  multiple?: boolean
  required?: boolean
  error?: string
  requirementLabel?: string
  requirementMet?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  multiple: false,
  required: false,
  error: '',
  requirementLabel: '',
  requirementMet: true,
})

const emit = defineEmits<{
  upload: [role: ProductRegistrationPhotoRole, files: File[]]
  remove: [photoId: string]
  selectRepresentative: [photoId: string]
}>()

const handleFileChange = (event: Event) => {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files ?? [])

  if (files.length > 0) {
    emit('upload', props.role, files)
  }

  input.value = ''
}
</script>

<template>
  <section class="product-photo-uploader" :aria-labelledby="`${id}-title`">
    <div class="product-photo-uploader__header">
      <div>
        <h3 :id="`${id}-title`">
          <span>{{ title }}</span>
          <span v-if="required" class="product-photo-uploader__required" aria-hidden="true"> * </span>
          <span v-if="required" class="product-photo-uploader__required-text"> 필수 입력 </span>
          <em
            v-if="requirementLabel"
            :class="{ 'product-photo-uploader__requirement--unmet': !requirementMet }"
          >
            {{ requirementLabel }}
          </em>
        </h3>
        <p>{{ description }}</p>
      </div>
      <label class="product-photo-uploader__trigger" :for="id">
        사진 선택
        <input
          :id="id"
          type="file"
          accept="image/*"
          :multiple="multiple"
          :aria-describedby="error ? `${id}-error` : undefined"
          @change="handleFileChange"
        />
      </label>
    </div>

    <p v-if="error" :id="`${id}-error`" class="product-photo-uploader__error" role="alert">
      {{ error }}
    </p>

    <div v-if="photos.length" class="product-photo-uploader__grid">
      <article
        v-for="photo in photos"
        :key="photo.id"
        class="product-photo-uploader__item"
        :class="{
          'product-photo-uploader__item--representative': photo.id === representativePhotoId,
        }"
      >
        <img :src="photo.previewUrl" :alt="`${title} 미리보기`" />
        <div class="product-photo-uploader__item-actions">
          <button
            type="button"
            :aria-pressed="photo.id === representativePhotoId"
            @click="emit('selectRepresentative', photo.id)"
          >
            {{ photo.id === representativePhotoId ? '대표 이미지' : '대표 선택' }}
          </button>
          <button type="button" @click="emit('remove', photo.id)">삭제</button>
        </div>
      </article>
    </div>

    <div v-else class="product-photo-uploader__empty" role="status">
      <strong>아직 선택한 사진이 없습니다.</strong>
    </div>
  </section>
</template>

<style scoped lang="scss">
.product-photo-uploader {
  display: grid;
  gap: var(--space-4);
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
}

.product-photo-uploader__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
}

.product-photo-uploader__header div {
  display: grid;
  gap: var(--space-1);
}

.product-photo-uploader__header h3 {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--color-text-primary);
  font-size: 18px;
  font-weight: var(--font-weight-bold);
  line-height: 26px;
}

.product-photo-uploader__header h3 em {
  color: var(--color-text-primary);
  font-size: 14px;
  font-style: normal;
  font-weight: var(--font-weight-bold);
}

.product-photo-uploader__required {
  margin-left: 2px;
  color: var(--color-error);
}

.product-photo-uploader__required-text {
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

.product-photo-uploader__header h3 .product-photo-uploader__requirement--unmet {
  color: var(--color-error);
}

.product-photo-uploader__header p {
  color: var(--color-text-secondary);
  font-size: 14px;
  line-height: 20px;
}

.product-photo-uploader__trigger {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 96px;
  height: var(--button-height-small);
  padding: 0 var(--space-4);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-primary);
  cursor: pointer;
  flex: 0 0 auto;
  font-size: 13px;
  font-weight: var(--font-weight-bold);
}

.product-photo-uploader__trigger input {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
}

.product-photo-uploader__error {
  color: var(--color-error);
  font-size: 13px;
  line-height: 20px;
}

.product-photo-uploader__grid {
  display: grid;
  gap: var(--space-4);
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.product-photo-uploader__item {
  display: grid;
  overflow: hidden;
  gap: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface-secondary);
}

.product-photo-uploader__item--representative {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
}

.product-photo-uploader__item img {
  width: 100%;
  aspect-ratio: 4 / 5;
  object-fit: cover;
}

.product-photo-uploader__item-actions {
  display: grid;
  gap: var(--space-2);
  padding: 0 var(--space-2) var(--space-3);
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.product-photo-uploader__item-actions button {
  min-width: 0;
  height: var(--button-height-small);
  padding: 0 var(--space-2);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-size: 12px;
  font-weight: var(--font-weight-bold);
  white-space: nowrap;
}

.product-photo-uploader__item-actions button[aria-pressed='true'] {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
  color: var(--color-primary);
}

.product-photo-uploader__empty {
  display: grid;
  gap: var(--space-1);
  min-height: 132px;
  place-content: center;
  padding: var(--space-5);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface-secondary);
  color: var(--color-text-secondary);
  text-align: center;
}

.product-photo-uploader__empty strong {
  color: var(--color-text-primary);
}

@media (max-width: 720px) {
  .product-photo-uploader__header {
    flex-direction: column;
  }

  .product-photo-uploader__trigger {
    width: 100%;
  }

  .product-photo-uploader__grid {
    grid-template-columns: 1fr;
  }
}
</style>
