import {
  mockPointAccount,
  mockPointBalance,
  mockPointTransactions,
  mockWithdrawalHistory,
} from '@/domains/point/constants/pointOptions'
import type {
  PointAccount,
  PointBalance,
  PointTransaction,
  PointTransactionQuery,
  PointWalletViewData,
  WithdrawalHistory,
  WithdrawalRequest,
} from '@/domains/point/types/point.types'
import type { PageResponse } from '@/shared/types/api.types'

const MOCK_DELAY_MS = 350

const wait = (delay: number) =>
  new Promise<void>((resolve) => {
    window.setTimeout(resolve, delay)
  })

export const getPointWallet = async (
  userId: number,
  query: PointTransactionQuery = {},
): Promise<PointWalletViewData> => {
  const [balance, transactions, account, withdrawals] = await Promise.all([
    getPointBalance(userId),
    getPointTransactions(userId, query),
    getPointAccount(userId),
    getWithdrawals(userId),
  ])

  return {
    balance,
    account,
    transactions: transactions.items,
    transactionMeta: transactions.meta,
    withdrawals,
  }
}

export const getPointBalance = async (userId: number): Promise<PointBalance> => {
  void userId
  await wait(MOCK_DELAY_MS)
  return { ...mockPointBalance }
}

export const getPointTransactions = async (
  userId: number,
  { page = 1, size = 10, type = 'ALL' }: PointTransactionQuery = {},
): Promise<PageResponse<PointTransaction>> => {
  void userId
  await wait(MOCK_DELAY_MS)
  const filteredItems =
    type === 'ALL'
      ? mockPointTransactions
      : mockPointTransactions.filter((transaction) => transaction.type === type)

  return {
    items: filteredItems,
    meta: {
      page,
      size,
      totalElements: filteredItems.length,
      totalPages: filteredItems.length > 0 ? 1 : 0,
    },
  }
}

export const chargePoints = async (userId: number, amount: number): Promise<PointBalance> => {
  void userId
  await wait(MOCK_DELAY_MS)
  return {
    ...mockPointBalance,
    available: mockPointBalance.available + amount,
    withdrawable: mockPointBalance.withdrawable + amount,
    lastChangedAt: new Date().toISOString(),
  }
}

export const getPointAccount = async (userId: number): Promise<PointAccount | null> => {
  void userId
  await wait(MOCK_DELAY_MS)
  return { ...mockPointAccount }
}
export const requestWithdrawal = async (
  userId: number,
  request: WithdrawalRequest,
): Promise<WithdrawalHistory> => {
  void userId
  await wait(MOCK_DELAY_MS)
  return {
    id: Date.now(),
    amount: request.amount,
    fee: 0,
    status: 'REQUESTED',
    requestedAt: new Date().toISOString(),
    account: request.account,
  }
}

export const getWithdrawals = async (userId: number): Promise<WithdrawalHistory[]> => {
  void userId
  await wait(MOCK_DELAY_MS)
  return [...mockWithdrawalHistory]
}

export const isPointApiEnabled = () => false
