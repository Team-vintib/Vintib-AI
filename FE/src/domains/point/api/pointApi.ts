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
import { http } from '@/shared/api/http'
import type { ApiResponse, PageResponse } from '@/shared/types/api.types'

interface BackendPageResponse<T> {
  content: T[]
  page: number
  size: number
  totalElements: number
  totalPages: number
}

const MOCK_DELAY_MS = 350
const POINT_API_ENABLED = import.meta.env.VITE_POINT_API_ENABLED === 'true'

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
  if (!POINT_API_ENABLED) {
    await wait(MOCK_DELAY_MS)
    return { ...mockPointBalance }
  }

  const response = await http.get<ApiResponse<PointBalance>>(`/users/${userId}/points`)
  return unwrapApiData(response.data, '포인트 잔액을 불러오지 못했습니다.')
}

export const getPointTransactions = async (
  userId: number,
  { page = 1, size = 10, type = 'ALL' }: PointTransactionQuery = {},
): Promise<PageResponse<PointTransaction>> => {
  if (!POINT_API_ENABLED) {
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

  const response = await http.get<
    ApiResponse<PageResponse<PointTransaction> | BackendPageResponse<PointTransaction>>
  >(`/users/${userId}/points/logs`, {
    params: {
      page: Math.max(page - 1, 0),
      size,
      type: type === 'ALL' ? undefined : type,
    },
  })

  return normalizePageResponse(unwrapApiData(response.data, '포인트 내역을 불러오지 못했습니다.'))
}

export const chargePoints = async (userId: number, amount: number): Promise<PointBalance> => {
  if (!POINT_API_ENABLED) {
    await wait(MOCK_DELAY_MS)
    return {
      ...mockPointBalance,
      available: mockPointBalance.available + amount,
      withdrawable: mockPointBalance.withdrawable + amount,
      lastChangedAt: new Date().toISOString(),
    }
  }

  const response = await http.post<ApiResponse<PointBalance>>(`/users/${userId}/points/charges`, {
    amount,
  })
  return unwrapApiData(response.data, '포인트 충전에 실패했습니다.')
}

export const getPointAccount = async (userId: number): Promise<PointAccount | null> => {
  if (!POINT_API_ENABLED) {
    await wait(MOCK_DELAY_MS)
    return { ...mockPointAccount }
  }

  const response = await http.get<ApiResponse<PointAccount | null>>(`/users/${userId}/points/account`)

  if (!response.data.success) {
    throw new Error(response.data.error?.message ?? '출금 계좌를 불러오지 못했습니다.')
  }

  return response.data.data
}

export const requestWithdrawal = async (
  userId: number,
  request: WithdrawalRequest,
): Promise<WithdrawalHistory> => {
  if (!POINT_API_ENABLED) {
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

  const response = await http.post<ApiResponse<WithdrawalHistory>>(
    `/users/${userId}/withdrawals`,
    request,
  )
  return unwrapApiData(response.data, '출금 신청에 실패했습니다.')
}

export const getWithdrawals = async (userId: number): Promise<WithdrawalHistory[]> => {
  if (!POINT_API_ENABLED) {
    await wait(MOCK_DELAY_MS)
    return [...mockWithdrawalHistory]
  }

  const response = await http.get<ApiResponse<WithdrawalHistory[]>>(`/users/${userId}/withdrawals`)
  return unwrapApiData(response.data, '출금 내역을 불러오지 못했습니다.')
}

export const isPointApiEnabled = () => POINT_API_ENABLED

const unwrapApiData = <T>(response: ApiResponse<T>, fallbackMessage: string) => {
  if (!response.success || response.data === null) {
    throw new Error(response.error?.message ?? fallbackMessage)
  }

  return response.data
}

const normalizePageResponse = <T>(
  response: PageResponse<T> | BackendPageResponse<T>,
): PageResponse<T> => {
  if ('items' in response) {
    return response
  }

  return {
    items: response.content,
    meta: {
      page: response.page + 1,
      size: response.size,
      totalElements: response.totalElements,
      totalPages: response.totalPages,
    },
  }
}
