import type {
  PointAccount,
  PointBalance,
  PointTransaction,
  PointTransactionType,
  WithdrawalHistory,
} from '@/domains/point/types/point.types'

// BE PointChargeRequest.amount는 @Min(10_000) — 결제위젯 준비(ready) 요청이 그 미만이면 400.
export const POINT_CHARGE_MIN_AMOUNT = 10_000
export const POINT_WITHDRAWAL_MIN_AMOUNT = 10_000
export const POINT_QUICK_CHARGE_AMOUNTS = [10_000, 30_000, 50_000, 100_000]

// 입찰 보류/해제(HOLD/HOLD_RELEASE)는 낙찰로 이어지지 않는 한 내역에 노출하지 않으므로
// 필터/라벨 목록에도 없다 — pointApi.ts의 getPointTransactions 참고.
export const POINT_TRANSACTION_FILTERS: Array<{
  id: PointTransactionType | 'ALL'
  label: string
}> = [
  { id: 'ALL', label: '전체' },
  { id: 'CHARGE', label: '충전' },
  { id: 'USE', label: '사용' },
  { id: 'SETTLEMENT', label: '정산' },
  { id: 'REFUND', label: '환불' },
  { id: 'WITHDRAWAL', label: '출금' },
]

export const POINT_TRANSACTION_TYPE_LABELS: Record<PointTransactionType, string> = {
  CHARGE: '충전',
  USE: '사용',
  SETTLEMENT: '정산',
  REFUND: '환불',
  WITHDRAWAL: '출금',
}

export const mockPointBalance: PointBalance = {
  available: 128_500,
  held: 42_000,
  escrow: 78_000,
  pendingSettlement: 156_000,
  withdrawalProcessing: 30_000,
  withdrawable: 128_500,
  lastChangedAt: '2026-08-01T14:20:00',
}

export const mockPointAccount: PointAccount = {
  bankName: '신한은행',
  accountNumber: '110-123-456789',
  holderName: '김서윤',
}

export const mockPointTransactions: PointTransaction[] = [
  {
    id: 101,
    type: 'CHARGE',
    title: '포인트 충전',
    amount: 50_000,
    balanceAfter: 128_500,
    status: 'COMPLETED',
    createdAt: '2026-08-01T14:20:00',
    memo: '카드 결제',
  },
  {
    id: 99,
    type: 'SETTLEMENT',
    title: '판매 정산',
    amount: 78_000,
    balanceAfter: 120_500,
    status: 'COMPLETED',
    createdAt: '2026-07-31T19:12:00',
    memo: '플리츠 스커트 판매',
  },
  {
    id: 98,
    type: 'WITHDRAWAL',
    title: '출금 신청',
    amount: -30_000,
    balanceAfter: 42_500,
    status: 'COMPLETED',
    createdAt: '2026-07-30T10:30:00',
    memo: '신한은행 110-***-456789',
  },
  {
    id: 97,
    type: 'REFUND',
    title: '주문 환불',
    amount: 22_500,
    balanceAfter: 72_500,
    status: 'COMPLETED',
    createdAt: '2026-07-29T16:45:00',
    memo: '상품 품절 환불',
  },
  {
    id: 96,
    type: 'USE',
    title: '상품 구매',
    amount: -36_000,
    balanceAfter: 50_000,
    status: 'COMPLETED',
    createdAt: '2026-07-28T11:24:00',
    memo: '울 블렌드 니트',
  },
  {
    id: 94,
    type: 'CHARGE',
    title: '포인트 충전',
    amount: 100_000,
    balanceAfter: 142_000,
    status: 'COMPLETED',
    createdAt: '2026-07-26T09:14:00',
    memo: '계좌이체',
  },
  {
    id: 93,
    type: 'WITHDRAWAL',
    title: '출금 신청',
    amount: -50_000,
    balanceAfter: 42_000,
    status: 'PENDING',
    createdAt: '2026-07-25T17:36:00',
    memo: '처리 중',
  },
  {
    id: 92,
    type: 'SETTLEMENT',
    title: '판매 정산 예정',
    amount: 64_000,
    balanceAfter: 92_000,
    status: 'PENDING',
    createdAt: '2026-07-24T15:05:00',
    memo: '구매 확정 대기',
  },
  {
    id: 91,
    type: 'CHARGE',
    title: '포인트 충전',
    amount: 30_000,
    balanceAfter: 28_000,
    status: 'COMPLETED',
    createdAt: '2026-07-23T12:40:00',
    memo: '간편결제',
  },
]

export const mockWithdrawalHistory: WithdrawalHistory[] = [
  {
    id: 12,
    amount: 30_000,
    fee: 0,
    status: 'COMPLETED',
    requestedAt: '2026-07-30T10:30:00',
    completedAt: '2026-07-31T09:10:00',
    account: mockPointAccount,
  },
]
