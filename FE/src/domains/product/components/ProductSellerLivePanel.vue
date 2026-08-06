<script setup lang="ts">
import { computed } from 'vue'

import fallbackLiveThumbnail from '@/assets/images/products/product-denim-jacket.webp'
import type { ProductLinkedLive } from '@/domains/product/types/productDetail.types'

const props = defineProps<{
  linkedLive: ProductLinkedLive | null
  sellerNickname: string
}>()

const emit = defineEmits<{
  viewLive: [liveId: number]
}>()

const displayThumbnailUrl = computed(() => props.linkedLive?.thumbnailUrl || fallbackLiveThumbnail)
const handleThumbnailError = (event: Event) => {
  const target = event.target

  if (target instanceof HTMLImageElement) {
    target.onerror = null
    target.src = fallbackLiveThumbnail
  }
}

const formattedLiveDate = computed(() => {
  if (!props.linkedLive?.startsAt) {
    return ''
  }

  const date = new Date(props.linkedLive.startsAt)

  if (Number.isNaN(date.getTime())) {
    return ''
  }

  return new Intl.DateTimeFormat('ko-KR', {
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
})
</script>

<template>
  <section
    v-if="linkedLive?.status === 'LIVE'"
    class="seller-live"
    aria-labelledby="linked-live-title"
  >
    <h2 id="linked-live-title">연결 라이브</h2>

    <article class="seller-live__live">
      <img
        :src="displayThumbnailUrl"
        :alt="`${linkedLive.title} 대표 이미지`"
        @error="handleThumbnailError"
      />
      <div class="seller-live__live-copy">
        <span class="seller-live__status">방송 중</span>
        <h3>{{ linkedLive.title }}</h3>
        <p v-if="props.sellerNickname">{{ props.sellerNickname }}</p>
        <p v-if="formattedLiveDate">{{ formattedLiveDate }}</p>
      </div>
      <div class="seller-live__actions">
        <button
          class="seller-live__link"
          type="button"
          @click="emit('viewLive', linkedLive.id)"
        >
          라이브 입장
        </button>
      </div>
    </article>
  </section>
</template>

<style scoped lang="scss">
.seller-live {
  margin-top: var(--space-12);
}

.seller-live > h2 {
  margin-bottom: var(--space-4);
  color: var(--color-text-primary);
  font-size: var(--font-size-2xl-plus);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-2xl-plus);
}

.seller-live__live {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: var(--space-5);
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
}

.seller-live__live img {
  flex: 0 0 auto;
  width: 180px;
  height: 116px;
  object-fit: cover;
}

.seller-live__live-copy {
  min-width: 0;
  flex: 1;
}

.seller-live__live-copy h3 {
  overflow: hidden;
  margin-top: var(--space-2);
  color: var(--color-text-primary);
  font-size: var(--font-size-md-plus);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-body);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.seller-live__live-copy p {
  margin-top: 2px;
  color: var(--color-text-secondary);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-regular);
  line-height: var(--line-height-snug);
}

.seller-live__status {
  display: inline-flex;
  padding: 2px 7px;
  background: var(--color-auction-soft);
  color: var(--color-auction);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-xs);
}

.seller-live__actions {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding-right: var(--space-6);
}

.seller-live__link {
  height: var(--button-height-sm);
  padding: 0 var(--space-4);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-snug);
}

.seller-live__link:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.seller-live button:focus-visible {
  outline: 1px solid var(--color-primary);
  outline-offset: 2px;
}

@media (max-width: 660px) {
  .seller-live__live {
    align-items: flex-start;
    flex-wrap: wrap;
    padding-bottom: var(--space-5);
  }

  .seller-live__live img {
    width: 100%;
    height: auto;
    aspect-ratio: 16 / 8;
  }

  .seller-live__live-copy,
  .seller-live__actions {
    padding: 0 var(--space-4);
  }
}
</style>
