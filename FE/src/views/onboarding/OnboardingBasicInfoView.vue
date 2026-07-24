<script setup lang="ts">
import OnboardingLayout from '@/layouts/OnboardingLayout.vue'
</script>

<template>
  <OnboardingLayout
    :current-step="1"
    title="기본 정보를 입력해 주세요"
    description="원활한 서비스 이용을 위해 기본 회원 정보를 등록해 주세요."
    :previous-disabled="true"
  >
    <section
      class="basic-info-intro"
      aria-labelledby="basic-info-section-title"
    >
      <h2 id="basic-info-section-title" class="basic-info-intro__title">
        기본 정보
      </h2>

      <p class="basic-info-intro__description">
        닉네임, 성별, 전화번호와 주소를 입력하는 단계입니다.
      </p>

      <div class="basic-info-intro__notice" role="note">
        <strong class="basic-info-intro__notice-title">입력 안내</strong>

        <p class="basic-info-intro__notice-description">
          각 항목을 확인하고 정확한 정보를 입력해 주세요.
        </p>
      </div>
    </section>
  </OnboardingLayout>
</template>

<style scoped lang="scss">
.basic-info-intro {
  max-width: 720px;
}

.basic-info-intro__title {
  font-size: 24px;
  font-weight: 700;
  line-height: 34px;
}

.basic-info-intro__description {
  margin-top: var(--space-2);
  color: var(--color-text-secondary);
}

.basic-info-intro__notice {
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  margin-top: var(--space-8);
  background: var(--color-surface-secondary);
}

.basic-info-intro__notice-title {
  color: var(--color-primary);
  font-size: 14px;
}

.basic-info-intro__notice-description {
  margin-top: var(--space-1);
  color: var(--color-text-secondary);
  font-size: 14px;
}
</style>
