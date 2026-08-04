<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '@/domains/auth/stores/authStore'
import {
  followUser,
  getFollowers,
  getFollowings,
  getPublicProfile,
  unfollowUser,
} from '@/domains/profile/api/profileApi'
import FollowUserItem from '@/domains/profile/components/FollowUserItem.vue'
import { useFollowStore } from '@/domains/profile/stores/followStore'
import type { FollowListKind, FollowUser, PublicProfile } from '@/domains/profile/types/profile.types'
import { ROUTE_NAMES } from '@/shared/constants/routes'
import DefaultLayout from '@/shared/layouts/DefaultLayout.vue'

type LoadState = 'loading' | 'success' | 'error'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const followStore = useFollowStore()

const PAGE_SIZE = 20
const profile = ref<PublicProfile | null>(null)
const users = ref<FollowUser[]>([])
const loadState = ref<LoadState>('loading')
const errorMessage = ref('')
const selectedPage = ref(1)
const totalPages = ref(1)
let requestId = 0

const userId = computed(() => {
  const id = Number(route.params.userId)

  return Number.isInteger(id) && id > 0 ? id : null
})
const kind = computed<FollowListKind>(() =>
  route.name === ROUTE_NAMES.PROFILE_FOLLOWING ? 'following' : 'followers',
)
const title = computed(() =>
  profile.value ? profile.value.nickname : '',
)
const countLabel = computed(() =>
  profile.value
    ? `${kind.value === 'followers' ? '팔로워' : '팔로잉'} ${
        kind.value === 'followers'
          ? profile.value.followerCount.toLocaleString('ko-KR')
          : profile.value.followingCount.toLocaleString('ko-KR')
      }`
    : '',
)
const emptyMessage = computed(() =>
  kind.value === 'followers' ? '팔로워가 없습니다.' : '팔로잉한 사용자가 없습니다.',
)
const visiblePages = computed(() => Array.from({ length: totalPages.value }, (_, index) => index + 1))

const loadList = async () => {
  const id = userId.value
  const currentRequestId = ++requestId

  loadState.value = 'loading'
  errorMessage.value = ''
  users.value = []

  await authStore.validateStoredSession()

  if (!id) {
    loadState.value = 'error'
    errorMessage.value = '존재하지 않는 사용자입니다.'
    return
  }

  try {
    const [nextProfile, response] = await Promise.all([
      getPublicProfile(id),
      kind.value === 'followers'
        ? getFollowers(id, { page: selectedPage.value, size: PAGE_SIZE })
        : getFollowings(id, { page: selectedPage.value, size: PAGE_SIZE }),
    ])

    if (currentRequestId !== requestId) return

    profile.value = nextProfile
    users.value = response.items
    totalPages.value = Math.max(response.meta.totalPages, 1)
    followStore.setFollowState(nextProfile.id, {
      followerCount: nextProfile.followerCount,
      isFollowing: nextProfile.isFollowing,
    })
    response.items.forEach((user) => {
      followStore.setFollowState(user.id, {
        followerCount: user.followerCount,
        isFollowing: user.isFollowing,
      })
    })
    loadState.value = 'success'
  } catch {
    if (currentRequestId !== requestId) return

    loadState.value = 'error'
    errorMessage.value = '목록을 불러오지 못했습니다.'
  }
}

const requireAuthenticatedAction = async () => {
  await authStore.validateStoredSession()

  if (authStore.isAuthenticated && authStore.user?.id) {
    return true
  }

  await router.push({
    name: ROUTE_NAMES.AUTH_LOGIN,
    query: { redirect: route.fullPath },
  })

  return false
}

const toggleFollow = async (targetUserId: number) => {
  if (authStore.user?.id === targetUserId || followStore.isPending(targetUserId)) {
    return
  }

  if (!(await requireAuthenticatedAction())) {
    return
  }

  const targetUser = users.value.find((user) => user.id === targetUserId)
  const previousState = followStore.getFollowState(targetUserId, {
    followerCount: targetUser?.followerCount ?? 0,
    isFollowing: targetUser?.isFollowing ?? false,
  })

  if (previousState.isFollowing && !window.confirm('팔로우를 취소하시겠습니까?')) {
    return
  }

  const nextIsFollowing = !previousState.isFollowing
  const nextFollowerCount = Math.max(
    previousState.followerCount + (nextIsFollowing ? 1 : -1),
    0,
  )

  followStore.setPending(targetUserId, true)
  followStore.setFollowState(targetUserId, {
    followerCount: nextFollowerCount,
    isFollowing: nextIsFollowing,
  })

  try {
    if (previousState.isFollowing) {
      await unfollowUser(targetUserId)
    } else {
      const response = await followUser(targetUserId)
      followStore.setFollowState(targetUserId, {
        followerCount: response.followerCount,
        isFollowing: response.isFollowing,
      })
    }

    if (profile.value?.id === targetUserId) {
      profile.value = {
        ...profile.value,
        followerCount: followStore.getFollowState(targetUserId, previousState).followerCount,
        isFollowing: followStore.getFollowState(targetUserId, previousState).isFollowing,
      }
    }
  } catch {
    followStore.setFollowState(targetUserId, previousState)
    errorMessage.value = '팔로우 상태를 변경하지 못했습니다.'
  } finally {
    followStore.setPending(targetUserId, false)
  }
}

const getFollowerCount = (user: FollowUser) =>
  followStore.getFollowState(user.id, {
    followerCount: user.followerCount,
    isFollowing: user.isFollowing,
  }).followerCount

const getIsFollowing = (user: FollowUser) =>
  followStore.getFollowState(user.id, {
    followerCount: user.followerCount,
    isFollowing: user.isFollowing,
  }).isFollowing

const moveToPage = (page: number) => {
  if (page < 1 || page > totalPages.value || page === selectedPage.value) return
  selectedPage.value = page
  void loadList()
}

const goToProfile = () => {
  if (!profile.value) return
  void router.push({ name: ROUTE_NAMES.PROFILE, params: { userId: profile.value.id } })
}

watch(
  () => [route.name, route.params.userId],
  () => {
    selectedPage.value = 1
    void loadList()
  },
  { immediate: true },
)
</script>

<template>
  <DefaultLayout content-max-width="960px">
    <section class="follow-list-page" aria-labelledby="follow-list-title">
      <header class="follow-list-page__header">
        <button class="follow-list-page__back" type="button" @click="goToProfile">
          <span aria-hidden="true">←</span>
          <span id="follow-list-title">{{ title || '프로필' }}</span>
        </button>
        <p>{{ countLabel || '팔로우 목록' }}</p>
      </header>

      <div v-if="loadState === 'loading'" class="follow-list-page__state" role="status">
        목록을 불러오는 중입니다.
      </div>

      <div v-else-if="loadState === 'error'" class="follow-list-page__state" role="alert">
        <strong>{{ errorMessage }}</strong>
        <button type="button" @click="loadList">다시 시도</button>
      </div>

      <div v-else-if="users.length" class="follow-list-page__list">
        <FollowUserItem
          v-for="user in users"
          :key="user.id"
          :user="user"
          :follower-count="getFollowerCount(user)"
          :is-following="getIsFollowing(user)"
          :is-pending="followStore.isPending(user.id)"
          :is-self="authStore.user?.id === user.id"
          @toggle-follow="toggleFollow"
        />
      </div>

      <p v-else class="follow-list-page__state">{{ emptyMessage }}</p>

      <nav v-if="totalPages > 1" class="follow-list-page__pagination" aria-label="팔로우 목록 페이지">
        <button type="button" :disabled="selectedPage === 1" @click="moveToPage(selectedPage - 1)">
          이전
        </button>
        <button
          v-for="page in visiblePages"
          :key="page"
          type="button"
          :class="{ 'follow-list-page__page--active': selectedPage === page }"
          @click="moveToPage(page)"
        >
          {{ page }}
        </button>
        <button type="button" :disabled="selectedPage >= totalPages" @click="moveToPage(selectedPage + 1)">
          다음
        </button>
      </nav>
    </section>
  </DefaultLayout>
</template>

<style scoped lang="scss">
.follow-list-page {
  display: grid;
  gap: var(--space-5);
  width: 100%;
  max-width: 1040px;
  margin-inline: auto;
}

.follow-list-page__header {
  display: grid;
  gap: var(--space-2);
  padding: var(--space-8) 0 var(--space-5);
  border-bottom: 1px solid var(--color-border);
}

.follow-list-page__back {
  display: inline-flex;
  align-items: center;
  justify-self: start;
  gap: var(--space-2);
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--color-text-primary);
  font-size: 30px;
  font-weight: 900;
  line-height: 38px;
  text-align: left;
}

.follow-list-page__back span:first-child {
  font-size: 24px;
  line-height: 1;
}

.follow-list-page__back:hover,
.follow-list-page__back:focus-visible {
  color: var(--color-primary);
  text-decoration: underline;
}

.follow-list-page__back:focus-visible {
  outline: 1px solid var(--color-primary);
  outline-offset: 3px;
}

.follow-list-page__header p {
  color: var(--color-text-secondary);
  padding-left: var(--space-8);
  font-size: 16px;
  font-weight: 700;
  line-height: 24px;
}

.follow-list-page__list {
  display: grid;
  gap: var(--space-3);
  border-top: 0;
}

.follow-list-page__state {
  display: grid;
  place-items: center;
  min-height: 220px;
  padding: var(--space-8);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  text-align: center;
}

.follow-list-page__state button {
  height: var(--button-height-small);
  margin-top: var(--space-4);
  padding: 0 var(--space-4);
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-control);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-weight: 700;
}

.follow-list-page__pagination {
  display: flex;
  justify-content: center;
  gap: var(--space-2);
}

.follow-list-page__pagination button {
  min-width: 38px;
  height: 38px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-weight: 700;
}

.follow-list-page__page--active {
  border-color: var(--color-primary) !important;
  background: var(--color-primary) !important;
  color: var(--color-text-inverse) !important;
}

@media (max-width: 640px) {
  .follow-list-page__header {
    padding: var(--space-6) 0 var(--space-4);
  }

  .follow-list-page__back {
    font-size: 28px;
    line-height: 36px;
  }

  .follow-list-page__header p {
    padding-left: calc(var(--space-6) + var(--space-1));
  }
}
</style>
