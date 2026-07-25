<script setup lang="ts">
import { useRouter } from 'vue-router'

import OnboardingLayout from '@/domains/onboard/components/OnboardingLayout.vue'
import { ROUTE_NAMES } from '@/shared/constants/routes'

const router = useRouter()

const handlePrevious = async () => {
  await router.push({ name: ROUTE_NAMES.ONBOARD_INTERESTS })
}
</script>

<template>
  <OnboardingLayout
    :current-step="3"
    title="AI 시착 정보를 등록해 주세요"
    description="가상 시착에 사용할 전신 사진과 신체 정보를 등록하는 단계입니다."
    next-disabled
    @previous="handlePrevious"
  >
    <section class="try-on-placeholder" aria-labelledby="try-on-placeholder-title">
      <p class="try-on-placeholder__eyebrow">ONBOARD-003</p>
      <h2 id="try-on-placeholder-title" class="try-on-placeholder__title">
        AI 시착 정보 화면 준비 중
      </h2>
      <p class="try-on-placeholder__description">
        관심 정보 저장과 단계 이동을 확인하기 위한 임시 화면입니다. 전신 사진과 신체 정보 등록
        기능은 후속 작업에서 구현합니다.
      </p>
    </section>
  </OnboardingLayout>
</template>

<style scoped lang="scss">
.try-on-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 256px;
  flex-direction: column;
  text-align: center;
}

.try-on-placeholder__eyebrow {
  color: var(--color-primary);
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.try-on-placeholder__title {
  margin-top: var(--space-2);
  font-size: 24px;
  line-height: 34px;
}

.try-on-placeholder__description {
  max-width: 560px;
  margin-top: var(--space-3);
  color: var(--color-text-secondary);
}
</style>
