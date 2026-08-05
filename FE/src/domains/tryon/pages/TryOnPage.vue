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
    <section class="tryon-page" aria-label="AI 시착">
      <TryOnComposer @generated="handleGenerated" />

      <TryOnResultGallery
        :results="results"
        :load-state="loadState"
        @delete="handleDelete"
        @retry="loadResults"
      />
    </section>
  </DefaultLayout>
</template>

<style scoped lang="scss">
.tryon-page {
  padding-bottom: var(--space-10);
}

</style>
