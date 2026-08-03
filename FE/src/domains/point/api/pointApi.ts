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

const EMPTY_POINT_BALANCE: PointBalance = {
  available: 0,
  held: 0,
  escrow: 0,
  pendingSettlement: 0,
  withdrawalProcessing: 0,
  withdrawable: 0,
  lastChangedAt: '',
}

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
  return { ...EMPTY_POINT_BALANCE }
}

export const getPointTransactions = async (
  userId: number,
  { page = 1, size = 10 }: PointTransactionQuery = {},
): Promise<PageResponse<PointTransaction>> => {
  void userId
  return {
    items: [],
    meta: {
      page,
      size,
      totalElements: 0,
      totalPages: 0,
    },
  }
}

export const chargePoints = async (userId: number, amount: number): Promise<PointBalance> => {
  void userId
  void amount
  return { ...EMPTY_POINT_BALANCE }
}

export const getPointAccount = async (userId: number): Promise<PointAccount | null> => {
  void userId
  return null
}

export const requestWithdrawal = async (
  userId: number,
  request: WithdrawalRequest,
): Promise<WithdrawalHistory> => {
  void userId
  return {
    id: 0,
    amount: request.amount,
    fee: 0,
    status: 'REQUESTED',
    requestedAt: '',
    account: request.account,
  }
}

export const getWithdrawals = async (userId: number): Promise<WithdrawalHistory[]> => {
  void userId
  return []
}

export const isPointApiEnabled = () => false
