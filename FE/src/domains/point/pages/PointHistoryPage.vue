<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/domains/auth/stores/authStore'
import { getPointTransactions } from '@/domains/point/api/pointApi'
import PointTransactionList from '@/domains/point/components/PointTransactionList.vue'
import type {
  PointHistoryFlowFilter,
  PointTransaction,
} from '@/domains/point/types/point.types'
import { normalizeApiError } from '@/shared/api/http'
import { ROUTE_NAMES, ROUTE_PATHS } from '@/shared/constants/routes'
import DefaultLayout from '@/shared/layouts/DefaultLayout.vue'

const router = useRouter()
const authStore = useAuthStore()

const transactions = ref<PointTransaction[]>([])
const loadState = ref<'idle' | 'loading' | 'success' | 'error' | 'guest'>('idle')
const errorMessage = ref('')
const selectedFlow = ref<PointHistoryFlowFilter>('ALL')
const startDate = ref('')
const endDate = ref('')

const flowOptions: Array<{ id: PointHistoryFlowFilter; label: string }> = [
  { id: 'ALL', label: '전체' },
  { id: 'WITHDRAWAL', label: '출금' },
  { id: 'DEPOSIT', label: '입금' },
]

const filteredTransactions = computed(() =>
  transactions.value.filter((transaction) => {
    const matchesFlow =
      selectedFlow.value === 'ALL' ||
      (selectedFlow.value === 'DEPOSIT' && transaction.amount > 0) ||
      (selectedFlow.value === 'WITHDRAWAL' && transaction.amount < 0)

    const transactionDate = transaction.createdAt.slice(0, 10)
    const matchesStart = !startDate.value || transactionDate >= startDate.value
    const matchesEnd = !endDate.value || transactionDate <= endDate.value

    return matchesFlow && matchesStart && matchesEnd
  }),
)

const loadHistory = async () => {
  await authStore.validateStoredSession()

  if (!authStore.user?.id) {
    loadState.value = 'guest'
    return
  }

  loadState.value = 'loading'
  errorMessage.value = ''

  try {
    const result = await getPointTransactions(authStore.user.id, {
      page: 1,
      size: 100,
      type: 'ALL',
    })

    transactions.value = result.items
    loadState.value = 'success'
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message
    loadState.value = 'error'
  }
}

const resetFilters = () => {
  selectedFlow.value = 'ALL'
  startDate.value = ''
  endDate.value = ''
}

const goToPoint = () => {
  void router.push({ name: ROUTE_NAMES.POINT })
}

const goToLogin = () => {
  void router.push({
    name: ROUTE_NAMES.AUTH_LOGIN,
    query: { redirect: ROUTE_PATHS.POINT_HISTORY },
  })
}

onMounted(() => {
  void loadHistory()
})
</script>

<template>
  <DefaultLayout content-max-width="960px">
    <section class="point-history" aria-labelledby="point-history-title">
      <header class="point-history__header">
        <div>
          <p class="point-history__eyebrow">POINT HISTORY</p>
          <h1 id="point-history-title">전체 내역</h1>
          <p>포인트 입금과 출금 내역을 조건별로 확인합니다.</p>
        </div>
        <button type="button" @click="goToPoint">포인트로 돌아가기</button>
      </header>

      <div v-if="loadState === 'loading'" class="point-history__state" role="status">
        포인트 내역을 불러오는 중입니다.
      </div>

      <div v-else-if="loadState === 'guest'" class="point-history__state">
        <strong>로그인이 필요합니다.</strong>
        <p>전체 내역은 로그인 후 확인할 수 있습니다.</p>
        <button type="button" @click="goToLogin">로그인으로 이동</button>
      </div>

      <div v-else-if="loadState === 'error'" class="point-history__state" role="alert">
        <strong>내역을 불러오지 못했습니다.</strong>
        <p>{{ errorMessage }}</p>
        <button type="button" @click="loadHistory">다시 시도</button>
      </div>

      <template v-else>
        <section class="point-history__filters" aria-label="포인트 내역 필터">
          <div class="point-history__flow" role="tablist" aria-label="입출금 구분">
            <button
              v-for="option in flowOptions"
              :key="option.id"
              type="button"
              role="tab"
              :aria-selected="selectedFlow === option.id"
              :class="{ 'point-history__flow--active': selectedFlow === option.id }"
              @click="selectedFlow = option.id"
            >
              {{ option.label }}
            </button>
          </div>

          <div class="point-history__period">
            <label>
              <span>시작일</span>
              <input v-model="startDate" type="date" />
            </label>
            <label>
              <span>종료일</span>
              <input v-model="endDate" type="date" />
            </label>
            <button type="button" @click="resetFilters">초기화</button>
          </div>
        </section>

        <PointTransactionList
          :title="`내역 ${filteredTransactions.length}건`"
          :transactions="filteredTransactions"
        />
      </template>
    </section>
  </DefaultLayout>
</template>

<style scoped lang="scss">
.point-history {
  display: grid;
  gap: var(--space-6);
}

.point-history__header {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: var(--space-5);
}

.point-history__eyebrow {
  margin-bottom: var(--space-1);
  color: var(--color-primary);
  font-size: 13px;
  font-weight: var(--font-weight-bold);
  line-height: 20px;
}

.point-history__header h1 {
  color: var(--color-text-primary);
  font-size: 36px;
  font-weight: var(--font-weight-extrabold);
  line-height: 44px;
}

.point-history__header p {
  margin-top: var(--space-2);
  color: var(--color-text-secondary);
  font-size: 15px;
  line-height: 24px;
}

.point-history__header button,
.point-history__state button,
.point-history__period button {
  min-height: var(--button-height-small);
  padding: 0 var(--space-4);
  border-radius: var(--radius-control);
  font-size: 14px;
  font-weight: var(--font-weight-bold);
}

.point-history__header button,
.point-history__period button {
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text-primary);
}

.point-history__state button {
  border: 0;
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

.point-history__filters {
  display: grid;
  gap: var(--space-4);
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
}

.point-history__flow {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-2);
}

.point-history__flow button {
  min-height: var(--button-height-small);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface-secondary);
  color: var(--color-text-primary);
  font-size: 14px;
  font-weight: var(--font-weight-bold);
}

.point-history__flow--active {
  border-color: var(--color-primary) !important;
  background: var(--color-primary) !important;
  color: var(--color-text-inverse) !important;
}

.point-history__period {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) auto;
  gap: var(--space-3);
  align-items: end;
}

.point-history__period label {
  display: grid;
  gap: var(--space-2);
}

.point-history__period span {
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: var(--font-weight-semibold);
  line-height: 20px;
}

.point-history__period input {
  min-height: var(--button-height-standard);
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-size: 14px;
}

.point-history__state {
  display: grid;
  justify-items: center;
  gap: var(--space-3);
  padding: var(--space-8);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  text-align: center;
}

.point-history__state strong {
  color: var(--color-text-primary);
  font-size: 18px;
  font-weight: var(--font-weight-extrabold);
}

@media (max-width: 720px) {
  .point-history__header {
    align-items: stretch;
    flex-direction: column;
  }

  .point-history__period {
    grid-template-columns: 1fr;
  }
}
</style>
