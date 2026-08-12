import type { ProductRegistrationPriceBucket } from '@/domains/product/types/productRegistration.types'

// AI 가격 추천(docs/requests/BE/028-pricing-async.md)의 comps_used 가격들을 만원 단위 지점별로
// 묶어 "가격대별 등록 상품 수" 점 그래프 데이터로 만든다. 각 지점은 구간(range)이 아니라
// 정확히 만원 단위 값(1, 2, 3...)이고, 그 지점에 반올림되는 comp 개수만큼 점이 쌓인다.
// 비어 있는 중간 지점도 축이 끊기지 않도록 0개짜리로 채운다.
const BUCKET_SIZE = 10_000

export const buildPriceRecommendationBuckets = (prices: number[]): ProductRegistrationPriceBucket[] => {
  if (prices.length === 0) {
    return []
  }

  const manValues = prices.map((price) => Math.round(price / BUCKET_SIZE))
  const minMan = Math.min(...manValues)
  const maxMan = Math.max(...manValues)
  const countByMan = new Map<number, number>()

  manValues.forEach((manValue) => {
    countByMan.set(manValue, (countByMan.get(manValue) ?? 0) + 1)
  })

  return Array.from({ length: maxMan - minMan + 1 }, (_, index) => {
    const manValue = minMan + index

    return {
      id: `point-${manValue}`,
      label: `${manValue}`,
      manValue,
      productCount: countByMan.get(manValue) ?? 0,
    }
  })
}
