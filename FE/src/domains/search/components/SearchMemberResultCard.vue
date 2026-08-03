<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import FollowButton from '@/domains/profile/components/FollowButton.vue'
import type { SearchMemberResult } from '@/domains/search/types/search.types'
import { ROUTE_NAMES } from '@/shared/constants/routes'

const props = defineProps<{
  member: SearchMemberResult
  isFollowing: boolean
  isPending?: boolean
  isSelf?: boolean
}>()

const emit = defineEmits<{
  toggleFollow: [memberId: number]
}>()

const initial = computed(() => props.member.nickname.slice(0, 1).toUpperCase())
</script>

<template>
  <article class="search-member-card">
    <RouterLink
      class="search-member-card__avatar"
      :to="{ name: ROUTE_NAMES.PROFILE, params: { userId: member.id } }"
      :aria-label="`${member.nickname} 프로필 보기`"
    >
      <img v-if="member.profileImageUrl" :src="member.profileImageUrl" :alt="member.nickname" />
      <span v-else>{{ initial }}</span>
    </RouterLink>

    <div class="search-member-card__body">
      <div class="search-member-card__header">
        <RouterLink
          class="search-member-card__profile-link"
          :to="{ name: ROUTE_NAMES.PROFILE, params: { userId: member.id } }"
        >
          <h3 class="search-member-card__name">{{ member.nickname }}</h3>
          <p class="search-member-card__stats">
            팔로워 {{ member.followerCount.toLocaleString('ko-KR') }}명 · 상품
            {{ member.productCount }}개
          </p>
        </RouterLink>

        <FollowButton
          :is-following="isFollowing"
          :is-pending="isPending"
          :is-self="isSelf"
          @toggle="emit('toggleFollow', member.id)"
        />
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
  display: grid;
  place-items: center;
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: var(--color-surface-secondary);
  color: var(--color-text-primary);
  font-weight: 800;
  text-decoration: none;
}

.search-member-card__avatar img {
  width: 100%;
  height: 100%;
  border-radius: inherit;
  object-fit: cover;
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

.search-member-card__profile-link {
  color: inherit;
  text-decoration: none;
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
