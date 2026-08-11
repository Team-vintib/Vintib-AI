import tryOnHardcodedResult from '@/assets/images/tryon/싸피_후드집업_트라이온.png'
import type { LiveTryOnMockResult } from '@/domains/tryon/types/liveTryOn.types'

const FIGMA_ASSET_BASE_URL = 'https://images.unsplash.com'

export const LIVE_TRY_ON_REGISTERED_PHOTO_URL =
  `${FIGMA_ASSET_BASE_URL}/photo-1500648767791-00dcc994a43e?w=700&h=900&fit=crop&crop=top`

// 임시: 실제 생성 결과 대신 하드코딩된 샘플 이미지를 노출한다(상품 상세·라이브 공통, LiveTryOnPanel.vue).
export const LIVE_TRY_ON_MOCK_RESULT: LiveTryOnMockResult = {
  imageUrl: tryOnHardcodedResult,
  fitTitle: '해당 사이즈는 살짝 큽니다.',
  fitDescription: '어깨와 가슴 부분, 소매 기장에 약간 여유 있는 핏이 예상됩니다.',
}

export const LIVE_TRY_ON_GENERATION_DELAY_MS = 1_200
