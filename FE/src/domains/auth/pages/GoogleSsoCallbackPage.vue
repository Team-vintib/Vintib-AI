<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { signInWithGoogle } from '@/domains/auth/api/authApi'
import { useAuthStore } from '@/domains/auth/stores/authStore'
import {
  clearGoogleOAuthSource,
  getGoogleOAuthRedirectUri,
  readGoogleOAuthSource,
  startGoogleOAuth,
  type GoogleOAuthSource,
} from '@/domains/auth/utils/googleOAuth'
import { writeLinkAccountSession } from '@/domains/auth/utils/linkAccountSession'
import { normalizeApiError } from '@/shared/api/http'
import { ROUTE_NAMES, ROUTE_PATHS } from '@/shared/constants/routes'
import AuthLayout from '@/shared/layouts/AuthLayout.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const isProcessing = ref(true)
const statusTitle = ref('Google 인증 처리 중')
const statusMessage = ref('인증 결과를 확인하고 있습니다.')
const errorMessage = ref('')
const oauthSource = ref<GoogleOAuthSource>('signup')

onMounted(() => {
  void handleCallback()
})

const handleCallback = async () => {
  oauthSource.value = readGoogleOAuthSource()

  const error = getQueryValue(route.query.error)
  const code = getQueryValue(route.query.code)

  if (error === 'access_denied') {
    applyCallbackError('Google 인증이 취소되었습니다.', '다시 인증을 시도할 수 있습니다.')
    return
  }

  if (error) {
    applyCallbackError('Google 인증에 실패했습니다.', '인증 제공자의 응답을 다시 확인해 주세요.')
    return
  }

  if (!code) {
    applyCallbackError(
      '인증 정보를 확인하지 못했습니다.',
      '잘못된 접근이거나 인증 시간이 만료되었습니다.',
    )
    return
  }

  try {
    const response = await signInWithGoogle({ code, redirectUri: getGoogleOAuthRedirectUri() })

    if (!response.success || !response.data) {
      applyCallbackError(
        'Google 인증을 완료하지 못했습니다.',
        response.error?.message || '잠시 후 다시 시도해 주세요.',
      )
      return
    }

    if (response.data.status === 'LINK_REQUIRED') {
      if (!response.data.linkToken) {
        applyCallbackError(
          '계정 연결 정보를 확인하지 못했습니다.',
          'Google 인증을 다시 진행해 주세요.',
        )
        return
      }

      writeLinkAccountSession({
        email: response.data.email || '',
        linkToken: response.data.linkToken,
      })
      await router.replace(ROUTE_PATHS.AUTH_LINK_ACCOUNT)
      return
    }

    if (!response.data.accessToken) {
      applyCallbackError('인증 결과를 확인하지 못했습니다.', 'Google 인증을 다시 진행해 주세요.')
      return
    }

    authStore.setSession({
      accessToken: response.data.accessToken,
      refreshToken: response.data.refreshToken,
      user: { onboardingCompleted: response.data.onboardingCompleted ?? undefined },
    })
    clearGoogleOAuthSource()

    if (response.data.onboardingCompleted === false) {
      await router.replace({ name: ROUTE_NAMES.ONBOARD_PROFILE })
      return
    }

    await router.replace(ROUTE_PATHS.HOME)
  } catch (error: unknown) {
    const apiError = normalizeApiError(error)

    applyCallbackError(
      'Google 인증을 완료하지 못했습니다.',
      apiError.message || '네트워크 연결을 확인한 뒤 다시 시도해 주세요.',
    )
  }
}

const applyCallbackError = (title: string, message: string) => {
  isProcessing.value = false
  statusTitle.value = title
  statusMessage.value = message
  errorMessage.value = message
}

const retryAuth = () => {
  startGoogleOAuth(oauthSource.value)
}

const fallbackPath = computed(() =>
  oauthSource.value === 'login' ? ROUTE_PATHS.AUTH_LOGIN : ROUTE_PATHS.AUTH_SIGNUP,
)

const fallbackLabel = computed(() =>
  oauthSource.value === 'login' ? '로그인으로 돌아가기' : '회원가입 선택으로 돌아가기',
)

function getQueryValue(value: unknown) {
  if (Array.isArray(value)) {
    return value[0] ? String(value[0]) : ''
  }

  return value ? String(value) : ''
}
</script>

<template>
  <AuthLayout>
    <article
      class="callback-card rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-8 shadow-sm"
      aria-labelledby="callback-title"
    >
      <div class="callback-state" :class="{ 'callback-state--error': errorMessage }">
        <span class="callback-state__indicator" aria-hidden="true"></span>
      </div>

      <h1 id="callback-title" class="callback-title">
        {{ statusTitle }}
      </h1>
      <p class="callback-description">
        {{ statusMessage }}
      </p>

      <div v-if="errorMessage" class="callback-actions">
        <button type="button" class="callback-primary-link" @click="retryAuth">
          다시 인증하기
        </button>
        <a class="callback-secondary-link" :href="fallbackPath">
          {{ fallbackLabel }}
        </a>
      </div>

      <p v-else-if="isProcessing" class="callback-caption">
        화면을 닫지 말고 잠시만 기다려 주세요.
      </p>
    </article>
  </AuthLayout>
</template>

<style scoped lang="scss">
.callback-card {
  width: 100%;
  padding: var(--space-8);
  text-align: center;
}

.callback-state {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  margin-bottom: var(--space-6);
  border-radius: var(--radius-chip);
  background: var(--color-primary-soft);
}

.callback-state__indicator {
  width: 18px;
  height: 18px;
  border: 3px solid var(--color-primary);
  border-top-color: transparent;
  border-radius: var(--radius-chip);
  animation: callback-spin 900ms linear infinite;
}

.callback-state--error {
  background: var(--color-error-soft);
}

.callback-state--error .callback-state__indicator {
  width: var(--space-4);
  height: var(--space-4);
  border: 0;
  border-radius: var(--radius-control);
  animation: none;
  background: var(--color-error);
}

.callback-title {
  color: var(--color-text-primary);
  font-size: var(--font-size-3xl);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-3xl);
}

.callback-description {
  margin-top: var(--space-3);
  color: var(--color-text-secondary);
  font-size: var(--font-size-body);
  line-height: var(--line-height-body);
}

.callback-caption {
  margin-top: var(--space-8);
  color: var(--color-text-muted);
  font-size: var(--font-size-caption);
  line-height: var(--line-height-snug);
}

.callback-actions {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  margin-top: var(--space-8);
}

.callback-primary-link,
.callback-secondary-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: var(--button-height-major);
  border-radius: var(--radius-control);
  font-size: var(--font-size-body);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-control);
}

.callback-primary-link {
  border: 0;
  background: var(--color-primary);
  color: var(--color-text-inverse);
  cursor: pointer;
}

.callback-primary-link:hover {
  background: var(--color-primary-hover);
}

.callback-secondary-link {
  border: 1px solid var(--color-border-strong);
  background: var(--color-surface);
  color: var(--color-text-primary);
}

.callback-secondary-link:hover {
  background: var(--color-surface-secondary);
}

@keyframes callback-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 560px) {
  .callback-card {
    padding: var(--space-6);
  }
}
</style>
