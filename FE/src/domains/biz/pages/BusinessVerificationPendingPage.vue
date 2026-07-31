<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { useBusinessVerificationStore } from '@/domains/biz/stores/businessVerificationStore'
import { ROUTE_NAMES } from '@/shared/constants/routes'

const router = useRouter()
const businessVerificationStore = useBusinessVerificationStore()

const certificatePreviewUrl = ref('')
const submission = computed(() => businessVerificationStore.submission)

const formattedBusinessRegistrationNumber = computed(() => {
  const number = submission.value?.businessRegistrationNumber ?? ''

  if (number.length !== 10) {
    return number
  }

  return `${number.slice(0, 3)}-${number.slice(3, 5)}-${number.slice(5)}`
})

const formattedSubmittedAt = computed(() => {
  if (!submission.value) {
    return ''
  }

  return new Intl.DateTimeFormat('ko-KR', {
    dateStyle: 'long',
    timeStyle: 'short',
  }).format(submission.value.submittedAt)
})

const formattedFileSize = computed(() => {
  const size = submission.value?.certificate.size ?? 0

  if (size < 1024) {
    return `${size} B`
  }

  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`
  }

  return `${(size / 1024 / 1024).toFixed(1)} MB`
})

const releaseCertificatePreviewUrl = () => {
  if (!certificatePreviewUrl.value) {
    return
  }

  URL.revokeObjectURL(certificatePreviewUrl.value)
  certificatePreviewUrl.value = ''
}

watch(
  () => submission.value?.certificateFile,
  (certificateFile) => {
    releaseCertificatePreviewUrl()

    if (certificateFile?.size) {
      certificatePreviewUrl.value = URL.createObjectURL(certificateFile)
    }
  },
  { immediate: true },
)

onMounted(() => {
  if (!businessVerificationStore.hasSubmission) {
    void router.replace({ name: ROUTE_NAMES.BIZ_VERIFY })
  }
})

onBeforeUnmount(() => {
  releaseCertificatePreviewUrl()
})

const goHome = async () => {
  await router.push({ name: ROUTE_NAMES.HOME })
}
</script>

<template>
  <main class="verification-pending">
    <section
      v-if="submission"
      class="verification-pending__container"
      aria-labelledby="verification-pending-title"
    >
      <header class="verification-pending__header">
        <span class="verification-pending__icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" focusable="false">
            <circle cx="12" cy="12" r="8.5" />
            <path d="M12 7.5v5l3 2" />
          </svg>
        </span>
        <p class="verification-pending__eyebrow">BIZ-001-2</p>
        <h1 id="verification-pending-title">사업자 인증을 확인하고 있어요</h1>
        <p>
          제출한 정보를 확인한 뒤 사업자 회원 기능을 사용할 수 있도록 안내해 드릴게요.
        </p>
      </header>

      <section class="verification-summary" aria-labelledby="verification-summary-title">
        <div class="verification-summary__header">
          <div>
            <h2 id="verification-summary-title">제출 정보</h2>
            <p>{{ formattedSubmittedAt }} 제출</p>
          </div>
          <span>확인 대기</span>
        </div>

        <dl class="verification-summary__details">
          <div>
            <dt>사업자등록번호</dt>
            <dd>{{ formattedBusinessRegistrationNumber }}</dd>
          </div>
          <div>
            <dt>상호명</dt>
            <dd>{{ submission.businessName }}</dd>
          </div>
          <div>
            <dt>대표자명</dt>
            <dd>{{ submission.representativeName }}</dd>
          </div>
        </dl>

        <article class="verification-certificate">
          <img
            v-if="certificatePreviewUrl"
            :src="certificatePreviewUrl"
            :alt="`제출한 사업자등록증 미리보기: ${submission.certificateFile.name}`"
          />
          <div>
            <strong>사업자등록증</strong>
            <span :title="submission.certificate.name">
              {{ submission.certificate.name }}
            </span>
            <small>{{ formattedFileSize }}</small>
          </div>
        </article>
      </section>

      <aside class="verification-pending__notice" aria-label="인증 안내">
        <strong>제출이 완료되었습니다.</strong>
        <p>
          현재 화면의 인증 결과는 FE 더미 상태입니다. 실제 심사 결과와 소요 시간은
          사업자 인증 API가 연결된 뒤 제공됩니다.
        </p>
      </aside>

      <button
        type="button"
        class="verification-pending__home-button"
        aria-describedby="verification-home-description"
        @click="goHome"
      >
        메인으로 이동
      </button>
      <p id="verification-home-description" class="verification-pending__home-description">
        홈 화면으로 이동해 라이브와 상품을 둘러볼 수 있습니다.
      </p>
    </section>
  </main>
</template>

<style scoped lang="scss">
.verification-pending {
  min-height: 100vh;
  padding: var(--space-12);
  background: var(--color-page);
}

.verification-pending__container {
  width: 100%;
  max-width: 720px;
  margin: 0 auto;
}

.verification-pending__header {
  display: flex;
  align-items: center;
  flex-direction: column;
  text-align: center;
}

.verification-pending__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background: var(--color-primary-soft);
  color: var(--color-primary);
}

.verification-pending__icon svg {
  width: 30px;
  height: 30px;
  fill: none;
  stroke: currentcolor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.8;
}

.verification-pending__eyebrow {
  margin-top: var(--space-4);
  color: var(--color-primary);
  font-size: 13px;
  font-weight: 700;
  line-height: 18px;
}

.verification-pending__header h1 {
  margin-top: var(--space-2);
  color: var(--color-text-primary);
  font-size: 32px;
  line-height: 44px;
}

.verification-pending__header > p:last-child {
  max-width: 560px;
  margin-top: var(--space-2);
  color: var(--color-text-secondary);
  line-height: 24px;
}

.verification-summary {
  padding: var(--space-8);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  margin-top: var(--space-10);
  background: var(--color-surface);
}

.verification-summary__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
}

.verification-summary__header h2 {
  font-size: 20px;
  line-height: 28px;
}

.verification-summary__header p {
  margin-top: var(--space-1);
  color: var(--color-text-secondary);
  font-size: 13px;
}

.verification-summary__header > span {
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-badge);
  background: var(--color-primary-soft);
  color: var(--color-primary);
  flex: 0 0 auto;
  font-size: 12px;
  font-weight: 700;
}

.verification-summary__details {
  display: grid;
  gap: 0;
  margin-top: var(--space-6);
}

.verification-summary__details > div {
  display: grid;
  padding: var(--space-4) 0;
  border-top: 1px solid var(--color-border);
  gap: var(--space-4);
  grid-template-columns: 140px minmax(0, 1fr);
}

.verification-summary__details dt {
  color: var(--color-text-secondary);
  font-size: 14px;
}

.verification-summary__details dd {
  min-width: 0;
  color: var(--color-text-primary);
  font-size: 14px;
  font-weight: 600;
  overflow-wrap: anywhere;
}

.verification-certificate {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-media);
  margin-top: var(--space-3);
  background: var(--color-surface-secondary);
}

.verification-certificate img {
  width: 112px;
  height: 88px;
  border-radius: var(--radius-control);
  background: var(--color-surface);
  object-fit: contain;
}

.verification-certificate div {
  display: flex;
  min-width: 0;
  flex-direction: column;
}

.verification-certificate strong {
  font-size: 14px;
}

.verification-certificate span {
  overflow: hidden;
  margin-top: var(--space-1);
  color: var(--color-text-secondary);
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.verification-certificate small {
  margin-top: var(--space-1);
  color: var(--color-text-muted);
}

.verification-pending__notice {
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  margin-top: var(--space-6);
  background: var(--color-surface-secondary);
}

.verification-pending__notice strong {
  color: var(--color-text-primary);
  font-size: 14px;
}

.verification-pending__notice p {
  margin-top: var(--space-1);
  color: var(--color-text-secondary);
  font-size: 13px;
  line-height: 20px;
}

.verification-pending__home-button {
  width: 100%;
  height: var(--button-height-major);
  border: 0;
  border-radius: var(--radius-control);
  margin-top: var(--space-6);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  cursor: pointer;
  font: inherit;
  font-size: 15px;
  font-weight: 700;
}

.verification-pending__home-button:hover {
  background: var(--color-primary-hover);
}

.verification-pending__home-button:disabled {
  background: var(--color-border-strong);
  color: var(--color-text-muted);
  cursor: not-allowed;
}

.verification-pending__home-button:focus-visible {
  outline: 3px solid var(--color-primary-soft);
  outline-offset: 2px;
}

.verification-pending__home-description {
  margin-top: var(--space-2);
  color: var(--color-text-muted);
  font-size: 12px;
  line-height: 18px;
  text-align: center;
}

@media (max-width: 640px) {
  .verification-pending {
    padding: var(--space-8) var(--space-4);
  }

  .verification-pending__header h1 {
    font-size: 28px;
    line-height: 38px;
  }

  .verification-summary {
    padding: var(--space-5);
  }

  .verification-summary__details > div {
    gap: var(--space-1);
    grid-template-columns: 1fr;
  }

  .verification-certificate {
    align-items: stretch;
    flex-direction: column;
  }

  .verification-certificate img {
    width: 100%;
    height: 180px;
  }
}
</style>
