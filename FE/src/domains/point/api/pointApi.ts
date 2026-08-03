import type {
  PointAccount,
  PointBalance,
  PointTransaction,
  PointTransactionType,
  PointTransactionQuery,
  PointWalletViewData,
  WithdrawalHistory,
  WithdrawalRequest,
} from '@/domains/point/types/point.types'
import { http } from '@/shared/api/http'
import type { ApiResponse, PageResponse } from '@/shared/types/api.types'

const POINT_API_ENABLED = import.meta.env.VITE_POINT_API_ENABLED !== 'false'

interface BackendPointBalanceResponse {
  available: number
  bidHeld: number
  tradeEscrow: number
  settling: number
  withdrawing: number
  updatedAt: string
}

interface BackendPointTransactionResponse {
  id: number
  type: string
  amount: number
  balanceAfter: number
  refType: string | null
  refId: number | null
  createdAt: string
}

interface BackendPageResponse<T> {
  content: T[]
  page: number
  size: number
  totalElements: number
  totalPages: number
}

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
  if (POINT_API_ENABLED) {
    const { data } = await http.get<ApiResponse<BackendPointBalanceResponse>>(
      `/users/${userId}/points`,
    )

    if (data.data) {
      return toPointBalance(data.data)
    }
  }

  return { ...EMPTY_POINT_BALANCE }
}

export const getPointTransactions = async (
  userId: number,
  { page = 1, size = 10 }: PointTransactionQuery = {},
): Promise<PageResponse<PointTransaction>> => {
  if (POINT_API_ENABLED) {
    const { data } = await http.get<
      ApiResponse<BackendPageResponse<BackendPointTransactionResponse>>
    >(`/users/${userId}/points/logs`, {
      params: {
        page: Math.max(page - 1, 0),
        size,
      },
    })

    if (data.data) {
      return toPageResponse(data.data, toPointTransaction)
    }
  }

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
  if (POINT_API_ENABLED) {
    const { data } = await http.post<ApiResponse<BackendPointBalanceResponse>>(
      `/users/${userId}/points/charges`,
      { amount },
    )

    if (data.data) {
      return toPointBalance(data.data)
    }
  }

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

export const isPointApiEnabled = () => POINT_API_ENABLED

const toPointBalance = (response: BackendPointBalanceResponse): PointBalance => ({
  available: response.available,
  held: response.bidHeld,
  escrow: response.tradeEscrow,
  pendingSettlement: response.settling,
  withdrawalProcessing: response.withdrawing,
  withdrawable: response.available,
  lastChangedAt: response.updatedAt,
})

const toPointTransaction = (response: BackendPointTransactionResponse): PointTransaction => {
  const type = toPointTransactionType(response.type)

  return {
    id: response.id,
    type,
    title: POINT_TRANSACTION_TITLES[type],
    amount: response.amount,
    balanceAfter: response.balanceAfter,
    status: 'COMPLETED',
    createdAt: response.createdAt,
    memo: response.refType && response.refId ? `${response.refType} #${response.refId}` : undefined,
  }
}

const toPointTransactionType = (type: string): PointTransactionType => {
  switch (type) {
    case 'BID_HOLD':
      return 'HOLD'
    case 'BID_RELEASE':
      return 'HOLD_RELEASE'
    case 'PAYMENT':
      return 'USE'
    case 'WITHDRAW':
      return 'WITHDRAWAL'
    case 'CHARGE':
    case 'SETTLEMENT':
    case 'REFUND':
      return type
    default:
      return 'USE'
  }
}

const POINT_TRANSACTION_TITLES: Record<PointTransactionType, string> = {
  CHARGE: '포인트 충전',
  USE: '포인트 사용',
  HOLD: '입찰 보류',
  HOLD_RELEASE: '보류 해제',
  SETTLEMENT: '판매 정산',
  REFUND: '환불',
  WITHDRAWAL: '출금 신청',
}

const toPageResponse = <T, R>(
  response: BackendPageResponse<T>,
  mapper: (item: T) => R,
): PageResponse<R> => ({
  items: response.content.map(mapper),
  meta: {
    page: response.page + 1,
    size: response.size,
    totalElements: response.totalElements,
    totalPages: response.totalPages,
  },
})
