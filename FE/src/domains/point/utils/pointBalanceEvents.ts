import type { PointBalance } from '@/domains/point/types/point.types'

export const POINT_BALANCE_UPDATED_EVENT = 'point:balance-updated'
const BROADCAST_CHANNEL_NAME = 'point-balance'

export interface PointBalanceUpdatedDetail {
  userId: number
  balance: PointBalance
}

// 결제(충전)는 토스 결제 도메인으로 리다이렉트됐다가 성공/실패 콜백 페이지로 돌아오며
// 진행 탭이 완전히 새로고침된다. 같은 탭 안에서만 전달되는 CustomEvent만으로는 사용자가
// 별도로 열어둔 다른 탭(헤더 잔액 등)이 갱신되지 않는다. BroadcastChannel로 같은 오리진의
// 다른 탭에도 함께 알린다. BroadcastChannel 미지원 환경(구형 브라우저)에서는
// 같은 탭 CustomEvent만 동작한다.
const broadcastChannel =
  typeof BroadcastChannel === 'undefined' ? null : new BroadcastChannel(BROADCAST_CHANNEL_NAME)

export const dispatchPointBalanceUpdated = (detail: PointBalanceUpdatedDetail) => {
  window.dispatchEvent(
    new CustomEvent<PointBalanceUpdatedDetail>(POINT_BALANCE_UPDATED_EVENT, { detail }),
  )
  broadcastChannel?.postMessage(detail)
}

export const isPointBalanceUpdatedEvent = (
  event: Event,
): event is CustomEvent<PointBalanceUpdatedDetail> =>
  event instanceof CustomEvent &&
  typeof event.detail?.userId === 'number' &&
  Boolean(event.detail.balance)

const isPointBalanceUpdatedDetail = (data: unknown): data is PointBalanceUpdatedDetail =>
  Boolean(data) &&
  typeof data === 'object' &&
  typeof (data as PointBalanceUpdatedDetail).userId === 'number' &&
  Boolean((data as PointBalanceUpdatedDetail).balance)

/** 다른 탭에서 발생한 포인트 잔액 변경을 구독한다. 반환한 함수를 호출하면 구독을 해제한다. */
export const subscribePointBalanceUpdatedAcrossTabs = (
  handler: (detail: PointBalanceUpdatedDetail) => void,
) => {
  if (!broadcastChannel) {
    return () => {}
  }

  const listener = (event: MessageEvent<unknown>) => {
    if (isPointBalanceUpdatedDetail(event.data)) {
      handler(event.data)
    }
  }

  broadcastChannel.addEventListener('message', listener)
  return () => broadcastChannel.removeEventListener('message', listener)
}
