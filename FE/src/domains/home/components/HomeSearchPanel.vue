<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import AppSearchBar from '@/shared/components/AppSearchBar.vue'
import { ROUTE_PATHS } from '@/shared/constants/routes'

const searchKeyword = ref('')
const popularKeywords = ['리바이스', '가죽 자켓', '라이브 경매', 'Archive Room']
const router = useRouter()

const moveToSearch = async (keyword: string) => {
  if (!keyword) {
    await router.push(ROUTE_PATHS.SEARCH)
    return
  }

  await router.push({
    path: ROUTE_PATHS.SEARCH,
    query: { keyword },
  })
}
</script>

<template>
  <AppSearchBar
    v-model="searchKeyword"
    search-label="홈 검색"
    placeholder="예: 리바이스 데님 자켓, Archive Room"
    :popular-keywords="popularKeywords"
    @submit="moveToSearch"
    @select-keyword="moveToSearch"
  />
</template>
