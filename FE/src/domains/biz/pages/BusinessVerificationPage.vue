<script setup lang="ts">
import { ref } from 'vue'

import BusinessCertificateUploader from '@/domains/biz/components/BusinessCertificateUploader.vue'

const businessRegistrationNumber = ref('')
const businessName = ref('')
const representativeName = ref('')
const certificateFile = ref<File | null>(null)

const onboardingSteps = [
  { id: 1, label: '기본 정보', state: 'completed' },
  { id: 2, label: '관심 정보', state: 'completed' },
  { id: 3, label: '신체 정보', state: 'completed' },
  { id: 4, label: '회원 유형', state: 'current' },
] as const
</script>

<template>
  <main class="business-verification">
    <section
      class="business-verification__container"
      aria-labelledby="business-verification-title"
    >
      <nav class="business-progress" aria-label="회원 정보 등록 진행 단계">
        <ol class="business-progress__list">
          <li
            v-for="step in onboardingSteps"
            :key="step.id"
            class="business-progress__item"
            :class="`business-progress__item--${step.state}`"
            :aria-current="step.state === 'current' ? 'step' : undefined"
          >
            <span class="business-progress__marker" aria-hidden="true">
              <span v-if="step.state === 'completed'">✓</span>
              <span v-else>{{ step.id }}</span>
            </span>
            <span>{{ step.label }}</span>
          </li>
        </ol>
      </nav>

      <header class="business-verification__header">
        <span class="business-verification__icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" focusable="false">
            <path d="M12 3.5 19 6v5.4c0 4.3-2.6 7.4-7 9.1-4.4-1.7-7-4.8-7-9.1V6l7-2.5Z" />
            <path d="m9 12 2 2 4-4" />
          </svg>
        </span>
        <p class="business-verification__eyebrow">사업자 회원 등록</p>
        <h1 id="business-verification-title">사업자 인증</h1>
        <p>사업자 회원 이용을 위해 정보를 제출해 주세요.</p>
      </header>

      <form class="business-form" @submit.prevent>
        <section class="business-form__section" aria-labelledby="business-details-title">
          <div class="business-form__section-header">
            <div>
              <h2 id="business-details-title">사업자 정보 입력</h2>
              <p>사업자등록증에 기재된 정보와 동일하게 입력해 주세요.</p>
            </div>
            <span>필수 입력</span>
          </div>

          <div class="business-form__fields">
            <label class="business-field business-field--full">
              <span class="business-field__label">사업자등록번호</span>
              <input
                v-model="businessRegistrationNumber"
                type="text"
                inputmode="numeric"
                autocomplete="off"
                placeholder="사업자등록번호를 입력해 주세요"
              />
            </label>

            <label class="business-field">
              <span class="business-field__label">상호명</span>
              <input
                v-model="businessName"
                type="text"
                autocomplete="organization"
                placeholder="상호명을 입력해 주세요"
              />
            </label>

            <label class="business-field">
              <span class="business-field__label">대표자명</span>
              <input
                v-model="representativeName"
                type="text"
                autocomplete="name"
                placeholder="대표자명을 입력해 주세요"
              />
            </label>
          </div>
        </section>

        <section class="business-form__section" aria-labelledby="certificate-title">
          <div class="business-form__section-header">
            <div>
              <h2 id="certificate-title">사업자등록증</h2>
              <p>확인 가능한 사업자등록증 이미지를 등록해 주세요.</p>
            </div>
            <span>필수 등록</span>
          </div>

          <BusinessCertificateUploader v-model="certificateFile" />
        </section>

        <aside class="business-privacy-notice" aria-label="개인정보 이용 안내">
          <span class="business-privacy-notice__icon" aria-hidden="true">i</span>
          <p>
            입력하신 정보는 회원 식별 및 서비스 제공을 위한 용도로만 사용됩니다.
            개인정보 보호 정책에 따라 안전하게 보관되니 안심하고 입력해 주세요.
          </p>
        </aside>

        <button
          type="submit"
          class="business-form__submit"
          disabled
          aria-describedby="business-submit-description"
        >
          사업자 정보 제출
        </button>
        <p id="business-submit-description" class="business-form__submit-description">
          제출 조건과 화면 이동은 다음 입력 제약 작업에서 연결합니다.
        </p>
      </form>
    </section>
  </main>
</template>

<style scoped lang="scss">
.business-verification {
  min-height: 100vh;
  padding: var(--space-12);
  background: var(--color-page);
}

.business-verification__container {
  width: 100%;
  max-width: 880px;
  margin: 0 auto;
}

.business-progress {
  margin-bottom: var(--space-12);
}

.business-progress__list {
  display: grid;
  padding: 0;
  margin: 0;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  list-style: none;
}

.business-progress__item {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--color-text-muted);
  flex-direction: column;
  font-size: 13px;
  line-height: 18px;
  text-align: center;
}

.business-progress__item:not(:last-child)::after {
  position: absolute;
  top: 17px;
  left: calc(50% + 24px);
  width: calc(100% - 48px);
  height: 2px;
  background: var(--color-primary);
  content: '';
}

.business-progress__marker {
  position: relative;
  z-index: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: 1px solid var(--color-primary);
  border-radius: 50%;
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-weight: 600;
}

.business-progress__item--current {
  color: var(--color-primary);
  font-weight: 600;
}

.business-progress__item--current .business-progress__marker {
  background: var(--color-surface);
  color: var(--color-primary);
}

.business-verification__header {
  display: flex;
  align-items: center;
  flex-direction: column;
  text-align: center;
}

.business-verification__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: var(--color-primary-soft);
  color: var(--color-primary);
}

.business-verification__icon svg {
  width: 26px;
  height: 26px;
  fill: none;
  stroke: currentcolor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.8;
}

.business-verification__eyebrow {
  margin-top: var(--space-4);
  color: var(--color-primary);
  font-size: 13px;
  font-weight: 600;
  line-height: 18px;
}

.business-verification__header h1 {
  margin-top: var(--space-2);
  font-size: 36px;
  font-weight: 700;
  line-height: 48px;
}

.business-verification__header > p:last-child {
  margin-top: var(--space-2);
  color: var(--color-text-secondary);
  line-height: 24px;
}

.business-form {
  padding: var(--space-8);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  margin-top: var(--space-10);
  background: var(--color-surface);
}

.business-form__section + .business-form__section {
  padding-top: var(--space-8);
  border-top: 1px solid var(--color-border);
  margin-top: var(--space-8);
}

.business-form__section-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
  margin-bottom: var(--space-6);
}

.business-form__section-header h2 {
  font-size: 20px;
  font-weight: 700;
  line-height: 28px;
}

.business-form__section-header p {
  margin-top: var(--space-1);
  color: var(--color-text-secondary);
  font-size: 13px;
  line-height: 18px;
}

.business-form__section-header > span {
  flex: 0 0 auto;
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-badge);
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-size: 12px;
  font-weight: 600;
  line-height: 16px;
}

.business-form__fields {
  display: grid;
  gap: var(--space-5);
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.business-field {
  display: flex;
  min-width: 0;
  flex-direction: column;
}

.business-field--full {
  grid-column: 1 / -1;
}

.business-field__label {
  margin-bottom: var(--space-2);
  font-size: 14px;
  font-weight: 600;
  line-height: 20px;
}

.business-field input {
  width: 100%;
  height: var(--button-height-standard);
  padding: 0 var(--space-4);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-primary);
  font: inherit;
  font-size: 15px;
  transition:
    border-color 160ms ease,
    box-shadow 160ms ease;
}

.business-field input::placeholder {
  color: var(--color-text-muted);
}

.business-field input:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
  outline: none;
}

.business-privacy-notice {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  margin-top: var(--space-8);
  background: var(--color-surface-secondary);
}

.business-privacy-notice__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border: 1px solid var(--color-text-secondary);
  border-radius: 50%;
  color: var(--color-text-secondary);
  flex: 0 0 auto;
  font-size: 12px;
  font-weight: 700;
}

.business-privacy-notice p {
  color: var(--color-text-secondary);
  font-size: 13px;
  line-height: 20px;
}

.business-form__submit {
  width: 100%;
  height: var(--button-height-major);
  border: 0;
  border-radius: var(--radius-control);
  margin-top: var(--space-6);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font: inherit;
  font-size: 15px;
  font-weight: 600;
}

.business-form__submit:disabled {
  background: var(--color-border-strong);
  color: var(--color-text-muted);
  cursor: not-allowed;
}

.business-form__submit-description {
  margin-top: var(--space-2);
  color: var(--color-text-muted);
  font-size: 12px;
  line-height: 18px;
  text-align: center;
}

@media (max-width: 720px) {
  .business-verification {
    padding: var(--space-8) var(--space-4);
  }

  .business-progress__item {
    font-size: 12px;
  }

  .business-progress__item:not(:last-child)::after {
    left: calc(50% + 20px);
    width: calc(100% - 40px);
  }

  .business-form {
    padding: var(--space-5);
  }

  .business-form__fields {
    grid-template-columns: 1fr;
  }

  .business-field--full {
    grid-column: auto;
  }
}
</style>
