<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/domains/auth/stores/authStore'
import { getHomeViewData } from '@/domains/home/api/homeViewApi'
import GuestHome from '@/domains/home/components/GuestHome.vue'
import MemberHome from '@/domains/home/components/MemberHome.vue'
import { getPublicProfile } from '@/domains/profile/api/profileApi'
import {
  addWish,
  buildProductCategoryOptions,
  getCategories,
  getProductDetail,
  getProductList,
  removeWish,
} from '@/domains/product/api/productApi'
import { useWishStore } from '@/domains/product/stores/wishStore'
import type {
  HomeLiveCardItem,
  HomePopularHostLive,
  HomeProductCardItem,
  HomeViewData,
} from '@/domains/home/types/homeView.types'
import type { ProductCategoryTabSection } from '@/domains/product/types/productList.types'
import { ROUTE_NAMES, ROUTE_PATHS } from '@/shared/constants/routes'
import DefaultLayout from '@/shared/layouts/DefaultLayout.vue'

const CATEGORY_TAB_PRODUCT_LIMIT = 8

const authStore = useAuthStore()
const router = useRouter()
const wishStore = useWishStore()

authStore.hydrateSession()

const homeData = ref<HomeViewData | null>(null)
const isLoading = ref(true)
const errorMessage = ref('')
const homeComponent = computed(() => (authStore.isAuthenticated ? MemberHome : GuestHome))
const wishedProductIds = computed(() => wishStore.wishedProductIds)
const productGradeLabels = ref<Map<number, string>>(new Map())
const popularHostLive = ref<HomePopularHostLive | null>(null)
const categoryProductTabs = ref<ProductCategoryTabSection[]>([])

const getHomeProducts = (data: HomeViewData) => {
  const productGroups: HomeProductCardItem[][] = [
    data.directSaleProducts,
    data.upcomingAuctionProducts,
    data.recommendedProducts,
  ]

  return productGroups.flat().map((product) => ({
    id: product.id,
    isWished: product.isWished,
  }))
}

const handleToggleWish = async (productId: number) => {
  await authStore.validateStoredSession()

  if (!authStore.isAuthenticated || !authStore.user?.id) {
    void router.push({
      name: ROUTE_NAMES.AUTH_LOGIN,
      query: { redirect: ROUTE_PATHS.HOME },
    })
    return
  }

  const wasWished = wishStore.isProductWished(productId)
  wishStore.setProductWish(productId, !wasWished)

  try {
    if (!wasWished) {
      await addWish(authStore.user.id, productId)
    } else {
      await removeWish(authStore.user.id, productId)
    }
  } catch {
    wishStore.setProductWish(productId, wasWished)
  }
}

const loadProductGradeLabels = async (data: HomeViewData) => {
  const productIds = [...new Set(getHomeProducts(data).map((product) => product.id))]
  const results = await Promise.allSettled(productIds.map((id) => getProductDetail(id)))
  const gradeLabels = new Map<number, string>()

  results.forEach((result, index) => {
    if (result.status === 'fulfilled' && result.value.conditionLabel) {
      gradeLabels.set(productIds[index], result.value.conditionLabel)
    }
  })

  productGradeLabels.value = gradeLabels
}

// 팔로워가 가장 많은 예약 라이브 호스트를 찾는다(홈 배너용). 개별 조회 실패는 무시한다.
const loadPopularHostLive = async (data: HomeViewData) => {
  const scheduledLives: HomeLiveCardItem[] = data.scheduledLives

  if (scheduledLives.length === 0) {
    popularHostLive.value = null
    return
  }

  const hostIds = [...new Set(scheduledLives.map((live) => live.hostId))]
  const results = await Promise.allSettled(hostIds.map((hostId) => getPublicProfile(hostId)))
  const followerCountByHostId = new Map<number, number>()

  results.forEach((result, index) => {
    if (result.status === 'fulfilled') {
      followerCountByHostId.set(hostIds[index], result.value.followerCount)
    }
  })

  const topLive = [...scheduledLives]
    .filter((live) => followerCountByHostId.has(live.hostId))
    .sort(
      (first, second) =>
        (followerCountByHostId.get(second.hostId) ?? 0) -
        (followerCountByHostId.get(first.hostId) ?? 0),
    )[0]

  popularHostLive.value = topLive
    ? { live: topLive, hostFollowerCount: followerCountByHostId.get(topLive.hostId) ?? 0 }
    : null
}

// BE `/home` 응답의 categoryProductSections는 카테고리 트리를 한 단계만 내려가며 상품을 모아
// 항상 빈 배열을 준다(docs/requests/BE/028-home-category-products-empty.md). BE 반영 전까지는
// 상품 목록 페이지와 같은 방식(GET /categories + GET /api/products?categoryIds=...)으로 홈에서
// 직접 채운다.
const loadCategoryProductTabs = async () => {
  try {
    const categories = await getCategories()
    const options = buildProductCategoryOptions(categories)

    const sections = await Promise.all(
      options.map(async (option): Promise<ProductCategoryTabSection> => {
        const { items } = await getProductList({
          categoryIds: option.categoryIds,
          size: CATEGORY_TAB_PRODUCT_LIMIT,
          sort: 'LATEST',
        })

        return { id: String(option.id), title: option.label, products: items }
      }),
    )

    categoryProductTabs.value = sections
    wishStore.hydrateProducts(sections.flatMap((section) => section.products))
  } catch {
    categoryProductTabs.value = []
  }
}

const loadHomeData = async () => {
  isLoading.value = true
  errorMessage.value = ''
  productGradeLabels.value = new Map()
  popularHostLive.value = null
  categoryProductTabs.value = []

  try {
    const nextHomeData = await getHomeViewData({ isAuthenticated: authStore.isAuthenticated })

    homeData.value = nextHomeData
    wishStore.hydrateProducts(getHomeProducts(nextHomeData))
    void loadProductGradeLabels(nextHomeData)
    void loadPopularHostLive(nextHomeData)
    void loadCategoryProductTabs()
  } catch {
    errorMessage.value = '홈 데이터를 불러오지 못했습니다.'
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  void loadHomeData()
})

watch(
  () => authStore.isAuthenticated,
  () => {
    void loadHomeData()
  },
)
</script>

<template>
  <DefaultLayout>
    <section v-if="isLoading" class="home-state" aria-live="polite">
      <p class="home-state__title">홈 페이지 연결 중입니다.</p>
    </section>

    <section v-else-if="errorMessage" class="home-state" aria-live="polite">
      <p class="home-state__title">{{ errorMessage }}</p>
      <button class="home-state__action" type="button" @click="loadHomeData">다시 시도</button>
    </section>

    <component
      v-else-if="homeData"
      :is="homeComponent"
      :home-data="homeData"
      :wished-product-ids="wishedProductIds"
      :product-grade-labels="productGradeLabels"
      :popular-host-live="popularHostLive"
      :category-product-tabs="categoryProductTabs"
      @toggle-wish="handleToggleWish"
    />
  </DefaultLayout>
</template>

<style scoped lang="scss">
.home-state {
  display: grid;
  min-height: 360px;
  place-items: center;
  align-content: center;
  gap: var(--space-4);
  color: var(--color-text-secondary);
  text-align: center;
}

.home-state__title {
  color: var(--color-text-primary);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  line-height: 28px;
}

.home-state__action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: var(--button-height-compact);
  padding: 0 var(--space-5);
  border: 0;
  border-radius: var(--radius-control);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-control);
}
</style>
