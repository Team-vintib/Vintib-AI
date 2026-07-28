<script setup lang="ts">
import type { ProductLinkedLive } from '@/domains/product/types/productDetail.types'

const props = defineProps<{
  linkedLive: ProductLinkedLive | null
  isReminderSet: boolean
}>()

const emit = defineEmits<{
  toggleReminder: []
  viewLive: [liveId: number]
}>()

const formatLiveDate = (date: string) =>
  new Intl.DateTimeFormat('ko-KR', {
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(date))
</script>

<template>
  <section v-if="linkedLive" class="seller-live" aria-labelledby="linked-live-title">
    <h2 id="linked-live-title">연결 라이브</h2>

    <article class="seller-live__live">
      <img :src="linkedLive.thumbnailUrl" :alt="`${linkedLive.title} 대표 이미지`" />
      <div class="seller-live__live-copy">
        <span class="seller-live__status">
          {{ linkedLive.status === 'LIVE' ? '방송 중' : '방송 예정' }}
        </span>
        <h3>{{ linkedLive.title }}</h3>
        <p>Vintage Hunter</p>
        <p>{{ formatLiveDate(linkedLive.startsAt) }}</p>
      </div>
      <div class="seller-live__actions">
        <button
          class="seller-live__secondary"
          :class="{ 'seller-live__secondary--active': props.isReminderSet }"
          type="button"
          :aria-pressed="props.isReminderSet"
          @click="emit('toggleReminder')"
        >
          {{ props.isReminderSet ? '알림 신청됨' : '알림 받기' }}
        </button>
        <button
          class="seller-live__link"
          type="button"
          @click="emit('viewLive', linkedLive.id)"
        >
          {{ linkedLive.status === 'LIVE' ? '라이브 입장' : '라이브 상세 보기' }}
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
  font-size: 26px;
  font-weight: 700;
  line-height: 36px;
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
  font-size: 17px;
  font-weight: 600;
  line-height: 24px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.seller-live__live-copy p {
  margin-top: 2px;
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: 400;
  line-height: 18px;
}

.seller-live__status {
  display: inline-flex;
  padding: 2px 7px;
  background: var(--color-auction-soft);
  color: var(--color-auction);
  font-size: 12px;
  font-weight: 600;
  line-height: 16px;
}

.seller-live__actions {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding-right: var(--space-6);
}

.seller-live__secondary {
  flex: 0 0 auto;
  height: 40px;
  padding: 0 var(--space-4);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-size: 13px;
  font-weight: 600;
  line-height: 18px;
}

.seller-live__link {
  border: 0;
  border-radius: var(--radius-control);
  background: transparent;
  font-size: 13px;
  font-weight: 600;
  line-height: 18px;
}

.seller-live__secondary:hover,
.seller-live__link:hover {
  color: var(--color-primary);
}

.seller-live__secondary--active {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
  color: var(--color-primary);
}

.seller-live button:focus-visible {
  outline: 3px solid var(--color-primary-soft);
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
