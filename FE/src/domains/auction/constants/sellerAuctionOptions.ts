import type {
  SellerAuctionConfig,
  SellerAuctionDurationPreset,
} from '@/domains/auction/types/sellerAuction.types'

// 서버는 양수 진행 시간·증액 단위를 받는다. 아래 값은 빠른 입력을 위한 FE 프리셋이다.
export const SELLER_AUCTION_DURATION_PRESETS: SellerAuctionDurationPreset[] = [
  { label: '1분', seconds: 60 },
  { label: '3분', seconds: 180 },
  { label: '5분', seconds: 300 },
]

export const SELLER_AUCTION_INCREMENT_PRESETS: number[] = [1_000, 5_000, 10_000]

export const SELLER_AUCTION_DEFAULT_CONFIG: Pick<
  SellerAuctionConfig,
  'increment' | 'durationSeconds'
> = {
  increment: 1_000,
  durationSeconds: 180,
}

// 시작가 직접 입력 시 fallback 기본값(선택 상품 가격이 없을 때).
export const SELLER_AUCTION_DEFAULT_START_PRICE = 10_000

export const SELLER_AUCTION_MIN_DURATION_SECONDS = 1
