<script setup lang="ts">
import LiveListCard from '@/domains/live/components/LiveListCard.vue'
import { liveListMockData } from '@/domains/live/constants/liveListMockData'
import DefaultLayout from '@/shared/layouts/DefaultLayout.vue'
</script>

<template>
  <DefaultLayout content-max-width="1200px">
    <section class="live-list-page" aria-labelledby="live-list-title">
      <header class="live-list-page__header">
        <p class="live-list-page__eyebrow">LIVE &amp; UPCOMING</p>
        <div class="live-list-page__heading-row">
          <div>
            <h1 id="live-list-title">라이브 둘러보기</h1>
            <p>빈티지 셀러의 진행 중 방송과 예정 라이브를 한눈에 확인해 보세요.</p>
          </div>
          <span class="live-list-page__count" aria-live="polite">
            총 {{ liveListMockData.length }}개
          </span>
        </div>
      </header>

      <div class="live-list-page__grid" aria-label="라이브 방송 목록">
        <LiveListCard v-for="live in liveListMockData" :key="live.id" :live="live" />
      </div>
    </section>
  </DefaultLayout>
</template>

<style scoped lang="scss">
.live-list-page {
  display: grid;
  gap: var(--space-8);
}

.live-list-page__header {
  display: grid;
  gap: var(--space-3);
}

.live-list-page__eyebrow {
  color: var(--color-live);
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0.08em;
}

.live-list-page__heading-row {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: var(--space-6);
}

.live-list-page__heading-row h1 {
  color: var(--color-text-primary);
  font-size: clamp(30px, 4vw, 44px);
  font-weight: 800;
  line-height: 1.2;
}

.live-list-page__heading-row p {
  margin-top: var(--space-3);
  color: var(--color-text-secondary);
  font-size: 16px;
  line-height: 26px;
}

.live-list-page__count {
  flex: 0 0 auto;
  color: var(--color-text-secondary);
  font-size: 14px;
  font-weight: 600;
}

.live-list-page__grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-6);
}

@media (max-width: 960px) {
  .live-list-page__grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .live-list-page {
    gap: var(--space-6);
  }

  .live-list-page__heading-row {
    align-items: start;
    flex-direction: column;
    gap: var(--space-3);
  }

  .live-list-page__grid {
    grid-template-columns: minmax(0, 1fr);
    gap: var(--space-5);
  }
}
</style>
