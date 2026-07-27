<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { ROUTE_NAMES } from '@/shared/constants/routes'

const route = useRoute()
const router = useRouter()

onMounted(() => {
  void router.replace({
    name: getRedirectRouteName(),
  })
})

const getRedirectRouteName = () =>
  getQueryValue(route.query.from) === 'login'
    ? ROUTE_NAMES.AUTH_SSAFY_LOGIN
    : ROUTE_NAMES.AUTH_SSAFY_SIGNUP

function getQueryValue(value: unknown) {
  if (Array.isArray(value)) {
    return value[0] ? String(value[0]) : ''
  }

  return value ? String(value) : ''
}
</script>

<template>
  <div aria-hidden="true"></div>
</template>
