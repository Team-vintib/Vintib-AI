<script setup lang="ts">
import SsafySsoStartCard from '@/domains/auth/components/SsafySsoStartCard.vue'
import { ROUTE_PATHS } from '@/shared/constants/routes'
import AuthLayout from '@/shared/layouts/AuthLayout.vue'
</script>

<template>
  <AuthLayout>
    <SsafySsoStartCard
      source="signup"
      title="싸피어스로 가입하기"
      description="SSAFY 계정 인증 후 VinTib 회원가입을 계속합니다."
      primary-label="싸피어스로 가입하기"
      return-label="회원가입 선택으로 돌아가기"
      :return-to="ROUTE_PATHS.AUTH_SIGNUP"
    />
  </AuthLayout>
</template>
