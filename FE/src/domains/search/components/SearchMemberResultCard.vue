<script setup lang="ts">
import type { SearchMemberResult } from '@/domains/search/types/search.types'

defineProps<{
  member: SearchMemberResult
  isFollowing: boolean
}>()

const emit = defineEmits<{
  toggleFollow: [memberId: number]
}>()
</script>

<template>
  <article class="search-member-card">
    <img class="search-member-card__avatar" :src="member.profileImageUrl" :alt="member.nickname" />

    <div class="search-member-card__body">
      <div class="search-member-card__header">
        <div>
          <h3 class="search-member-card__name">{{ member.nickname }}</h3>
          <p class="search-member-card__stats">
            팔로워 {{ member.followerCount.toLocaleString('ko-KR') }}명 · 상품
            {{ member.productCount }}개 · 라이브 {{ member.liveCount }}회
          </p>
        </div>

        <button
          class="search-member-card__follow"
          :class="{ 'search-member-card__follow--active': isFollowing }"
          type="button"
          :aria-pressed="isFollowing"
          @click="emit('toggleFollow', member.id)"
        >
          {{ isFollowing ? '팔로잉' : '팔로우' }}
        </button>
      </div>

      <p class="search-member-card__description">{{ member.description }}</p>
    </div>
  </article>
</template>

<style scoped lang="scss">
.search-member-card {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr);
  gap: var(--space-4);
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
}

.search-member-card__avatar {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  object-fit: cover;
  background: var(--color-surface-secondary);
}

.search-member-card__body {
  min-width: 0;
}

.search-member-card__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
}

.search-member-card__name {
  color: var(--color-text-primary);
  font-size: 18px;
  font-weight: 800;
  line-height: 26px;
}

.search-member-card__stats,
.search-member-card__description {
  color: var(--color-text-secondary);
  font-size: var(--font-size-caption);
  line-height: 20px;
}

.search-member-card__description {
  display: -webkit-box;
  overflow: hidden;
  margin-top: var(--space-3);
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.search-member-card__follow {
  flex: 0 0 auto;
  min-width: 76px;
  height: var(--button-height-small);
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-control);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-bold);
}

.search-member-card__follow--active {
  background: var(--color-surface);
  color: var(--color-primary);
}

.search-member-card__follow:focus-visible {
  outline: 3px solid var(--color-primary-soft);
  outline-offset: 2px;
}

@media (max-width: 520px) {
  .search-member-card {
    grid-template-columns: 56px minmax(0, 1fr);
    padding: var(--space-4);
  }

  .search-member-card__avatar {
    width: 56px;
    height: 56px;
  }

  .search-member-card__header {
    flex-direction: column;
  }
}
</style>
