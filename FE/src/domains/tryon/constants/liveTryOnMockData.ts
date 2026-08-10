import type { LiveTryOnMockResult } from '@/domains/tryon/types/liveTryOn.types'

const FIGMA_ASSET_BASE_URL = 'https://images.unsplash.com'

export const LIVE_TRY_ON_REGISTERED_PHOTO_URL =
  `${FIGMA_ASSET_BASE_URL}/photo-1500648767791-00dcc994a43e?w=700&h=900&fit=crop&crop=top`

// 실 API 미사용(비로그인/QA 시나리오) 폴백 mock — 등록 사진과 같은 이미지를 결과처럼 보여준다.
export const LIVE_TRY_ON_MOCK_RESULT: LiveTryOnMockResult = {
  imageUrl: LIVE_TRY_ON_REGISTERED_PHOTO_URL,
  fitTitle: '해당 사이즈는 살짝 큽니다.',
  fitDescription: '어깨와 가슴 부분, 소매 기장에 약간 여유 있는 핏이 예상됩니다.',
}

export const LIVE_TRY_ON_GENERATION_DELAY_MS = 1_200
