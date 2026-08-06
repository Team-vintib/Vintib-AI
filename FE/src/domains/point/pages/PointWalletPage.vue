<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '@/domains/auth/stores/authStore'
import { getPointWallet, requestWithdrawal } from '@/domains/point/api/pointApi'
import PointChargePanel from '@/domains/point/components/PointChargePanel.vue'
import PointSummaryPanel from '@/domains/point/components/PointSummaryPanel.vue'
import PointTransactionList from '@/domains/point/components/PointTransactionList.vue'
import PointWithdrawalPanel from '@/domains/point/components/PointWithdrawalPanel.vue'
import type {
  PointAccount,
  PointBalance,
  PointTransaction,
} from '@/domains/point/types/point.types'
import { normalizeApiError } from '@/shared/api/http'
import { ROUTE_NAMES, ROUTE_PATHS } from '@/shared/constants/routes'
import DefaultLayout from '@/shared/layouts/DefaultLayout.vue'

type PointMainSection = 'history' | 'charge' | 'withdraw'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const balance = ref<PointBalance | null>(null)
const account = ref<PointAccount | null>(null)
const transactions = ref<PointTransaction[]>([])
const selectedSection = ref<PointMainSection>(route.query.section === 'charge' ? 'charge' : 'history')
const loadState = ref<'idle' | 'loading' | 'success' | 'error' | 'guest'>('idle')
const errorMessage = ref('')
const actionMessage = ref('')
const actionErrorMessage = ref('')
const isWithdrawing = ref(false)

// PointChargePanel/PointWithdrawalPanel은 loadState가 'success'일 때만 렌더링되고,
// 그 상태는 authStore.user.id가 있어야만 도달하므로 0 폴백은 실제로 쓰이지 않는다.
const userId = computed(() => authStore.user?.id ?? 0)
const isLoading = computed(() => loadState.value === 'loading')
const hasLoadError = computed(() => loadState.value === 'error')
const isGuest = computed(() => loadState.value === 'guest')
const recentTransactions = computed(() => transactions.value.slice(0, 10))

const sectionButtons: Array<{ id: PointMainSection; label: string }> = [
  { id: 'history', label: '내역' },
  { id: 'charge', label: '충전' },
  { id: 'withdraw', label: '출금' },
]

const loadWallet = async () => {
  await authStore.validateStoredSession()

  if (!authStore.user?.id) {
    loadState.value = 'guest'
    return
  }

  loadState.value = 'loading'
  errorMessage.value = ''
  actionErrorMessage.value = ''

  try {
    const wallet = await getPointWallet(authStore.user.id, {
      page: 1,
      size: 10,
      type: 'ALL',
    })

    balance.value = wallet.balance
    account.value = wallet.account
    transactions.value = wallet.transactions
    loadState.value = 'success'
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message
    loadState.value = 'error'
  }
}

const selectSection = (section: PointMainSection) => {
  selectedSection.value = section
  actionMessage.value = ''
  actionErrorMessage.value = ''
}

const goToHistory = () => {
  void router.push({ name: ROUTE_NAMES.POINT_HISTORY })
}

// 실제 충전 처리는 PointChargePanel이 토스 결제위젯으로 리다이렉트해 진행하고,
// 최종 승인은 /points/charge/success 콜백 페이지가 맡는다. 여기서는 위젯 준비/요청
// 단계에서 난 오류만 화면에 보여준다.
const handleChargeError = (message: string) => {
  actionErrorMessage.value = message
}

const handleWithdrawal = async (amount: number, nextAccount: PointAccount) => {
  if (!authStore.user?.id) {
    await router.push({ name: ROUTE_NAMES.AUTH_LOGIN, query: { redirect: ROUTE_PATHS.POINT } })
    return
  }

  isWithdrawing.value = true
  actionMessage.value = ''
  actionErrorMessage.value = ''

  try {
    await requestWithdrawal(authStore.user.id, {
      amount,
      account: nextAccount,
    })

    account.value = nextAccount
    actionMessage.value = `${amount.toLocaleString('ko-KR')}P 출금 신청이 접수되었습니다.`
    await loadWallet()
    selectedSection.value = 'history'
  } catch (error) {
    const apiError = normalizeApiError(error)
    actionErrorMessage.value =
      apiError.code === 'POINT_INSUFFICIENT' ? '출금 가능 포인트가 부족합니다.' : apiError.message
  } finally {
    isWithdrawing.value = false
  }
}

const goToLogin = () => {
  void router.push({
    name: ROUTE_NAMES.AUTH_LOGIN,
    query: { redirect: ROUTE_PATHS.POINT },
  })
}

onMounted(() => {
  void loadWallet()
})
</script>

<template>
  <DefaultLayout content-max-width="1120px">
    <section class="point-page" aria-label="포인트">
      <div v-if="isLoading" class="point-page__state" role="status">
        포인트 정보를 불러오는 중입니다.
      </div>

      <div v-else-if="isGuest" class="point-page__state">
        <strong>로그인이 필요합니다.</strong>
        <p>포인트 잔액과 출금 내역은 로그인 후 확인할 수 있습니다.</p>
        <button type="button" @click="goToLogin">로그인으로 이동</button>
      </div>

      <div v-else-if="hasLoadError" class="point-page__state" role="alert">
        <strong>포인트 정보를 불러오지 못했습니다.</strong>
        <p>{{ errorMessage }}</p>
        <button type="button" @click="loadWallet">다시 시도</button>
      </div>

      <template v-else-if="balance">
        <PointSummaryPanel :balance="balance" />

        <div class="point-page__section-tabs" role="tablist" aria-label="포인트 메뉴">
          <button
            v-for="button in sectionButtons"
            :key="button.id"
            type="button"
            role="tab"
            :aria-selected="selectedSection === button.id"
            :class="{ 'point-page__section-tab--active': selectedSection === button.id }"
            @click="selectSection(button.id)"
          >
            {{ button.label }}
          </button>
        </div>

        <p v-if="actionMessage" class="point-page__message" role="status">
          {{ actionMessage }}
        </p>
        <p v-if="actionErrorMessage" class="point-page__error" role="alert">
          {{ actionErrorMessage }}
        </p>

        <PointTransactionList
          v-if="selectedSection === 'history'"
          title="최근 내역"
          :transactions="recentTransactions"
          show-view-all
          @view-all="goToHistory"
        />

        <PointChargePanel
          v-else-if="selectedSection === 'charge'"
          :user-id="userId"
          :current-balance="balance.available"
          @error="handleChargeError"
        />

        <PointWithdrawalPanel
          v-else
          :account="account"
          :withdrawable-amount="balance.withdrawable"
          :is-submitting="isWithdrawing"
          @withdraw="handleWithdrawal"
        />
      </template>
    </section>
  </DefaultLayout>
</template>

<style scoped lang="scss">
.point-page {
  display: grid;
  gap: var(--space-6);
}

.point-page__section-tabs {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-3);
}

.point-page__section-tabs button {
  min-height: var(--button-height-standard);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-size: var(--font-size-body);
  font-weight: var(--font-weight-bold);
}

.point-page__section-tab--active {
  border-color: var(--color-primary) !important;
  background: var(--color-primary) !important;
  color: var(--color-text-inverse) !important;
}

.point-page__state {
  display: grid;
  justify-items: center;
  gap: var(--space-3);
  padding: var(--space-8);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  font-size: var(--font-size-body);
  line-height: var(--line-height-body);
  text-align: center;
}

.point-page__state strong {
  color: var(--color-text-primary);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-extrabold);
  line-height: var(--line-height-lg);
}

.point-page__state button {
  min-height: var(--button-height-small);
  padding: 0 var(--space-4);
  border: 0;
  border-radius: var(--radius-control);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-bold);
}

.point-page__message,
.point-page__error {
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-control);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-relaxed);
}

.point-page__message {
  background: var(--color-primary-soft);
  color: var(--color-primary);
}

.point-page__error {
  background: var(--color-error-soft);
  color: var(--color-error);
}

@media (max-width: 520px) {
  .point-page__section-tabs {
    grid-template-columns: 1fr;
  }
}
</style>
