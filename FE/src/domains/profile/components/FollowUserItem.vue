<script setup lang="ts">
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

const getProfileRoute = () => ({ name: ROUTE_NAMES.PROFILE, params: { userId: props.user.id } })
</script>

<template>
  <article class="follow-user-item">
    <RouterLink
      class="follow-user-item__link"
      :to="getProfileRoute()"
      :aria-label="`${user.nickname} 프로필 보기`"
    >
      <span class="follow-user-item__body">
        <strong>{{ user.nickname }}</strong>
        <span>상품 {{ user.productCount.toLocaleString('ko-KR') }} · 팔로워 {{ followerCount.toLocaleString('ko-KR') }}</span>
      </span>

      <span class="follow-user-item__arrow" aria-hidden="true">›</span>
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
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  min-height: 84px;
  gap: var(--space-3);
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
  transition:
    border-color 160ms ease,
    box-shadow 160ms ease;
}

.follow-user-item:hover {
  border-color: var(--color-border-strong);
  box-shadow: 0 4px 12px color-mix(in srgb, var(--color-text-primary) 5%, transparent);
}

.follow-user-item:focus-within {
  border-color: var(--color-border-strong);
}

.follow-user-item__link:focus-visible {
  outline: 3px solid var(--color-primary-soft);
  outline-offset: 3px;
}

.follow-user-item__link {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  min-width: 0;
  gap: var(--space-3);
  color: inherit;
  text-decoration: none;
}

.follow-user-item__body {
  display: grid;
  min-width: 0;
  gap: 2px;
  color: inherit;
  text-decoration: none;
}

.follow-user-item__link:hover .follow-user-item__body strong,
.follow-user-item__link:focus-visible .follow-user-item__body strong {
  color: var(--color-primary);
}

.follow-user-item__body strong {
  overflow: hidden;
  color: var(--color-text-primary);
  font-size: 18px;
  line-height: 26px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.follow-user-item__body span {
  color: var(--color-text-secondary);
  font-size: 14px;
  line-height: 22px;
}

.follow-user-item__arrow {
  color: var(--color-text-muted);
  font-size: 20px;
  line-height: 1;
}

@media (max-width: 520px) {
  .follow-user-item {
    grid-template-columns: minmax(0, 1fr) auto;
    gap: var(--space-3);
    padding: var(--space-4);
  }

  .follow-user-item .follow-button {
    grid-column: 1 / -1;
    justify-self: start;
  }
}
</style>
