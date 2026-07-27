<script setup lang="ts">
import SsafySsoStartCard from '@/domains/auth/components/SsafySsoStartCard.vue'
import { ROUTE_PATHS } from '@/shared/constants/routes'
import AuthLayout from '@/shared/layouts/AuthLayout.vue'
</script>

<template>
  <AuthLayout>
    <SsafySsoStartCard
      source="login"
      title="싸피어스로 로그인"
      description="SSAFY 계정 인증 후 VinTib 로그인을 계속합니다."
      primary-label="싸피어스로 로그인"
      return-label="로그인으로 돌아가기"
      :return-to="ROUTE_PATHS.AUTH_LOGIN"
    />
  </AuthLayout>
</template>
