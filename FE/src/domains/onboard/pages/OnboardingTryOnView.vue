<script setup lang="ts">
import { useRouter } from 'vue-router'

import BaseButton from '@/domains/onboard/components/BaseButton.vue'
import OnboardingLayout from '@/domains/onboard/components/OnboardingLayout.vue'
import { ROUTE_NAMES } from '@/shared/constants/routes'

interface BodyField {
  id: string
  label: string
  unit?: string
}

const bodyFields: BodyField[] = [
  { id: 'height', label: '키', unit: 'cm' },
  { id: 'weight', label: '몸무게', unit: 'kg' },
  { id: 'chest', label: '가슴' },
  { id: 'waist', label: '허리' },
  { id: 'hip', label: '엉덩이' },
]

const router = useRouter()

const handlePrevious = async () => {
  await router.push({ name: ROUTE_NAMES.ONBOARD_INTERESTS })
}
</script>

<template>
  <OnboardingLayout
    :current-step="3"
    title="AI 시착 정보를 등록해 주세요"
    description="전신 사진과 신체 정보를 등록하면 더 정확한 가상 시착 결과를 확인할 수 있습니다."
    show-skip
    skip-disabled
    next-disabled
    @previous="handlePrevious"
  >
    <div class="try-on-registration">
      <header class="try-on-registration__header">
        <div>
          <h2 class="try-on-registration__title">AI 시착 정보</h2>
          <p class="try-on-registration__description">
            모든 항목은 선택 사항이며 가입 후 마이페이지에서 변경할 수 있습니다.
          </p>
        </div>

        <span class="try-on-registration__optional">선택 사항</span>
      </header>

      <section class="registration-section" aria-labelledby="full-body-photo-title">
        <div class="registration-section__heading">
          <div>
            <h3 id="full-body-photo-title" class="registration-section__title">전신 사진</h3>
            <p class="registration-section__description">
              AI 시착에 사용할 정면 전신 사진을 등록해 주세요.
            </p>
          </div>

          <span class="registration-section__status">등록 전</span>
        </div>

        <div class="photo-registration">
          <div class="photo-registration__empty" role="status">
            <span class="photo-registration__icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" focusable="false">
                <path
                  d="M4 5.75A1.75 1.75 0 0 1 5.75 4h12.5A1.75 1.75 0 0 1 20 5.75v12.5A1.75 1.75 0 0 1 18.25 20H5.75A1.75 1.75 0 0 1 4 18.25V5.75Z"
                />
                <path d="m6.5 17 3.2-3.8 2.25 2.35 1.85-2.15L17.5 17" />
                <circle cx="15.75" cy="8.25" r="1.25" />
              </svg>
            </span>

            <strong>등록된 전신 사진이 없습니다.</strong>
            <p>사진 등록 기능은 다음 작업에서 연결됩니다.</p>

            <div class="photo-registration__actions" aria-label="전신 사진 등록 방법">
              <BaseButton variant="secondary" disabled>
                <svg class="photo-registration__button-icon" viewBox="0 0 24 24" aria-hidden="true">
                  <path
                    d="M12 16V4m0 0L7.5 8.5M12 4l4.5 4.5M5 14v4.25A1.75 1.75 0 0 0 6.75 20h10.5A1.75 1.75 0 0 0 19 18.25V14"
                  />
                </svg>
                사진 등록
              </BaseButton>

              <BaseButton variant="secondary" disabled>
                <svg class="photo-registration__button-icon" viewBox="0 0 24 24" aria-hidden="true">
                  <path
                    d="M4 8.75A1.75 1.75 0 0 1 5.75 7h2l1.1-2h6.3l1.1 2h2A1.75 1.75 0 0 1 20 8.75v8.5A1.75 1.75 0 0 1 18.25 19H5.75A1.75 1.75 0 0 1 4 17.25v-8.5Z"
                  />
                  <circle cx="12" cy="13" r="3.25" />
                </svg>
                즉시 촬영
              </BaseButton>
            </div>
          </div>

          <aside class="photo-guide" aria-labelledby="photo-guide-title">
            <div class="photo-guide__heading">
              <span class="photo-guide__icon" aria-hidden="true">i</span>
              <h4 id="photo-guide-title">사진 촬영 가이드</h4>
            </div>

            <ul class="photo-guide__list">
              <li>머리부터 발끝까지 전신이 모두 보이도록 촬영해 주세요.</li>
              <li>카메라 정면을 바라보고 몸을 바르게 세워 주세요.</li>
              <li>몸의 형태가 잘 보이는 옷을 착용하는 것을 권장합니다.</li>
            </ul>

            <p class="photo-guide__notice">전신 사진이 없으면 AI 시착 기능을 이용할 수 없습니다.</p>
          </aside>
        </div>
      </section>

      <section
        class="registration-section registration-section--measurements"
        aria-labelledby="body-measurements-title"
      >
        <div class="registration-section__heading">
          <div>
            <h3 id="body-measurements-title" class="registration-section__title">신체 정보</h3>
            <p id="body-measurements-status" class="registration-section__description">
              실제 치수에 가까운 정보를 입력할수록 시착 결과의 정확도가 높아집니다.
            </p>
          </div>

          <span class="registration-section__status">선택 입력</span>
        </div>

        <fieldset class="body-fields" aria-describedby="body-measurements-status" disabled>
          <legend class="visually-hidden">신체 정보 입력 항목</legend>

          <div v-for="field in bodyFields" :key="field.id" class="body-field">
            <label class="body-field__label" :for="field.id">{{ field.label }}</label>

            <div class="body-field__control">
              <input
                :id="field.id"
                class="body-field__input"
                type="text"
                inputmode="decimal"
                placeholder="입력 예정"
                disabled
              />
              <span v-if="field.unit" class="body-field__unit" aria-hidden="true">
                {{ field.unit }}
              </span>
            </div>
          </div>
        </fieldset>

        <p class="body-fields__notice" role="note">
          신체 정보 입력과 저장 기능은 다음 작업에서 연결됩니다.
        </p>
      </section>
    </div>
  </OnboardingLayout>
</template>

<style scoped lang="scss">
.try-on-registration {
  width: 100%;
}

.try-on-registration__header,
.registration-section__heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
}

.try-on-registration__header {
  margin-bottom: var(--space-10);
}

.try-on-registration__title {
  font-size: 24px;
  font-weight: 700;
  line-height: 34px;
}

.try-on-registration__description,
.registration-section__description {
  margin-top: var(--space-2);
  color: var(--color-text-secondary);
}

.try-on-registration__optional,
.registration-section__status {
  flex: 0 0 auto;
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-chip);
  font-size: 12px;
  font-weight: 600;
  line-height: 20px;
}

.try-on-registration__optional {
  background: var(--color-ai-soft);
  color: var(--color-ai);
}

.registration-section__status {
  background: var(--color-surface-secondary);
  color: var(--color-text-secondary);
}

.registration-section + .registration-section {
  padding-top: var(--space-10);
  border-top: 1px solid var(--color-border);
  margin-top: var(--space-10);
}

.registration-section__title {
  font-size: 17px;
  font-weight: 600;
  line-height: 24px;
}

.registration-section__description {
  font-size: 13px;
  line-height: 20px;
}

.photo-registration {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(320px, 0.85fr);
  gap: var(--space-6);
  margin-top: var(--space-5);
}

.photo-registration__empty {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 320px;
  padding: var(--space-8);
  border: 1px dashed var(--color-border-strong);
  border-radius: var(--radius-media);
  flex-direction: column;
  background: var(--color-surface-secondary);
  text-align: center;
}

.photo-registration__empty strong {
  margin-top: var(--space-4);
  font-size: 17px;
  line-height: 24px;
}

.photo-registration__empty p {
  margin-top: var(--space-1);
  color: var(--color-text-secondary);
  font-size: 13px;
}

.photo-registration__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: var(--color-ai-soft);
  color: var(--color-ai);
}

.photo-registration__icon svg {
  width: 30px;
  height: 30px;
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.7;
}

.photo-registration__actions {
  display: flex;
  justify-content: center;
  gap: var(--space-3);
  margin-top: var(--space-6);
}

.photo-registration__button-icon {
  width: 20px;
  height: 20px;
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.8;
}

.photo-guide {
  padding: var(--space-6);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
}

.photo-guide__heading {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  font-size: 15px;
  font-weight: 600;
}

.photo-guide__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--color-ai-soft);
  color: var(--color-ai);
  font-size: 13px;
  font-weight: 700;
}

.photo-guide__list {
  display: grid;
  gap: var(--space-3);
  margin-top: var(--space-5);
  color: var(--color-text-secondary);
  font-size: 14px;
  line-height: 22px;
  list-style: none;
}

.photo-guide__list li {
  position: relative;
  padding-left: var(--space-5);
}

.photo-guide__list li::before {
  position: absolute;
  top: 8px;
  left: 0;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-ai);
  content: '';
}

.photo-guide__notice,
.body-fields__notice {
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-control);
  background: var(--color-ai-soft);
  color: var(--color-ai);
  font-size: 13px;
  font-weight: 600;
  line-height: 20px;
}

.photo-guide__notice {
  margin-top: var(--space-6);
}

.body-fields {
  display: grid;
  min-width: 0;
  padding: 0;
  border: 0;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-5);
  margin-top: var(--space-5);
}

.body-field {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: var(--space-2);
}

.body-field__label {
  color: var(--color-text-primary);
  font-size: 14px;
  font-weight: 600;
  line-height: 20px;
}

.body-field__control {
  position: relative;
}

.body-field__input {
  width: 100%;
  height: var(--button-height-standard);
  padding: 0 var(--space-4);
  padding-right: var(--space-12);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface-secondary);
  color: var(--color-text-secondary);
  outline: none;
}

.body-field__input::placeholder {
  color: var(--color-text-muted);
}

.body-field__unit {
  position: absolute;
  top: 50%;
  right: var(--space-4);
  color: var(--color-text-muted);
  font-size: 13px;
  transform: translateY(-50%);
}

.body-fields__notice {
  margin-top: var(--space-5);
}

.visually-hidden {
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

@media (max-width: 980px) {
  .photo-registration {
    grid-template-columns: 1fr;
  }

  .photo-registration__empty {
    min-height: 280px;
  }
}

@media (max-width: 820px) {
  .body-fields {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 560px) {
  .try-on-registration__header,
  .registration-section__heading {
    flex-direction: column;
  }

  .photo-registration__empty,
  .photo-guide {
    padding: var(--space-5);
  }

  .photo-registration__actions,
  .body-fields {
    width: 100%;
    grid-template-columns: 1fr;
  }

  .photo-registration__actions {
    align-items: stretch;
    flex-direction: column;
  }

  .photo-registration__actions :deep(.base-button) {
    width: 100%;
  }
}
</style>
