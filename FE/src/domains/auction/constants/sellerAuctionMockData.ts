import type {
  SellerAuctionConfig,
  SellerAuctionDurationPreset,
} from '@/domains/auction/types/sellerAuction.types'

// 아래 프리셋·기본값·범위는 계약 미확정 → Mock 전용(BE 확인 필요).
// 진행 시간/증액 단위 프리셋(사용자 결정: 프리셋 + 직접 입력 병행).
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

// 진행 시간/증액 단위 직접 입력 허용 범위(Mock).
export const SELLER_AUCTION_DURATION_RANGE = { min: 10, max: 3_600 }
