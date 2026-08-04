<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { useAuthStore } from '@/domains/auth/stores/authStore'
import { deleteTryOnResult, getMyTryOnResults } from '@/domains/tryon/api/tryOnResultApi'
import TryOnComposer from '@/domains/tryon/components/TryOnComposer.vue'
import TryOnResultGallery from '@/domains/tryon/components/TryOnResultGallery.vue'
import DefaultLayout from '@/shared/layouts/DefaultLayout.vue'

import type { TryOnResult } from '@/domains/tryon/types/tryOnResult.types'

const authStore = useAuthStore()

const results = ref<TryOnResult[]>([])
const loadState = ref<'loading' | 'loaded' | 'error'>('loading')

const getUserId = () => authStore.user?.id ?? null

const loadResults = async () => {
  loadState.value = 'loading'

  try {
    results.value = await getMyTryOnResults(getUserId())
    loadState.value = 'loaded'
  } catch {
    loadState.value = 'error'
  }
}

const handleGenerated = (result: TryOnResult) => {
  results.value = [result, ...results.value]
}

const handleDelete = async (resultId: number) => {
  const previous = results.value
  results.value = results.value.filter((result) => result.id !== resultId)

  try {
    await deleteTryOnResult(getUserId(), resultId)
  } catch {
    results.value = previous
  }
}

onMounted(loadResults)
</script>

<template>
  <DefaultLayout>
    <div class="tryon-page">
      <header class="tryon-page__header">
        <h1>AI 시착</h1>
        <p>등록한 전신 사진에 찜한 옷을 입어보고, 저장된 시착 결과를 카테고리별로 확인하세요.</p>
      </header>

      <TryOnComposer @generated="handleGenerated" />

      <TryOnResultGallery
        :results="results"
        :load-state="loadState"
        @delete="handleDelete"
        @retry="loadResults"
      />
    </div>
  </DefaultLayout>
</template>

<style scoped lang="scss">
.tryon-page {
  padding-bottom: var(--space-10);
}

.tryon-page__header {
  margin-bottom: var(--space-8);
}

.tryon-page__header h1 {
  font-size: 30px;
  font-weight: 700;
  line-height: 40px;
}

.tryon-page__header p {
  margin-top: var(--space-2);
  color: var(--color-text-secondary);
  line-height: 24px;
}
</style>
