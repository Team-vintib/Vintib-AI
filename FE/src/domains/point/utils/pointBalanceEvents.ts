import type { PointBalance } from '@/domains/point/types/point.types'

export const POINT_BALANCE_UPDATED_EVENT = 'point:balance-updated'

export interface PointBalanceUpdatedDetail {
  userId: number
  balance: PointBalance
}

export const dispatchPointBalanceUpdated = (detail: PointBalanceUpdatedDetail) => {
  window.dispatchEvent(
    new CustomEvent<PointBalanceUpdatedDetail>(POINT_BALANCE_UPDATED_EVENT, { detail }),
  )
}

export const isPointBalanceUpdatedEvent = (
  event: Event,
): event is CustomEvent<PointBalanceUpdatedDetail> =>
  event instanceof CustomEvent &&
  typeof event.detail?.userId === 'number' &&
  Boolean(event.detail.balance)
