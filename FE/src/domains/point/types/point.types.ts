import type { PageMeta } from '@/shared/types/api.types'

export type PointTransactionType =
  | 'CHARGE'
  | 'USE'
  | 'HOLD'
  | 'HOLD_RELEASE'
  | 'SETTLEMENT'
  | 'REFUND'
  | 'WITHDRAWAL'

export type PointTransactionStatus = 'COMPLETED' | 'PENDING' | 'FAILED'
export type WithdrawalStatus = 'REQUESTED' | 'PROCESSING' | 'COMPLETED' | 'REJECTED'
export type PointHistoryFlowFilter = 'ALL' | 'DEPOSIT' | 'WITHDRAWAL'

export interface PointBalance {
  available: number
  held: number
  escrow: number
  pendingSettlement: number
  withdrawalProcessing: number
  withdrawable: number
  lastChangedAt: string
}

export interface PointTransaction {
  id: number
  type: PointTransactionType
  title: string
  amount: number
  balanceAfter: number
  status: PointTransactionStatus
  createdAt: string
  memo?: string
}

export interface PointAccount {
  bankName: string
  accountNumber: string
  holderName: string
}

export interface WithdrawalRequest {
  amount: number
  account: PointAccount
}

export interface WithdrawalHistory {
  id: number
  amount: number
  fee: number
  status: WithdrawalStatus
  requestedAt: string
  completedAt?: string
  account: PointAccount
}

export interface PointWalletViewData {
  balance: PointBalance
  account: PointAccount | null
  transactions: PointTransaction[]
  transactionMeta: PageMeta
  withdrawals: WithdrawalHistory[]
}

export interface PointTransactionQuery {
  page?: number
  size?: number
  type?: PointTransactionType | 'ALL'
}
