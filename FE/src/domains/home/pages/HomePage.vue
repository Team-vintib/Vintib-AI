<script setup lang="ts">
import { computed } from 'vue'

import { useAuthStore } from '@/domains/auth/stores/authStore'
import GuestHome from '@/domains/home/components/GuestHome.vue'
import MemberHome from '@/domains/home/components/MemberHome.vue'
import DefaultLayout from '@/shared/layouts/DefaultLayout.vue'

const authStore = useAuthStore()

authStore.hydrateSession()

const homeComponent = computed(() => (authStore.isAuthenticated ? MemberHome : GuestHome))
</script>

<template>
  <DefaultLayout content-max-width="1200px">
    <component :is="homeComponent" />
  </DefaultLayout>
</template>
