export interface SellerAuctionConfig {
  startPrice: number
  increment: number
  durationSeconds: number
}

export interface SellerAuctionDurationPreset {
  label: string
  seconds: number
}
