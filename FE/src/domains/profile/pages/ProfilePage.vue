<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '@/domains/auth/stores/authStore'
import { getLiveListViewData } from '@/domains/live/api/liveListApi'
import LiveListCard from '@/domains/live/components/LiveListCard.vue'
import type { LiveBroadcastStatus, LiveListItem } from '@/domains/live/types/liveList.types'
import {
  deleteProfileImage,
  getPublicProfile,
  followUser,
  unfollowUser,
  updateProfileBio,
  uploadProfileImage,
} from '@/domains/profile/api/profileApi'
import FollowButton from '@/domains/profile/components/FollowButton.vue'
import { useFollowStore } from '@/domains/profile/stores/followStore'
import type {
  ProfileImageKind,
  ProfileMutationResult,
  PublicProfile,
} from '@/domains/profile/types/profile.types'
import {
  addWish,
  getProductList,
  getWishProductIds,
  removeWish,
} from '@/domains/product/api/productApi'
import ProductCard from '@/domains/product/components/ProductCard.vue'
import { useWishStore } from '@/domains/product/stores/wishStore'
import type { ProductListItem } from '@/domains/product/types/productList.types'
import { ROUTE_NAMES } from '@/shared/constants/routes'
import DefaultLayout from '@/shared/layouts/DefaultLayout.vue'

type ProfileLoadState = 'loading' | 'success' | 'error' | 'not-found'
type ProfileTabId = 'products' | 'lives'
type ListLoadState = 'idle' | 'loading' | 'success' | 'error'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const followStore = useFollowStore()
const wishStore = useWishStore()

const PROFILE_PAGE_SIZE = 12
const PROFILE_LIVE_FETCH_SIZE = 100
const PROFILE_LIVE_STATUSES: Exclude<LiveBroadcastStatus, 'ENDED'>[] = ['LIVE', 'SCHEDULED']

const profile = ref<PublicProfile | null>(null)
const profileLoadState = ref<ProfileLoadState>('loading')
const profileMessage = ref('')
const activeTab = ref<ProfileTabId>('products')
const productPage = ref(1)
const livePage = ref(1)
const products = ref<ProductListItem[]>([])
const lives = ref<LiveListItem[]>([])
const productTotalPages = ref(1)
const liveTotalPages = ref(1)
const activeLiveTotalCount = ref(0)
const productLoadState = ref<ListLoadState>('idle')
const liveLoadState = ref<ListLoadState>('idle')
const productMessage = ref('')
const liveMessage = ref('')
const isEditPanelOpen = ref(false)
const bioDraft = ref('')
const editMessage = ref('')
const editLoadState = ref<'idle' | 'saving' | 'uploading-profile' | 'uploading-cover' | 'deleting-profile' | 'deleting-cover'>('idle')
const profileImageInput = ref<HTMLInputElement | null>(null)
const coverImageInput = ref<HTMLInputElement | null>(null)
let profileRequestId = 0
let productRequestId = 0
let liveRequestId = 0

const routeUserId = computed(() => {
  if (route.name === ROUTE_NAMES.PROFILE_ME) {
    return authStore.user?.id ?? null
  }

  const userId = Number(route.params.userId)

  return Number.isInteger(userId) && userId > 0 ? userId : null
})

const isSelfProfile = computed(
  () => Boolean(authStore.user?.id && profile.value?.id === authStore.user.id),
)
const followState = computed(() =>
  profile.value
    ? followStore.getFollowState(profile.value.id, {
        followerCount: profile.value.followerCount,
        isFollowing: profile.value.isFollowing,
      })
    : { followerCount: 0, isFollowing: false },
)
const profileDescription = computed(() => profile.value?.description?.trim() ?? '')
const isProfileEditBusy = computed(() => editLoadState.value !== 'idle')
const productEmptyMessage = computed(() =>
  isSelfProfile.value ? '아직 등록한 상품이 없습니다.' : '판매 중인 상품이 없습니다.',
)
const liveEmptyMessage = computed(() =>
  isSelfProfile.value ? '아직 개설한 라이브가 없습니다.' : '등록된 라이브가 없습니다.',
)
const profileLiveCount = computed(() => activeLiveTotalCount.value)
const visibleProductPages = computed(() =>
  Array.from({ length: productTotalPages.value }, (_, index) => index + 1),
)
const visibleLivePages = computed(() =>
  Array.from({ length: liveTotalPages.value }, (_, index) => index + 1),
)

const loadProfile = async () => {
  const requestId = ++profileRequestId

  profile.value = null
  profileLoadState.value = 'loading'
  profileMessage.value = ''
  products.value = []
  lives.value = []

  await authStore.validateStoredSession()

  const userId = routeUserId.value

  if (!userId) {
    profileLoadState.value = route.name === ROUTE_NAMES.PROFILE_ME ? 'error' : 'not-found'
    profileMessage.value =
      route.name === ROUTE_NAMES.PROFILE_ME
        ? '로그인한 뒤 프로필을 확인해 주세요.'
        : '존재하지 않는 사용자입니다.'
    return
  }

  try {
    const nextProfile = await getPublicProfile(userId)

    if (requestId !== profileRequestId) return

    profile.value = nextProfile
    bioDraft.value = nextProfile.description?.trim() ?? ''
    editMessage.value = ''
    followStore.setFollowState(nextProfile.id, {
      followerCount: nextProfile.followerCount,
      isFollowing: nextProfile.isFollowing,
    })
    profileLoadState.value = 'success'
    productPage.value = 1
    livePage.value = 1
    await Promise.all([loadProducts(), loadLives()])
  } catch {
    if (requestId !== profileRequestId) return

    profileLoadState.value = 'not-found'
    profileMessage.value = '프로필을 찾을 수 없습니다.'
  }
}

const applyProfileMutation = (result: ProfileMutationResult) => {
  if (!profile.value) return

  profile.value = {
    ...profile.value,
    nickname: result.nickname,
    profileImageUrl: result.profileImageUrl,
    description: result.description ?? '',
    coverImageUrl: result.coverImageUrl,
  }
  bioDraft.value = result.description?.trim() ?? ''
}

const loadProducts = async () => {
  if (!profile.value) return

  const requestId = ++productRequestId
  productLoadState.value = 'loading'
  productMessage.value = ''

  try {
    const response = await getProductList({
      page: productPage.value,
      sellerId: profile.value.id,
      size: PROFILE_PAGE_SIZE,
    })

    if (requestId !== productRequestId) return

    products.value = response.items
    productTotalPages.value = Math.max(response.meta.totalPages, 1)
    wishStore.hydrateProducts(response.items)
    await hydrateProductWishes(response.items)
    productLoadState.value = 'success'
  } catch {
    if (requestId !== productRequestId) return

    products.value = []
    productTotalPages.value = 1
    productLoadState.value = 'error'
    productMessage.value = '상품 목록을 불러오지 못했습니다.'
  }
}

const hydrateProductWishes = async (visibleProducts: ProductListItem[]) => {
  if (!authStore.isAuthenticated || !authStore.user?.id) {
    wishStore.hydrateProducts(visibleProducts.map((product) => ({ id: product.id, isLiked: false })))
    return
  }

  try {
    const wishedProductIds = new Set(await getWishProductIds(authStore.user.id))
    wishStore.hydrateWishedProductIds([...wishedProductIds])
    wishStore.hydrateProducts(
      visibleProducts.map((product) => ({
        id: product.id,
        isLiked: wishedProductIds.has(product.id),
      })),
    )
  } catch {
    // 찜 목록 보강에 실패해도 공개 프로필 상품 목록은 유지한다.
  }
}

const loadLives = async () => {
  if (!profile.value) return

  const requestId = ++liveRequestId
  liveLoadState.value = 'loading'
  liveMessage.value = ''

  try {
    const allLives = await loadDisplayableLives(profile.value.id)

    if (requestId !== liveRequestId) return

    const startIndex = (livePage.value - 1) * PROFILE_PAGE_SIZE

    activeLiveTotalCount.value = allLives.length
    lives.value = allLives.slice(startIndex, startIndex + PROFILE_PAGE_SIZE)
    liveTotalPages.value = Math.max(Math.ceil(allLives.length / PROFILE_PAGE_SIZE), 1)
    liveLoadState.value = 'success'
  } catch {
    if (requestId !== liveRequestId) return

    lives.value = []
    activeLiveTotalCount.value = 0
    liveTotalPages.value = 1
    liveLoadState.value = 'error'
    liveMessage.value = '라이브 목록을 불러오지 못했습니다.'
  }
}

const loadDisplayableLives = async (hostId: number) => {
  const liveGroups = await Promise.all(
    PROFILE_LIVE_STATUSES.map((status) => loadLivesByStatus(hostId, status)),
  )

  return liveGroups
    .flat()
    .sort((a, b) => new Date(b.broadcastAt).getTime() - new Date(a.broadcastAt).getTime())
}

const loadLivesByStatus = async (
  hostId: number,
  status: Exclude<LiveBroadcastStatus, 'ENDED'>,
) => {
  const firstPage = await getLiveListViewData({
    hostId,
    page: 1,
    size: PROFILE_LIVE_FETCH_SIZE,
    sort: 'LATEST',
    status,
  })

  if (firstPage.totalPages <= 1) {
    return firstPage.items
  }

  const restPages = await Promise.all(
    Array.from({ length: firstPage.totalPages - 1 }, (_, index) =>
      getLiveListViewData({
        hostId,
        page: index + 2,
        size: PROFILE_LIVE_FETCH_SIZE,
        sort: 'LATEST',
        status,
      }),
    ),
  )

  return [firstPage, ...restPages].flatMap((page) => page.items)
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

const toggleProfileFollow = async () => {
  if (!profile.value || isSelfProfile.value || followStore.isPending(profile.value.id)) {
    return
  }

  if (!(await requireAuthenticatedAction())) {
    return
  }

  const userId = profile.value.id
  const previousState = followState.value

  if (previousState.isFollowing && !window.confirm('팔로우를 취소하시겠습니까?')) {
    return
  }

  const nextIsFollowing = !previousState.isFollowing
  const nextFollowerCount = Math.max(
    previousState.followerCount + (nextIsFollowing ? 1 : -1),
    0,
  )

  followStore.setPending(userId, true)
  followStore.setFollowState(userId, {
    followerCount: nextFollowerCount,
    isFollowing: nextIsFollowing,
  })

  try {
    if (previousState.isFollowing) {
      await unfollowUser(userId)
    } else {
      const response = await followUser(userId)
      followStore.setFollowState(userId, {
        followerCount: response.followerCount,
        isFollowing: response.isFollowing,
      })
    }
  } catch {
    followStore.setFollowState(userId, previousState)
    profileMessage.value = '팔로우 상태를 변경하지 못했습니다.'
  } finally {
    followStore.setPending(userId, false)
  }
}

const openProfileEditPanel = () => {
  if (!profile.value || !isSelfProfile.value) return

  bioDraft.value = profile.value.description?.trim() ?? ''
  editMessage.value = ''
  isEditPanelOpen.value = !isEditPanelOpen.value
}

const saveProfileBio = async () => {
  if (!profile.value || !isSelfProfile.value || isProfileEditBusy.value) return

  editLoadState.value = 'saving'
  editMessage.value = ''

  try {
    const result = await updateProfileBio(profile.value.id, bioDraft.value.trim())
    applyProfileMutation(result)
    editMessage.value = '소개글을 저장했습니다.'
  } catch {
    editMessage.value = '소개글을 저장하지 못했습니다.'
  } finally {
    editLoadState.value = 'idle'
  }
}

const chooseProfileImage = (kind: ProfileImageKind) => {
  if (isProfileEditBusy.value) return

  if (kind === 'profile') {
    profileImageInput.value?.click()
    return
  }

  coverImageInput.value?.click()
}

const handleProfileImageChange = async (kind: ProfileImageKind, event: Event) => {
  if (!profile.value || !isSelfProfile.value || isProfileEditBusy.value) return

  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''

  if (!file) return

  if (!file.type.startsWith('image/')) {
    editMessage.value = '이미지 파일만 업로드할 수 있습니다.'
    return
  }

  editLoadState.value = kind === 'profile' ? 'uploading-profile' : 'uploading-cover'
  editMessage.value = ''

  try {
    const result = await uploadProfileImage(profile.value.id, kind, file)
    applyProfileMutation(result)
    editMessage.value = kind === 'profile' ? '프로필 이미지를 저장했습니다.' : '커버 이미지를 저장했습니다.'
  } catch {
    editMessage.value = kind === 'profile' ? '프로필 이미지를 저장하지 못했습니다.' : '커버 이미지를 저장하지 못했습니다.'
  } finally {
    editLoadState.value = 'idle'
  }
}

const removeProfileImage = async (kind: ProfileImageKind) => {
  if (!profile.value || !isSelfProfile.value || isProfileEditBusy.value) return

  editLoadState.value = kind === 'profile' ? 'deleting-profile' : 'deleting-cover'
  editMessage.value = ''

  try {
    await deleteProfileImage(profile.value.id, kind)

    profile.value = {
      ...profile.value,
      profileImageUrl: kind === 'profile' ? null : profile.value.profileImageUrl,
      coverImageUrl: kind === 'cover' ? null : profile.value.coverImageUrl,
    }
    editMessage.value = kind === 'profile' ? '프로필 이미지를 삭제했습니다.' : '커버 이미지를 삭제했습니다.'
  } catch {
    editMessage.value = kind === 'profile' ? '프로필 이미지를 삭제하지 못했습니다.' : '커버 이미지를 삭제하지 못했습니다.'
  } finally {
    editLoadState.value = 'idle'
  }
}

const toggleWish = async (productId: number) => {
  if (!(await requireAuthenticatedAction())) {
    return
  }

  const userId = authStore.user?.id
  if (!userId) return

  const wasLiked = wishStore.isProductWished(productId)
  wishStore.setProductWish(productId, !wasLiked)

  try {
    if (wasLiked) {
      await removeWish(userId, productId)
    } else {
      await addWish(userId, productId)
    }
  } catch {
    wishStore.setProductWish(productId, wasLiked)
  }
}

const selectTab = (tabId: ProfileTabId) => {
  activeTab.value = tabId
  void router.replace({
    query: {
      ...route.query,
      tab: tabId === 'products' ? undefined : tabId,
    },
  })
}

const moveProductPage = (page: number) => {
  if (page < 1 || page > productTotalPages.value || page === productPage.value) return
  productPage.value = page
  void loadProducts()
}

const moveLivePage = (page: number) => {
  if (page < 1 || page > liveTotalPages.value || page === livePage.value) return
  livePage.value = page
  void loadLives()
}

const goToFollowList = (kind: 'followers' | 'following') => {
  if (!profile.value) return

  void router.push({
    name: kind === 'followers' ? ROUTE_NAMES.PROFILE_FOLLOWERS : ROUTE_NAMES.PROFILE_FOLLOWING,
    params: { userId: profile.value.id },
  })
}

watch(
  () => route.query.tab,
  (tab) => {
    activeTab.value = tab === 'lives' ? 'lives' : 'products'
  },
  { immediate: true },
)

watch(
  () => [route.name, route.params.userId, authStore.user?.id],
  () => {
    void loadProfile()
  },
  { immediate: true },
)
</script>

<template>
  <DefaultLayout content-max-width="1200px">
    <section class="profile-page" aria-labelledby="profile-title">
      <div v-if="profileLoadState === 'loading'" class="profile-state" role="status">
        프로필을 불러오는 중입니다.
      </div>

      <div v-else-if="profileLoadState !== 'success' || !profile" class="profile-state" role="alert">
        <strong>{{ profileMessage || '프로필을 불러오지 못했습니다.' }}</strong>
        <button type="button" @click="loadProfile">다시 시도</button>
      </div>

      <template v-else>
        <header class="profile-summary">
          <div v-if="profile.coverImageUrl" class="profile-summary__cover">
            <img :src="profile.coverImageUrl" :alt="`${profile.nickname} 커버 이미지`" />
          </div>

          <div class="profile-summary__top">
            <div class="profile-summary__main">
              <img
                v-if="profile.profileImageUrl"
                class="profile-summary__image"
                :src="profile.profileImageUrl"
                :alt="`${profile.nickname} 프로필 이미지`"
              />
              <div class="profile-summary__identity">
                <h1 id="profile-title">{{ profile.nickname }}</h1>
                <p v-if="profileDescription">{{ profileDescription }}</p>
              </div>
            </div>

            <div class="profile-summary__actions">
              <button
                v-if="isSelfProfile"
                class="profile-summary__edit"
                type="button"
                :aria-expanded="isEditPanelOpen"
                @click="openProfileEditPanel"
              >
                프로필 편집
              </button>
              <FollowButton
                :is-following="followState.isFollowing"
                :is-pending="followStore.isPending(profile.id)"
                :is-self="isSelfProfile"
                @toggle="toggleProfileFollow"
              />
            </div>
          </div>

          <p v-if="profileMessage" class="profile-summary__message" role="status">
            {{ profileMessage }}
          </p>

          <div v-if="isSelfProfile && isEditPanelOpen" class="profile-editor">
            <div class="profile-editor__section">
              <div class="profile-editor__field">
                <label for="profile-bio">소개글</label>
                <textarea
                  id="profile-bio"
                  v-model="bioDraft"
                  maxlength="500"
                  rows="3"
                  :disabled="isProfileEditBusy"
                  placeholder="상점을 소개해 주세요"
                ></textarea>
                <span>{{ bioDraft.length }}/500</span>
              </div>

              <button
                class="profile-editor__button profile-editor__button--primary"
                type="button"
                :disabled="isProfileEditBusy"
                @click="saveProfileBio"
              >
                {{ editLoadState === 'saving' ? '저장 중' : '소개글 저장' }}
              </button>
            </div>

            <div class="profile-editor__section profile-editor__section--media">
              <strong class="profile-editor__section-title">이미지</strong>
              <input
                ref="profileImageInput"
                class="sr-only"
                type="file"
                accept="image/*"
                @change="handleProfileImageChange('profile', $event)"
              />
              <input
                ref="coverImageInput"
                class="sr-only"
                type="file"
                accept="image/*"
                @change="handleProfileImageChange('cover', $event)"
              />

              <div class="profile-editor__media-actions">
                <button
                  class="profile-editor__button"
                  type="button"
                  :disabled="isProfileEditBusy"
                  @click="chooseProfileImage('profile')"
                >
                  {{ editLoadState === 'uploading-profile' ? '업로드 중' : '프로필 이미지 변경' }}
                </button>
                <button
                  class="profile-editor__button"
                  type="button"
                  :disabled="isProfileEditBusy"
                  @click="chooseProfileImage('cover')"
                >
                  {{ editLoadState === 'uploading-cover' ? '업로드 중' : '커버 이미지 변경' }}
                </button>
                <button
                  v-if="profile.profileImageUrl"
                  class="profile-editor__button profile-editor__button--danger"
                  type="button"
                  :disabled="isProfileEditBusy"
                  @click="removeProfileImage('profile')"
                >
                  {{ editLoadState === 'deleting-profile' ? '삭제 중' : '프로필 이미지 삭제' }}
                </button>
                <button
                  v-if="profile.coverImageUrl"
                  class="profile-editor__button profile-editor__button--danger"
                  type="button"
                  :disabled="isProfileEditBusy"
                  @click="removeProfileImage('cover')"
                >
                  {{ editLoadState === 'deleting-cover' ? '삭제 중' : '커버 이미지 삭제' }}
                </button>
              </div>
            </div>

            <p v-if="editMessage" class="profile-editor__message" role="status">
              {{ editMessage }}
            </p>
          </div>

          <div class="profile-stats" aria-label="프로필 통계">
            <button class="profile-stats__item" type="button" @click="goToFollowList('followers')">
              <strong>{{ followState.followerCount.toLocaleString('ko-KR') }}</strong>
              <span>팔로워</span>
            </button>
            <button class="profile-stats__item" type="button" @click="goToFollowList('following')">
              <strong>{{ profile.followingCount.toLocaleString('ko-KR') }}</strong>
              <span>팔로잉</span>
            </button>
            <div class="profile-stats__item" aria-label="상품 수">
              <strong>{{ profile.productCount.toLocaleString('ko-KR') }}</strong>
              <span>상품</span>
            </div>
          </div>
        </header>

        <div class="profile-content-card">
          <div class="profile-tabs" role="tablist" aria-label="프로필 콘텐츠">
            <button
              type="button"
              role="tab"
              :aria-selected="activeTab === 'products'"
              :class="{ 'profile-tabs__item--active': activeTab === 'products' }"
              @click="selectTab('products')"
            >
              상품 {{ profile.productCount.toLocaleString('ko-KR') }}
            </button>
            <button
              type="button"
              role="tab"
              :aria-selected="activeTab === 'lives'"
              :class="{ 'profile-tabs__item--active': activeTab === 'lives' }"
              @click="selectTab('lives')"
            >
              라이브 {{ profileLiveCount.toLocaleString('ko-KR') }}
            </button>
          </div>

          <section v-if="activeTab === 'products'" class="profile-section" aria-label="판매 상품">
            <div v-if="productLoadState === 'loading'" class="profile-state" role="status">
              상품을 불러오는 중입니다.
            </div>
            <div v-else-if="productLoadState === 'error'" class="profile-state" role="alert">
              <strong>{{ productMessage }}</strong>
              <button type="button" @click="loadProducts">다시 시도</button>
            </div>
            <div v-else-if="products.length" class="profile-product-grid">
              <ProductCard
                v-for="product in products"
                :key="product.id"
                :product="product"
                :is-liked="wishStore.isProductWished(product.id, product.isLiked)"
                @toggle-like="toggleWish"
              />
            </div>
            <p v-else class="profile-empty">{{ productEmptyMessage }}</p>

            <nav v-if="productTotalPages > 1" class="profile-pagination" aria-label="상품 페이지">
              <button type="button" :disabled="productPage === 1" @click="moveProductPage(productPage - 1)">
                이전
              </button>
              <button
                v-for="page in visibleProductPages"
                :key="page"
                type="button"
                :class="{ 'profile-pagination__item--active': productPage === page }"
                @click="moveProductPage(page)"
              >
                {{ page }}
              </button>
              <button
                type="button"
                :disabled="productPage >= productTotalPages"
                @click="moveProductPage(productPage + 1)"
              >
                다음
              </button>
            </nav>
          </section>

          <section v-else class="profile-section" aria-label="라이브">
            <div v-if="liveLoadState === 'loading'" class="profile-state" role="status">
              라이브를 불러오는 중입니다.
            </div>
            <div v-else-if="liveLoadState === 'error'" class="profile-state" role="alert">
              <strong>{{ liveMessage }}</strong>
              <button type="button" @click="loadLives">다시 시도</button>
            </div>
            <div v-else-if="lives.length" class="profile-live-grid">
              <LiveListCard v-for="live in lives" :key="live.id" :live="live" />
            </div>
            <p v-else class="profile-empty">{{ liveEmptyMessage }}</p>

            <nav v-if="liveTotalPages > 1" class="profile-pagination" aria-label="라이브 페이지">
              <button type="button" :disabled="livePage === 1" @click="moveLivePage(livePage - 1)">
                이전
              </button>
              <button
                v-for="page in visibleLivePages"
                :key="page"
                type="button"
                :class="{ 'profile-pagination__item--active': livePage === page }"
                @click="moveLivePage(page)"
              >
                {{ page }}
              </button>
              <button type="button" :disabled="livePage >= liveTotalPages" @click="moveLivePage(livePage + 1)">
                다음
              </button>
            </nav>
          </section>
        </div>
      </template>
    </section>
  </DefaultLayout>
</template>

<style scoped lang="scss">
.profile-page {
  display: grid;
  gap: var(--space-5);
  width: 100%;
}

.profile-state,
.profile-empty {
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

.profile-state {
  gap: var(--space-4);
}

.profile-state strong {
  color: var(--color-text-primary);
}

.profile-state button {
  height: var(--button-height-small);
  padding: 0 var(--space-4);
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-control);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-weight: 700;
}

.profile-summary {
  overflow: hidden;
  display: grid;
  gap: var(--space-6);
  padding: var(--space-8);
  border: 1px solid var(--color-border);
  border-radius: 18px;
  background: var(--color-surface);
  box-shadow: none;
}

.profile-summary__cover {
  display: block;
  overflow: hidden;
  aspect-ratio: 5 / 1;
  margin: calc(var(--space-8) * -1) calc(var(--space-8) * -1) 0;
  background: var(--color-surface-secondary);
}

.profile-summary__cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.profile-summary__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-5);
}

.profile-summary__main {
  display: flex;
  align-items: center;
  min-width: 0;
  gap: var(--space-5);
}

.profile-summary__image {
  flex: 0 0 auto;
  width: 88px;
  height: 88px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-media);
  object-fit: cover;
}

.profile-summary__top :deep(.follow-button) {
  min-width: 120px;
  height: 42px;
}

.profile-summary__actions {
  display: flex;
  align-items: center;
  flex: 0 0 auto;
  gap: var(--space-3);
}

.profile-summary__edit {
  min-width: 112px;
  height: 42px;
  padding: 0 var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: 10px;
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-bold);
}

.profile-summary__edit:hover,
.profile-summary__edit:focus-visible {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.profile-summary__identity {
  min-width: 0;
}

.profile-summary__identity h1 {
  overflow-wrap: anywhere;
  color: var(--color-text-primary);
  font-size: 32px;
  font-weight: 900;
  line-height: 42px;
}

.profile-summary__identity p,
.profile-summary__message {
  margin-top: var(--space-2);
  color: var(--color-text-secondary);
  font-size: 14px;
  line-height: 22px;
}

.profile-summary__message {
  color: var(--color-danger);
}

.profile-editor {
  display: grid;
  gap: var(--space-5);
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-media);
  background: var(--color-surface-secondary);
}

.profile-editor__section {
  display: grid;
  gap: var(--space-3);
}

.profile-editor__section--media {
  padding-top: var(--space-4);
  border-top: 1px solid var(--color-border);
}

.profile-editor__section-title {
  color: var(--color-text-primary);
  font-size: 14px;
  font-weight: 800;
  line-height: 20px;
}

.profile-editor__field {
  display: grid;
  gap: var(--space-2);
}

.profile-editor__field label {
  color: var(--color-text-primary);
  font-size: 14px;
  font-weight: 800;
  line-height: 20px;
}

.profile-editor__field textarea {
  width: 100%;
  resize: vertical;
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-primary);
  font: inherit;
  line-height: var(--line-height-body);
}

.profile-editor__field textarea:focus-visible {
  outline: 1px solid var(--color-primary);
  border-color: var(--color-primary);
}

.profile-editor__field span,
.profile-editor__message {
  color: var(--color-text-secondary);
  font-size: var(--font-size-caption);
  line-height: 20px;
}

.profile-editor__media-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.profile-editor__button {
  justify-self: start;
  min-height: 38px;
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-bold);
}

.profile-editor__button--primary {
  border-color: var(--color-primary);
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

.profile-editor__button--danger {
  color: var(--color-danger);
}

.profile-editor__button:hover:not(:disabled),
.profile-editor__button:focus-visible {
  border-color: var(--color-primary);
}

.profile-editor__button--danger:hover:not(:disabled),
.profile-editor__button--danger:focus-visible {
  border-color: var(--color-danger);
}

.profile-editor__button:disabled {
  cursor: wait;
  opacity: 0.7;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  border: 0;
  white-space: nowrap;
}

.profile-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface-secondary);
}

.profile-stats__item {
  display: grid;
  place-items: center;
  min-height: 76px;
  gap: var(--space-1);
  padding: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  color: var(--color-text-primary);
  text-align: center;
}

.profile-stats__item + .profile-stats__item {
  border-left: 1px solid var(--color-border);
}

.profile-stats button.profile-stats__item {
  cursor: pointer;
  transition:
    border-color 160ms ease,
    background-color 160ms ease,
    color 160ms ease;
}

.profile-stats__item strong {
  color: var(--color-text-primary);
  font-size: 22px;
  font-weight: 900;
  line-height: 28px;
}

.profile-stats__item span {
  color: var(--color-text-secondary);
  font-size: 14px;
  font-weight: 700;
  line-height: 20px;
}

.profile-stats button.profile-stats__item:hover,
.profile-stats button.profile-stats__item:focus-visible {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
  color: var(--color-primary);
}

.profile-stats button.profile-stats__item:focus-visible {
  outline: 1px solid var(--color-primary);
  outline-offset: 3px;
}

.profile-content-card {
  display: grid;
  gap: var(--space-5);
  padding: var(--space-6);
  border: 1px solid var(--color-border);
  border-radius: 18px;
  background: var(--color-surface);
}

.profile-tabs {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-media);
  background: var(--color-surface-secondary);
}

.profile-tabs button {
  min-width: 0;
  height: 48px;
  border: 0;
  border-bottom: 3px solid transparent;
  background: transparent;
  color: var(--color-text-secondary);
  font-size: 16px;
  font-weight: 700;
  text-align: center;
  transition:
    background-color 160ms ease,
    border-color 160ms ease,
    color 160ms ease;
}

.profile-tabs button + button {
  border-left: 1px solid var(--color-border);
}

.profile-tabs button:hover {
  background: var(--color-primary-soft);
}

.profile-tabs__item--active {
  border-bottom-color: var(--color-primary) !important;
  background: var(--color-surface) !important;
  color: var(--color-text-primary) !important;
}

.profile-section {
  display: grid;
  gap: var(--space-5);
  min-height: 420px;
}

.profile-product-grid,
.profile-live-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space-5);
}

.profile-live-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.profile-pagination {
  display: flex;
  justify-content: center;
  gap: var(--space-2);
}

.profile-pagination button {
  min-width: 38px;
  height: 38px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-weight: 700;
}

.profile-pagination__item--active {
  border-color: var(--color-primary) !important;
  background: var(--color-primary) !important;
  color: var(--color-text-inverse) !important;
}

.profile-pagination button:disabled {
  color: var(--color-text-muted);
  cursor: not-allowed;
}

@media (max-width: 960px) {
  .profile-product-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .profile-live-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .profile-summary {
    gap: var(--space-5);
    padding: var(--space-5);
    border-radius: var(--radius-media);
  }

  .profile-summary__cover {
    aspect-ratio: 16 / 7;
    margin: calc(var(--space-5) * -1) calc(var(--space-5) * -1) 0;
  }

  .profile-summary__top {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-4);
  }

  .profile-summary__main {
    align-items: flex-start;
    flex-direction: column;
    gap: var(--space-3);
  }

  .profile-summary__image {
    width: 72px;
    height: 72px;
  }

  .profile-summary__actions {
    width: 100%;
    flex-direction: column;
  }

  .profile-summary__edit {
    width: 100%;
  }

  .profile-summary__top :deep(.follow-button) {
    width: 100%;
  }

  .profile-summary__identity h1 {
    font-size: 30px;
    line-height: 38px;
  }

  .profile-stats__item {
    min-height: 78px;
    border-radius: 0;
  }

  .profile-stats__item strong {
    font-size: 20px;
    line-height: 26px;
  }

  .profile-content-card {
    gap: var(--space-5);
    padding: var(--space-4);
    border-radius: var(--radius-media);
  }

  .profile-product-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: var(--space-3);
  }

  .profile-live-grid {
    grid-template-columns: 1fr;
    gap: var(--space-3);
  }
}
</style>
