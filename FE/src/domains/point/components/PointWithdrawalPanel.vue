<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'

import { POINT_WITHDRAWAL_MIN_AMOUNT } from '@/domains/point/constants/pointOptions'
import type { PointAccount } from '@/domains/point/types/point.types'

const props = defineProps<{
  account: PointAccount | null
  withdrawableAmount: number
  isSubmitting: boolean
}>()

const emit = defineEmits<{
  withdraw: [amount: number, account: PointAccount]
}>()

const amount = ref('')
const errorMessage = ref('')
const accountForm = reactive<PointAccount>({
  bankName: props.account?.bankName ?? '',
  accountNumber: props.account?.accountNumber ?? '',
  holderName: props.account?.holderName ?? '',
})

const parsedAmount = computed(() => Number(amount.value))
const hasAccount = computed(
  () => accountForm.bankName.trim() && accountForm.accountNumber.trim() && accountForm.holderName.trim(),
)
const canSubmit = computed(
  () =>
    !props.isSubmitting &&
    hasAccount.value &&
    Number.isInteger(parsedAmount.value) &&
    parsedAmount.value >= POINT_WITHDRAWAL_MIN_AMOUNT &&
    parsedAmount.value <= props.withdrawableAmount,
)

watch(
  () => props.account,
  (nextAccount) => {
    accountForm.bankName = nextAccount?.bankName ?? accountForm.bankName
    accountForm.accountNumber = nextAccount?.accountNumber ?? accountForm.accountNumber
    accountForm.holderName = nextAccount?.holderName ?? accountForm.holderName
  },
)

watch([amount, () => accountForm.bankName, () => accountForm.accountNumber, () => accountForm.holderName], () => {
  errorMessage.value = ''
})

const submitWithdrawal = () => {
  if (!hasAccount.value) {
    errorMessage.value = '출금 계좌 정보를 입력해 주세요.'
    return
  }

  if (!Number.isInteger(parsedAmount.value) || parsedAmount.value < POINT_WITHDRAWAL_MIN_AMOUNT) {
    errorMessage.value = `출금 금액은 최소 ${POINT_WITHDRAWAL_MIN_AMOUNT.toLocaleString('ko-KR')}P 이상이어야 합니다.`
    return
  }

  if (parsedAmount.value > props.withdrawableAmount) {
    errorMessage.value = '출금 가능 포인트보다 큰 금액은 신청할 수 없습니다.'
    return
  }

  emit('withdraw', parsedAmount.value, { ...accountForm })
}
</script>

<template>
  <section class="point-withdrawal" aria-labelledby="point-withdrawal-title">
    <header>
      <h2 id="point-withdrawal-title">출금</h2>
      <p>출금 가능 {{ withdrawableAmount.toLocaleString('ko-KR') }}P</p>
    </header>

    <div class="point-withdrawal__section">
      <h3>출금 계좌 확인</h3>
      <div class="point-withdrawal__fields">
        <label>
          <span>은행</span>
          <input v-model="accountForm.bankName" type="text" :disabled="isSubmitting" />
        </label>
        <label>
          <span>계좌번호</span>
          <input v-model="accountForm.accountNumber" type="text" :disabled="isSubmitting" />
        </label>
        <label>
          <span>예금주</span>
          <input v-model="accountForm.holderName" type="text" :disabled="isSubmitting" />
        </label>
      </div>
    </div>

    <div class="point-withdrawal__section">
      <h3>출금 가격 입력 및 출금 신청</h3>
      <label class="point-withdrawal__amount">
        <span>출금 금액</span>
        <input
          v-model="amount"
          type="number"
          min="10000"
          step="1000"
          inputmode="numeric"
          :disabled="isSubmitting"
          placeholder="출금할 금액 입력"
        />
      </label>
    </div>

    <p v-if="errorMessage" class="point-withdrawal__error" role="alert">{{ errorMessage }}</p>

    <button type="button" :disabled="!canSubmit" @click="submitWithdrawal">
      {{ isSubmitting ? '신청 처리 중' : '출금 신청하기' }}
    </button>
  </section>
</template>

<style scoped lang="scss">
.point-withdrawal,
.point-withdrawal__section,
.point-withdrawal__fields,
.point-withdrawal label {
  display: grid;
  gap: var(--space-4);
}

.point-withdrawal {
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
}

.point-withdrawal header {
  display: grid;
  gap: var(--space-2);
}

.point-withdrawal h2 {
  color: var(--color-text-primary);
  font-size: var(--font-size-lg-plus);
  font-weight: var(--font-weight-extrabold);
  line-height: var(--line-height-lg-plus);
}

.point-withdrawal h3 {
  color: var(--color-text-primary);
  font-size: var(--font-size-body);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-relaxed);
}

.point-withdrawal p,
.point-withdrawal span {
  color: var(--color-text-secondary);
  font-size: var(--font-size-caption);
  line-height: var(--line-height-control);
}

.point-withdrawal label {
  gap: var(--space-2);
}

.point-withdrawal label span {
  font-weight: var(--font-weight-semibold);
}

.point-withdrawal input {
  min-height: var(--button-height-standard);
  padding: 0 var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-size: var(--font-size-body);
}

.point-withdrawal button {
  min-height: var(--button-height-small);
  border: 0;
  border-radius: var(--radius-control);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-bold);
}

.point-withdrawal button:disabled {
  opacity: 0.55;
}

.point-withdrawal__error {
  color: var(--color-error) !important;
  font-weight: var(--font-weight-semibold);
}
</style>
