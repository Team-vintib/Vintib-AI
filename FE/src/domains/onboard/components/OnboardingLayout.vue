<script setup lang="ts">
import BaseButton from '@/domains/onboard/components/BaseButton.vue'
import OnboardingStepIndicator from '@/domains/onboard/components/OnboardingStepIndicator.vue'

interface Props {
  currentStep: number
  title: string
  description: string
  previousDisabled?: boolean
  showSkip?: boolean
  skipDisabled?: boolean
  skipLabel?: string
  nextDisabled?: boolean
  nextLabel?: string
}

const {
  currentStep,
  title,
  description,
  previousDisabled = false,
  showSkip = false,
  skipDisabled = false,
  skipLabel = '건너뛰기',
  nextDisabled = false,
  nextLabel = '다음 단계',
} = defineProps<Props>()

const emit = defineEmits<{
  previous: []
  skip: []
  next: []
}>()

const onboardingSteps = [
  { id: 1, label: '기본 정보' },
  { id: 2, label: '관심 정보' },
  { id: 3, label: 'AI 시착 정보' },
  { id: 4, label: '회원 유형' },
]
</script>

<template>
  <main class="onboarding-layout">
    <section class="onboarding-layout__container" aria-labelledby="onboarding-title">
      <header class="onboarding-layout__header">
        <p class="onboarding-layout__eyebrow">회원 정보 등록</p>

        <h1 id="onboarding-title" class="onboarding-layout__title">
          {{ title }}
        </h1>

        <p class="onboarding-layout__description">
          {{ description }}
        </p>
      </header>

      <OnboardingStepIndicator :steps="onboardingSteps" :current-step="currentStep" />

      <div class="onboarding-layout__content">
        <slot />
      </div>

      <footer class="onboarding-layout__actions">
        <BaseButton
          class="onboarding-layout__action"
          variant="secondary"
          size="major"
          :disabled="previousDisabled"
          @click="emit('previous')"
        >
          이전 단계
        </BaseButton>

        <div class="onboarding-layout__action-group">
          <BaseButton
            v-if="showSkip"
            class="onboarding-layout__action"
            variant="secondary"
            size="major"
            :disabled="skipDisabled"
            @click="emit('skip')"
          >
            {{ skipLabel }}
          </BaseButton>

          <BaseButton
            class="onboarding-layout__action"
            size="major"
            :disabled="nextDisabled"
            @click="emit('next')"
          >
            {{ nextLabel }}
          </BaseButton>
        </div>
      </footer>
    </section>
  </main>
</template>

<style scoped lang="scss">
.onboarding-layout {
  min-height: 100vh;
  padding: var(--space-16) var(--space-12);
  background: var(--color-page);
}

.onboarding-layout__container {
  width: 100%;
  max-width: var(--layout-content-max-width);
  margin: 0 auto;
}

.onboarding-layout__header {
  max-width: 720px;
  margin-bottom: var(--space-10);
}

.onboarding-layout__eyebrow {
  margin-bottom: var(--space-2);
  color: var(--color-primary);
  font-size: 13px;
  font-weight: 600;
  line-height: 18px;
}

.onboarding-layout__title {
  font-size: 36px;
  font-weight: 700;
  line-height: 48px;
}

.onboarding-layout__description {
  margin-top: var(--space-3);
  color: var(--color-text-secondary);
  line-height: 24px;
}

.onboarding-layout__content {
  min-height: 320px;
  padding: var(--space-8);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  margin-top: var(--space-12);
  background: var(--color-surface);
}

.onboarding-layout__actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  margin-top: var(--space-6);
}

.onboarding-layout__action-group {
  display: flex;
  gap: var(--space-4);
}

.onboarding-layout__action {
  min-width: 160px;
}

@media (max-width: 560px) {
  .onboarding-layout {
    padding: var(--space-10) var(--space-4);
  }

  .onboarding-layout__content {
    padding: var(--space-5);
  }

  .onboarding-layout__actions,
  .onboarding-layout__action-group {
    align-items: stretch;
    flex-direction: column;
  }

  .onboarding-layout__action-group {
    width: 100%;
  }

  .onboarding-layout__action {
    width: 100%;
  }
}
</style>
