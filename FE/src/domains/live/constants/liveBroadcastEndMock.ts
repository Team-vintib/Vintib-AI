import type { LiveWatchProduct } from '@/domains/live/types/liveWatch.types'

// 방송 종료 대시보드(438)의 상품별 결과·집계 뷰모델.
// 실제 경매 결과/방송 요약 API는 없음(docs/requests/BE/009, 013) → 전부 Mock 전용.

export type BroadcastProductOutcome = 'WON' | 'UNSOLD' | 'NOT_AUCTIONED'

export interface BroadcastProductResult {
  productId: number
  title: string
  outcome: BroadcastProductOutcome
  winnerNickname: string | null
  finalPrice: number | null
}

export interface BroadcastEndSummary {
  productCount: number
  soldCount: number
  unsoldCount: number
  totalSales: number
  results: BroadcastProductResult[]
}

const MOCK_WINNERS = ['vintage_hunter', 'archive_king', 'fashion_kim', 'seoul_thrift']
const MOCK_UNSOLD_FALLBACK_PRICE = 30_000

// Mock 전용: 실제 경매 결과가 없어 연결 상품 목록으로 그럴듯한 요약을 만든다.
// allSold=true면 전부 낙찰(미낙찰 처리 섹션 숨김 확인용).
export const buildBroadcastEndSummary = (
  products: LiveWatchProduct[],
  allSold = false,
): BroadcastEndSummary => {
  const results: BroadcastProductResult[] = products.map((product, index) => {
    const won = allSold || index % 2 === 0
    const basePrice = product.price ?? MOCK_UNSOLD_FALLBACK_PRICE

    return {
      productId: product.id,
      title: product.title,
      outcome: won ? 'WON' : 'UNSOLD',
      winnerNickname: won ? (MOCK_WINNERS[index % MOCK_WINNERS.length] ?? null) : null,
      finalPrice: won ? basePrice + index * 5_000 : null,
    }
  })

  const soldCount = results.filter((result) => result.outcome === 'WON').length
  const unsoldCount = results.filter((result) => result.outcome === 'UNSOLD').length
  const totalSales = results.reduce((sum, result) => sum + (result.finalPrice ?? 0), 0)

  return { productCount: products.length, soldCount, unsoldCount, totalSales, results }
}
