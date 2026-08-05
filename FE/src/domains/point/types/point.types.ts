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

/** 충전 준비(POINT-001) 응답 — 토스페이먼츠 결제위젯에 그대로 넘긴다. */
export interface PointChargeReady {
  orderId: string
  amount: number
  clientKey: string
}

/** 충전 승인(POINT-001) 요청 — 결제위젯이 successUrl로 돌려준 값을 그대로 담는다. */
export interface PointChargeConfirmRequest {
  orderId: string
  paymentKey: string
  amount: number
}
