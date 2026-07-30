import type { LiveTryOnMockResult } from '@/domains/tryon/types/liveTryOn.types'

const FIGMA_ASSET_BASE_URL = 'https://images.unsplash.com'

export const LIVE_TRY_ON_REGISTERED_PHOTO_URL =
  `${FIGMA_ASSET_BASE_URL}/photo-1500648767791-00dcc994a43e?w=700&h=900&fit=crop&crop=top`

export const LIVE_TRY_ON_MOCK_RESULT: LiveTryOnMockResult = {
  imageUrl:
    `${FIGMA_ASSET_BASE_URL}/photo-1552902865-b72c031ac5ea?w=700&h=900&fit=crop&crop=top`,
  fitTitle: 'M 사이즈가 적합합니다.',
  fitDescription: '어깨와 가슴 부분에 약간 여유 있는 핏이 예상됩니다.',
}

export const LIVE_TRY_ON_GENERATION_DELAY_MS = 1_200
