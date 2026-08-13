<script setup lang="ts">
import { computed } from 'vue'

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
  maxCount?: number
}

const props = withDefaults(defineProps<Props>(), {
  multiple: false,
  required: false,
  error: '',
  requirementLabel: '',
  requirementMet: true,
  maxCount: undefined,
})

const emit = defineEmits<{
  upload: [role: ProductRegistrationPhotoRole, files: File[]]
  remove: [photoId: string]
  selectRepresentative: [photoId: string]
}>()

// 단일 사진(front/back)은 이미 등록됐으면 다시 고를 필요가 없고, 여러 장(additional)은
// maxCount에 닿으면 더 못 고른다 — 두 경우 모두 "사진 선택" 트리거 자체를 숨긴다.
const canUploadMore = computed(() => {
  if (props.maxCount !== undefined && props.photos.length >= props.maxCount) {
    return false
  }

  return props.multiple || props.photos.length === 0
})

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
          <span class="product-photo-uploader__title-text">{{ title }}</span>
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
      <label v-if="canUploadMore" class="product-photo-uploader__trigger" :for="id">
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

    <div
      v-if="photos.length"
      class="product-photo-uploader__grid"
      :class="{ 'product-photo-uploader__grid--scroll': multiple }"
    >
      <article
        v-for="photo in photos"
        :key="photo.id"
        class="product-photo-uploader__item"
        :class="{
          'product-photo-uploader__item--representative': photo.id === representativePhotoId,
        }"
      >
        <div class="product-photo-uploader__media">
          <img :src="photo.previewUrl" :alt="`${title} 미리보기`" />

          <button
            type="button"
            class="product-photo-uploader__badge"
            :class="{ 'product-photo-uploader__badge--active': photo.id === representativePhotoId }"
            :aria-pressed="photo.id === representativePhotoId"
            @click="emit('selectRepresentative', photo.id)"
          >
            대표
          </button>

          <button
            type="button"
            class="product-photo-uploader__remove"
            :aria-label="`${title} 사진 삭제`"
            @click="emit('remove', photo.id)"
          >
            <svg aria-hidden="true" viewBox="0 0 24 24">
              <path
                d="M6 6l12 12M18 6 6 18"
                fill="none"
                stroke="currentColor"
                stroke-linecap="round"
                stroke-width="2"
              />
            </svg>
          </button>
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
  display: grid;
  gap: var(--space-3);
}

.product-photo-uploader__header div {
  display: grid;
  gap: var(--space-1);
  min-width: 0;
}

.product-photo-uploader__header h3 {
  display: flex;
  align-items: center;
  min-width: 0;
  gap: 4px;
  color: var(--color-text-primary);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-lg);
}

.product-photo-uploader__title-text {
  min-width: 0;
  white-space: nowrap;
}

.product-photo-uploader__header h3 em {
  flex: 0 0 auto;
  color: var(--color-text-primary);
  font-size: var(--font-size-button-small);
  font-style: normal;
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-control);
  white-space: nowrap;
}

.product-photo-uploader__required {
  flex: 0 0 auto;
  margin-left: 2px;
  color: var(--color-error);
  line-height: var(--line-height-control);
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
  font-size: var(--font-size-button-small);
  line-height: var(--line-height-control);
  white-space: pre-line;
}

.product-photo-uploader__trigger {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  min-height: var(--button-height-standard);
  padding: 0 var(--space-4);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-primary);
  cursor: pointer;
  font-size: var(--font-size-caption);
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
  font-size: var(--font-size-caption);
  line-height: var(--line-height-control);
}

.product-photo-uploader__grid {
  display: grid;
  gap: var(--space-3);
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.product-photo-uploader__grid--scroll {
  display: flex;
  overflow-x: auto;
  padding-bottom: var(--space-1);
  scroll-snap-type: x proximity;
}

.product-photo-uploader__grid--scroll .product-photo-uploader__item {
  flex: 0 0 240px;
  scroll-snap-align: start;
}

.product-photo-uploader__item {
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface-secondary);
}

.product-photo-uploader__item--representative {
  border-width: 3px;
  border-color: var(--color-error);
}

.product-photo-uploader__media {
  position: relative;
}

.product-photo-uploader__media img {
  display: block;
  width: 100%;
  aspect-ratio: 4 / 5;
  object-fit: cover;
}

.product-photo-uploader__badge {
  position: absolute;
  top: var(--space-2);
  left: var(--space-2);
  padding: var(--space-1) var(--space-3);
  border: none;
  border-radius: var(--radius-control);
  background: var(--overlay-scrim-strong);
  color: var(--color-text-primary);
  cursor: pointer;
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-control);
}

.product-photo-uploader__badge--active {
  background: var(--color-error);
  color: var(--color-text-primary);
}

.product-photo-uploader__remove {
  position: absolute;
  right: var(--space-2);
  bottom: var(--space-2);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  padding: 0;
  border: none;
  border-radius: 50%;
  background: var(--overlay-scrim-strong);
  color: var(--color-text-primary);
  cursor: pointer;
}

.product-photo-uploader__remove svg {
  width: 14px;
  height: 14px;
}

.product-photo-uploader__empty {
  display: grid;
  gap: var(--space-1);
  min-height: var(--surface-min-height-2xs);
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

  .product-photo-uploader__title-text {
    white-space: normal;
  }

  .product-photo-uploader__grid {
    grid-template-columns: 1fr;
  }
}
</style>
