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

// AUCT-010 종료 직전 자동 연장(Mock 연출). 실제 연장 판정·값은 BE 몫.
export const SELLER_AUCTION_EXTEND_THRESHOLD_SECONDS = 3
export const SELLER_AUCTION_EXTEND_SECONDS = 5

// 진행 중 mock 입찰을 만드는 가짜 경쟁자. 실제 최고 입찰자는 BE 선착순 판정 결과로 대체.
export const SELLER_AUCTION_MOCK_COMPETITORS = [
  'bidder_99',
  'vintage_lover',
  'archive_king',
  'fashion_kim',
]

// mock 입찰 주기(초). 진행 시간 동안 이 간격마다 가짜 입찰이 들어온다.
export const SELLER_AUCTION_MOCK_BID_INTERVAL_SECONDS = 4
