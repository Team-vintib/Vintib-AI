import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

interface FollowState {
  followerCount: number
  isFollowing: boolean
}

export const useFollowStore = defineStore('follow', () => {
  const states = ref(new Map<number, FollowState>())
  const pendingUserIds = ref(new Set<number>())

  const setFollowState = (
    userId: number,
    state: Partial<FollowState> & Pick<FollowState, 'isFollowing'>,
  ) => {
    const nextStates = new Map(states.value)
    const previous = nextStates.get(userId)

    nextStates.set(userId, {
      followerCount: state.followerCount ?? previous?.followerCount ?? 0,
      isFollowing: state.isFollowing,
    })
    states.value = nextStates
  }

  const getFollowState = (userId: number, fallback: FollowState): FollowState => ({
    followerCount: states.value.get(userId)?.followerCount ?? fallback.followerCount,
    isFollowing: states.value.get(userId)?.isFollowing ?? fallback.isFollowing,
  })

  const setPending = (userId: number, pending: boolean) => {
    const nextPendingUserIds = new Set(pendingUserIds.value)

    if (pending) {
      nextPendingUserIds.add(userId)
    } else {
      nextPendingUserIds.delete(userId)
    }

    pendingUserIds.value = nextPendingUserIds
  }

  const isPending = (userId: number) => pendingUserIds.value.has(userId)
  const pendingCount = computed(() => pendingUserIds.value.size)

  return {
    pendingCount,
    getFollowState,
    isPending,
    setFollowState,
    setPending,
  }
})

