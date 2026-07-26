<script setup lang="ts">
import { computed } from 'vue'

import SsafySsoStartCard from '@/domains/auth/components/SsafySsoStartCard.vue'
import { ROUTE_PATHS } from '@/shared/constants/routes'
import AuthLayout from '@/shared/layouts/AuthLayout.vue'

const props = defineProps<{
  source?: 'login' | 'signup'
}>()

const ssoSource = computed(() => (props.source === 'login' ? 'login' : 'signup'))
const isLoginSource = computed(() => ssoSource.value === 'login')
</script>

<template>
  <AuthLayout>
    <SsafySsoStartCard
      :source="ssoSource"
      :title="isLoginSource ? '싸피어스로 로그인' : '싸피어스로 가입하기'"
      :description="
        isLoginSource
          ? 'SSAFY 계정 인증 후 VinTib 로그인을 계속합니다.'
          : 'SSAFY 계정 인증 후 VinTib 회원가입을 계속합니다.'
      "
      :primary-label="isLoginSource ? '싸피어스로 로그인' : '싸피어스로 가입하기'"
      :return-label="isLoginSource ? '로그인으로 돌아가기' : '회원가입 선택으로 돌아가기'"
      :return-to="isLoginSource ? ROUTE_PATHS.AUTH_LOGIN : ROUTE_PATHS.AUTH_SIGNUP"
    />
  </AuthLayout>
</template>
