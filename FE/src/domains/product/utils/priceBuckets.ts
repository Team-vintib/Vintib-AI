import type { ProductRegistrationPriceBucket } from '@/domains/product/types/productRegistration.types'

// AI 가격 추천(docs/requests/BE/028-pricing-async.md)의 comps_used 가격들을 구간별로 묶어
// "가격대별 등록 상품 수" 히스토그램 데이터로 만든다. comps 수가 적을 수 있어(mock 기준 3~5건)
// 구간 개수를 comps 수 이하로 제한한다.
export const buildPriceRecommendationBuckets = (prices: number[]): ProductRegistrationPriceBucket[] => {
  if (prices.length === 0) {
    return []
  }

  const min = Math.min(...prices)
  const max = Math.max(...prices)

  if (min === max) {
    return [{ id: 'single', label: `${Math.round(min / 10_000)}만`, productCount: prices.length }]
  }

  const bucketCount = Math.min(5, prices.length)
  const bucketSize = (max - min) / bucketCount
  const buckets: ProductRegistrationPriceBucket[] = Array.from({ length: bucketCount }, (_, index) => {
    const bucketMin = min + bucketSize * index
    const bucketMax = index === bucketCount - 1 ? max : bucketMin + bucketSize

    return {
      id: `bucket-${index}`,
      label: `${Math.round(bucketMin / 10_000)}~${Math.round(bucketMax / 10_000)}만`,
      productCount: 0,
    }
  })

  prices.forEach((price) => {
    const bucketIndex = Math.min(bucketCount - 1, Math.floor((price - min) / bucketSize))
    buckets[bucketIndex].productCount += 1
  })

  return buckets
}
