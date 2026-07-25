<script setup lang="ts">
import { useRouter } from 'vue-router'

import OnboardingLayout from '@/layouts/OnboardingLayout.vue'

const router = useRouter()

const handlePrevious = async () => {
  await router.push({ name: 'onboarding-basic-info' })
}
</script>

<template>
  <OnboardingLayout
    :current-step="2"
    title="관심 정보를 설정해 주세요"
    description="관심 브랜드와 카테고리를 선택하는 화면을 준비하고 있습니다."
    next-disabled
    @previous="handlePrevious"
  >
    <div class="interests-placeholder" role="status">
      <strong class="interests-placeholder__title">관심 정보 화면 준비 중</strong>
      <p>
        기본 정보가 저장되어 다음 단계로 이동했습니다. 관심 브랜드와 카테고리 설정은
        ONBOARD-002 구현 작업에서 제공됩니다.
      </p>
    </div>
  </OnboardingLayout>
</template>

<style scoped lang="scss">
.interests-placeholder {
  padding: var(--space-8);
  border: 1px dashed var(--color-border-strong);
  border-radius: var(--radius-control);
  background: var(--color-surface-secondary);
  color: var(--color-text-secondary);
  text-align: center;
}

.interests-placeholder__title {
  display: block;
  margin-bottom: var(--space-3);
  color: var(--color-text-primary);
  font-size: 18px;
}
</style>
