<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import OnboardingLayout from '@/domains/onboard/components/OnboardingLayout.vue'
import { ROUTE_NAMES } from '@/shared/constants/routes'

type MemberType = 'GENERAL' | 'BUSINESS'

interface MemberTypeOption {
  value: MemberType
  badge: string
  title: string
  description: string
  benefits: string[]
}

const memberTypeOptions: MemberTypeOption[] = [
  {
    value: 'GENERAL',
    badge: '일반',
    title: '일반 회원',
    description: '빈티지 의류를 자유롭게 사고팔고 싶은 개인 회원에게 적합합니다.',
    benefits: ['상품 구매와 경매 참여', '일반 판매 활동 이용'],
  },
  {
    value: 'BUSINESS',
    badge: '사업자',
    title: '사업자 회원',
    description: '사업자 인증 후 전문적인 판매 활동을 이어가려는 회원에게 적합합니다.',
    benefits: ['상품 판매와 라이브 진행', '사업자 기능 이용'],
  },
]

const router = useRouter()
const selectedMemberType = ref<MemberType | null>(null)

const handlePrevious = async () => {
  await router.push({ name: ROUTE_NAMES.ONBOARD_TRYON })
}
</script>

<template>
  <OnboardingLayout
    :current-step="4"
    title="회원 유형을 선택해 주세요"
    description="이용 목적에 맞는 회원 유형을 선택해 주세요. 가입 후에도 기본 구매·판매 기능은 동일하게 이용할 수 있습니다."
    :next-disabled="selectedMemberType === null"
    @previous="handlePrevious"
  >
    <section class="member-type-selection" aria-labelledby="member-type-title">
      <header class="member-type-selection__header">
        <div>
          <h2 id="member-type-title" class="member-type-selection__title">
            이용할 회원 유형
          </h2>
          <p id="member-type-hint" class="member-type-selection__description">
            하나의 유형을 선택해 주세요. 사업자 회원은 다음 단계에서 인증 정보를
            등록합니다.
          </p>
        </div>

        <span class="member-type-selection__required">필수 선택</span>
      </header>

      <fieldset class="member-type-group" aria-describedby="member-type-hint member-type-status">
        <legend class="member-type-group__legend">회원 유형 선택</legend>

        <div class="member-type-options">
          <label
            v-for="option in memberTypeOptions"
            :key="option.value"
            class="member-type-option"
            :class="{
              'member-type-option--selected': selectedMemberType === option.value,
            }"
          >
            <input
              v-model="selectedMemberType"
              class="member-type-option__input"
              type="radio"
              name="member-type"
              :value="option.value"
            />

            <span class="member-type-option__top">
              <span class="member-type-option__badge">{{ option.badge }}</span>
              <span class="member-type-option__check" aria-hidden="true">
                {{ selectedMemberType === option.value ? '✓' : '' }}
              </span>
            </span>

            <span class="member-type-option__title">{{ option.title }}</span>
            <span class="member-type-option__description">{{ option.description }}</span>

            <span class="member-type-option__benefits">
              <span
                v-for="benefit in option.benefits"
                :key="benefit"
                class="member-type-option__benefit"
              >
                <span aria-hidden="true">✓</span>
                {{ benefit }}
              </span>
            </span>
          </label>
        </div>
      </fieldset>

      <p id="member-type-status" class="member-type-selection__status" aria-live="polite">
        {{
          selectedMemberType
            ? `${selectedMemberType === 'GENERAL' ? '일반 회원' : '사업자 회원'}을 선택했습니다.`
            : '회원 유형을 선택하면 다음 단계로 진행할 수 있습니다.'
        }}
      </p>
    </section>
  </OnboardingLayout>
</template>

<style scoped lang="scss">
.member-type-selection {
  width: 100%;
}

.member-type-selection__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
  margin-bottom: var(--space-8);
}

.member-type-selection__title {
  font-size: 24px;
  font-weight: 700;
  line-height: 34px;
}

.member-type-selection__description {
  max-width: 680px;
  margin-top: var(--space-2);
  color: var(--color-text-secondary);
}

.member-type-selection__required {
  flex: 0 0 auto;
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-chip);
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-size: 12px;
  font-weight: 600;
  line-height: 20px;
}

.member-type-group {
  min-width: 0;
  padding: 0;
  border: 0;
}

.member-type-group__legend {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  border: 0;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
}

.member-type-options {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-5);
}

.member-type-option {
  display: flex;
  min-height: 300px;
  padding: var(--space-8);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-card);
  flex-direction: column;
  background: var(--color-surface);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition:
    border-color 160ms ease,
    background-color 160ms ease,
    color 160ms ease,
    box-shadow 160ms ease,
    transform 160ms ease;
}

.member-type-option:hover {
  border-color: var(--color-primary);
  transform: translateY(-2px);
}

.member-type-option:has(.member-type-option__input:focus-visible) {
  border-color: var(--color-primary);
  outline: none;
  box-shadow: 0 0 0 3px var(--color-primary-soft);
}

.member-type-option--selected {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
  color: var(--color-primary);
}

.member-type-option__input {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}

.member-type-option__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
}

.member-type-option__badge {
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-chip);
  background: var(--color-surface-secondary);
  color: var(--color-text-secondary);
  font-size: 12px;
  font-weight: 700;
  line-height: 20px;
}

.member-type-option--selected .member-type-option__badge {
  background: var(--color-surface);
  color: var(--color-primary);
}

.member-type-option__check {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: 1px solid var(--color-border-strong);
  border-radius: 50%;
  background: var(--color-surface);
  color: var(--color-text-inverse);
  font-size: 15px;
  font-weight: 700;
}

.member-type-option--selected .member-type-option__check {
  border-color: var(--color-primary);
  background: var(--color-primary);
}

.member-type-option__title {
  margin-top: var(--space-8);
  color: var(--color-text-primary);
  font-size: 24px;
  font-weight: 700;
  line-height: 34px;
}

.member-type-option__description {
  margin-top: var(--space-2);
  line-height: 24px;
}

.member-type-option__benefits {
  display: flex;
  gap: var(--space-3);
  margin-top: auto;
  padding-top: var(--space-8);
  flex-direction: column;
}

.member-type-option__benefit {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--color-text-primary);
  font-weight: 600;
}

.member-type-option__benefit > span {
  color: var(--color-primary);
  font-weight: 700;
}

.member-type-selection__status {
  padding: var(--space-4) var(--space-5);
  border-radius: var(--radius-control);
  margin-top: var(--space-6);
  background: var(--color-surface-secondary);
  color: var(--color-text-secondary);
  font-size: 14px;
  text-align: center;
}

@media (max-width: 820px) {
  .member-type-option {
    min-height: 320px;
    padding: var(--space-6);
  }
}

@media (max-width: 560px) {
  .member-type-selection__header {
    flex-direction: column;
  }

  .member-type-options {
    grid-template-columns: 1fr;
  }

  .member-type-option {
    min-height: 280px;
    padding: var(--space-5);
  }
}
</style>
