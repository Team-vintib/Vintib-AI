<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/domains/auth/stores/authStore'
import { getHomeViewData } from '@/domains/home/api/homeViewApi'
import GuestHome from '@/domains/home/components/GuestHome.vue'
import MemberHome from '@/domains/home/components/MemberHome.vue'
import type { HomeProductCardItem, HomeViewData } from '@/domains/home/types/homeView.types'
import { ROUTE_NAMES, ROUTE_PATHS } from '@/shared/constants/routes'
import DefaultLayout from '@/shared/layouts/DefaultLayout.vue'

const authStore = useAuthStore()
const router = useRouter()

authStore.hydrateSession()

const homeData = ref<HomeViewData | null>(null)
const wishedProductIds = ref(new Set<number>())
const isLoading = ref(true)
const errorMessage = ref('')
const homeComponent = computed(() => (authStore.isAuthenticated ? MemberHome : GuestHome))

const getInitialWishedProductIds = (data: HomeViewData) => {
  const productGroups: HomeProductCardItem[][] = [
    data.directSaleProducts,
    data.upcomingAuctionProducts,
    data.recommendedProducts,
    ...data.categoryProductSections.map((section) => section.products),
  ]

  return new Set(
    productGroups.flat().filter((product) => product.isWished).map((product) => product.id),
  )
}

const handleToggleWish = (productId: number) => {
  if (!authStore.isAuthenticated) {
    void router.push({
      name: ROUTE_NAMES.AUTH_LOGIN,
      query: { redirect: ROUTE_PATHS.HOME },
    })
    return
  }

  const nextWishedProductIds = new Set(wishedProductIds.value)

  if (nextWishedProductIds.has(productId)) {
    nextWishedProductIds.delete(productId)
  } else {
    nextWishedProductIds.add(productId)
  }

  wishedProductIds.value = nextWishedProductIds
}

const loadHomeData = async () => {
  isLoading.value = true
  errorMessage.value = ''

  try {
    const nextHomeData = await getHomeViewData({ isAuthenticated: authStore.isAuthenticated })

    homeData.value = nextHomeData
    wishedProductIds.value = getInitialWishedProductIds(nextHomeData)
  } catch {
    errorMessage.value = '홈 데이터를 불러오지 못했습니다.'
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  void loadHomeData()
})
</script>

<template>
  <DefaultLayout content-max-width="1200px">
    <section v-if="isLoading" class="home-state" aria-live="polite">
      <p class="home-state__title">홈 데이터를 불러오는 중입니다.</p>
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
  font-size: 18px;
  font-weight: 700;
  line-height: 28px;
}

.home-state__action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 44px;
  padding: 0 var(--space-5);
  border: 0;
  border-radius: var(--radius-control);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-size: 14px;
  font-weight: 700;
  line-height: 20px;
}
</style>
