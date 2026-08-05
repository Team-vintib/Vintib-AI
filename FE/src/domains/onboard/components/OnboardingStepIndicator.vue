<script setup lang="ts">
interface OnboardingStep {
  id: number
  label: string
}

interface Props {
  steps: OnboardingStep[]
  currentStep: number
}

type StepState = 'completed' | 'current' | 'upcoming'

const props = defineProps<Props>()

const getStepState = (stepId: number): StepState => {
  if (stepId < props.currentStep) {
    return 'completed'
  }

  if (stepId === props.currentStep) {
    return 'current'
  }

  return 'upcoming'
}

const getStateText = (stepId: number) => {
  const state = getStepState(stepId)

  if (state === 'completed') {
    return '완료된 단계'
  }

  if (state === 'current') {
    return '현재 단계'
  }

  return '미완료 단계'
}
</script>

<template>
  <nav class="step-indicator" aria-label="온보딩 진행 단계">
    <ol
      class="step-indicator__list"
      :style="{ '--step-count': steps.length }"
    >
      <li
        v-for="step in steps"
        :key="step.id"
        class="step-indicator__item"
        :class="`step-indicator__item--${getStepState(step.id)}`"
        :aria-current="step.id === currentStep ? 'step' : undefined"
      >
        <span class="step-indicator__marker" aria-hidden="true">
          <span v-if="getStepState(step.id) === 'completed'">✓</span>
          <span v-else>{{ step.id }}</span>
        </span>

        <span class="step-indicator__label">{{ step.label }}</span>
        <span class="step-indicator__state">{{ getStateText(step.id) }}</span>
      </li>
    </ol>
  </nav>
</template>

<style scoped lang="scss">
.step-indicator {
  width: 100%;
}

.step-indicator__list {
  display: grid;
  grid-template-columns: repeat(var(--step-count), minmax(0, 1fr));
  list-style: none;
}

.step-indicator__item {
  position: relative;
  display: flex;
  align-items: center;
  flex-direction: column;
  gap: var(--space-2);
  color: var(--color-text-muted);
  text-align: center;
}

.step-indicator__item:not(:last-child)::after {
  position: absolute;
  top: 17px;
  left: calc(50% + 24px);
  width: calc(100% - 48px);
  height: 2px;
  background: var(--color-border);
  content: '';
}

.step-indicator__item--completed:not(:last-child)::after {
  background: var(--color-primary);
}

.step-indicator__marker {
  position: relative;
  z-index: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border: 1px solid var(--color-border-input);
  border-radius: var(--radius-badge);
  background: var(--color-surface);
  color: var(--color-text-muted);
  font-family: var(--font-mono);
  font-size: 13px;
  font-weight: 500;
}

.step-indicator__item--completed .step-indicator__marker,
.step-indicator__item--current .step-indicator__marker {
  border-color: var(--color-primary);
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

.step-indicator__item--current .step-indicator__label {
  color: var(--color-primary);
  font-weight: 600;
}

.step-indicator__label {
  font-size: 13px;
  line-height: 18px;
}

.step-indicator__state {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  overflow: hidden;
  border: 0;
  margin: -1px;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
}
</style>
