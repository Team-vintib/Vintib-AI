<script setup lang="ts">
import { useRouter } from 'vue-router'

import OnboardingLayout from '@/domains/onboard/components/OnboardingLayout.vue'
import { ROUTE_NAMES } from '@/shared/constants/routes'

const router = useRouter()

const handlePrevious = async () => {
  await router.push({ name: ROUTE_NAMES.ONBOARD_TRYON })
}
</script>

<template>
  <OnboardingLayout
    :current-step="4"
    title="회원 유형을 선택해 주세요"
    description="일반 회원과 사업자 회원 중 이용할 회원 유형을 선택하는 단계입니다."
    next-disabled
    next-label="다음 작업에서 연결"
    @previous="handlePrevious"
  >
    <section class="member-type-placeholder" aria-labelledby="member-type-placeholder-title">
      <span class="member-type-placeholder__step">ONBOARD-004</span>

      <h2 id="member-type-placeholder-title">회원 유형 화면 준비 중</h2>

      <p>
        현재는 ONBOARD-003의 다음 단계와 건너뛰기 이동을 확인하기 위한 임시 화면입니다.
        일반·사업자 회원 선택과 저장 기능은 ONBOARD-004 작업에서 연결합니다.
      </p>
    </section>
  </OnboardingLayout>
</template>

<style scoped lang="scss">
.member-type-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 320px;
  padding: var(--space-8);
  flex-direction: column;
  text-align: center;
}

.member-type-placeholder__step {
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-chip);
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-size: 12px;
  font-weight: 700;
}

.member-type-placeholder h2 {
  margin-top: var(--space-4);
  font-size: 24px;
  line-height: 34px;
}

.member-type-placeholder p {
  max-width: 560px;
  margin-top: var(--space-3);
  color: var(--color-text-secondary);
  line-height: 24px;
}

@media (max-width: 560px) {
  .member-type-placeholder {
    min-height: 260px;
    padding: var(--space-5);
  }
}
</style>
