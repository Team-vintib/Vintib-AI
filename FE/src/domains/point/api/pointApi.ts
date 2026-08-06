import { getOrderDetail } from '@/domains/order/api/orderApi'
import type {
  PointAccount,
  PointBalance,
  PointChargeConfirmRequest,
  PointChargeReady,
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

// 경매 입찰 보류/해제 — 낙찰로 이어지지 않는 한 포인트 내역에 보이면 안 된다(입찰 자체는
// 라이브 경매 화면에서 이미 보여준다). BE가 아직 조회에서 걸러주지 않아(docs/requests/BE/042)
// FE에서 우선 제외한다 — 서버가 걸러주기 전까지는 페이지당 표시 건수가 size보다 적게 보일 수
// 있다(meta.totalElements는 걸러내기 전 값이라 완벽히 맞물리지 않음).
const HIDDEN_TRANSACTION_TYPES = new Set(['BID_HOLD', 'BID_RELEASE'])

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
      const visible = {
        ...data.data,
        content: data.data.content.filter((item) => !HIDDEN_TRANSACTION_TYPES.has(item.type)),
      }
      const orderTitles = await getOrderTitles(visible.content)
      return toPageResponse(visible, (item) => toPointTransaction(item, orderTitles))
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

/** 충전 준비(POINT-001) — 토스페이먼츠 결제위젯에 넘길 orderId/clientKey를 발급받는다. */
export const readyPointCharge = async (userId: number, amount: number): Promise<PointChargeReady> => {
  if (POINT_API_ENABLED) {
    const { data } = await http.post<ApiResponse<PointChargeReady>>(
      `/users/${userId}/points/charges/ready`,
      { amount },
    )

    if (data.data) {
      return data.data
    }
  }

  return { orderId: `mock-${Date.now()}`, amount, clientKey: '' }
}

/** 충전 승인(POINT-001) — 결제위젯이 돌려준 paymentKey로 토스 결제를 승인하고 잔액에 반영한다. */
export const confirmPointCharge = async (
  userId: number,
  request: PointChargeConfirmRequest,
): Promise<PointBalance> => {
  if (POINT_API_ENABLED) {
    const { data } = await http.post<ApiResponse<BackendPointBalanceResponse>>(
      `/users/${userId}/points/charges/confirm`,
      request,
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

// 결제/정산/환불(refType=ORDER)은 어떤 주문인지가 아니라 어떤 상품인지가 사용자에게 의미 있는
// 정보라, refId를 그대로 보여주는 대신 주문 상세에서 가져온 상품명을 memo에 채운다.
const toPointTransaction = (
  response: BackendPointTransactionResponse,
  orderTitles: Map<number, string>,
): PointTransaction => {
  const type = toPointTransactionType(response.type)
  const orderTitle =
    response.refType === 'ORDER' && response.refId != null
      ? orderTitles.get(response.refId)
      : undefined

  return {
    id: response.id,
    type,
    title: POINT_TRANSACTION_TITLES[type],
    amount: response.amount,
    balanceAfter: response.balanceAfter,
    status: 'COMPLETED',
    createdAt: response.createdAt,
    memo:
      orderTitle ??
      (response.refType && response.refId ? `${response.refType} #${response.refId}` : undefined),
  }
}

// refType=ORDER인 내역들의 상품명을 한 번에 조회한다. 같은 주문을 가리키는 항목(예: 구매 결제 +
// 이후 정산)이 있을 수 있어 refId 기준으로 중복 제거하고, 개별 조회 실패는 무시한다 — 상품명이
// 없으면 toPointTransaction이 `ORDER #123` 형태로 대체한다.
const getOrderTitles = async (
  items: BackendPointTransactionResponse[],
): Promise<Map<number, string>> => {
  const orderIds = [
    ...new Set(
      items
        .filter((item) => item.refType === 'ORDER' && item.refId != null)
        .map((item) => item.refId as number),
    ),
  ]

  if (orderIds.length === 0) {
    return new Map()
  }

  const results = await Promise.allSettled(orderIds.map((orderId) => getOrderDetail(orderId)))

  const titles = new Map<number, string>()
  results.forEach((result, index) => {
    if (result.status === 'fulfilled') {
      titles.set(orderIds[index], result.value.product.title)
    }
  })
  return titles
}

// BID_HOLD/BID_RELEASE는 getPointTransactions에서 이미 걸러낸 뒤 호출되므로 여기서는
// 다루지 않는다(들어와도 default로 안전하게 떨어진다).
const toPointTransactionType = (type: string): PointTransactionType => {
  switch (type) {
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
