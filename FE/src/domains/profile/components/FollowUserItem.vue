<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import FollowButton from '@/domains/profile/components/FollowButton.vue'
import type { FollowUser } from '@/domains/profile/types/profile.types'
import { ROUTE_NAMES } from '@/shared/constants/routes'

const props = defineProps<{
  user: FollowUser
  followerCount: number
  isFollowing: boolean
  isPending: boolean
  isSelf: boolean
}>()

const emit = defineEmits<{
  toggleFollow: [userId: number]
}>()

const initial = computed(() => props.user.nickname.slice(0, 1).toUpperCase())
</script>

<template>
  <article class="follow-user-item">
    <RouterLink
      class="follow-user-item__avatar"
      :to="{ name: ROUTE_NAMES.PROFILE, params: { userId: user.id } }"
      :aria-label="`${user.nickname} 프로필 보기`"
    >
      <img v-if="user.profileImageUrl" :src="user.profileImageUrl" :alt="`${user.nickname} 프로필 사진`" />
      <span v-else>{{ initial }}</span>
    </RouterLink>

    <RouterLink
      class="follow-user-item__body"
      :to="{ name: ROUTE_NAMES.PROFILE, params: { userId: user.id } }"
    >
      <strong>{{ user.nickname }}</strong>
      <span>팔로워 {{ followerCount.toLocaleString('ko-KR') }}명 · 상품 {{ user.productCount }}개</span>
    </RouterLink>

    <FollowButton
      :is-following="isFollowing"
      :is-pending="isPending"
      :is-self="isSelf"
      @toggle="emit('toggleFollow', user.id)"
    />
  </article>
</template>

<style scoped lang="scss">
.follow-user-item {
  display: grid;
  grid-template-columns: 56px minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-4) 0;
  border-bottom: 1px solid var(--color-border);
}

.follow-user-item__avatar {
  display: grid;
  overflow: hidden;
  place-items: center;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: var(--color-surface-secondary);
  color: var(--color-text-primary);
  font-weight: 800;
  text-decoration: none;
}

.follow-user-item__avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.follow-user-item__body {
  display: grid;
  min-width: 0;
  gap: 2px;
  color: inherit;
  text-decoration: none;
}

.follow-user-item__body strong {
  overflow: hidden;
  color: var(--color-text-primary);
  font-size: 16px;
  line-height: 24px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.follow-user-item__body span {
  color: var(--color-text-secondary);
  font-size: var(--font-size-caption);
  line-height: 20px;
}

@media (max-width: 520px) {
  .follow-user-item {
    grid-template-columns: 48px minmax(0, 1fr);
  }

  .follow-user-item__avatar {
    width: 48px;
    height: 48px;
  }

  .follow-user-item .follow-button {
    grid-column: 2;
    justify-self: start;
  }
}
</style>
