import axios from 'axios'

import {
  getLiveWatchMockData,
  LIVE_WATCH_FALLBACK_PRODUCT_IMAGES,
  LIVE_WATCH_POSTER_URL,
} from '@/domains/live/constants/liveWatchMockData'
import { http } from '@/shared/api/http'

import type {
  LiveDetailDto,
  LiveProductDto,
  LiveWatchMockScenario,
  LiveWatchProduct,
  LiveWatchViewData,
} from '@/domains/live/types/liveWatch.types'
import type { ApiResponse } from '@/shared/types/api.types'

const MOCK_DELAY_MS = 450
const LIVE_WATCH_API_ENABLED = import.meta.env.VITE_LIVE_WATCH_API_ENABLED === 'true'

export class LiveWatchContractError extends Error {
  constructor(message = '라이브 시청 정보 응답 형식을 확인할 수 없습니다.') {
    super(message)
    this.name = 'LiveWatchContractError'
  }
}

export class LiveWatchNotFoundError extends Error {
  constructor(message = '라이브 방송을 찾을 수 없습니다.') {
    super(message)
    this.name = 'LiveWatchNotFoundError'
  }
}

const wait = (delay: number) =>
  new Promise<void>((resolve) => {
    window.setTimeout(resolve, delay)
  })

const mapLiveProductDto = (dto: LiveProductDto, index: number): LiveWatchProduct => ({
  id: dto.productId,
  title: dto.productTitle,
  brandName: null,
  price: null,
  thumbnailUrl:
    LIVE_WATCH_FALLBACK_PRODUCT_IMAGES[index % LIVE_WATCH_FALLBACK_PRODUCT_IMAGES.length] ?? null,
  saleType: null,
  material: null,
  condition: null,
  measurements: null,
  defectSummary: null,
})

const mapLiveDetailDto = (dto: LiveDetailDto): LiveWatchViewData => ({
  id: dto.id,
  hostId: dto.hostId,
  hostNickname: dto.hostNickname,
  hostProfileImageUrl: null,
  title: dto.title,
  description: null,
  posterUrl: dto.thumbnailUrl || LIVE_WATCH_POSTER_URL,
  status: dto.status,
  scheduledAt: dto.scheduledAt,
  startedAt: dto.startedAt,
  endedAt: dto.endedAt,
  currentViewerCount: dto.currentViewerCount ?? null,
  peakViewerCount: dto.peakViewerCount,
  currentProductId: null,
  products: [...dto.products]
    .sort((first, second) => first.sortOrder - second.sortOrder)
    .map(mapLiveProductDto),
  categories: dto.categories ?? [],
})

const requestLiveWatch = async (liveId: number): Promise<LiveWatchViewData> => {
  try {
    const response = await http.get<ApiResponse<LiveDetailDto>>(`/lives/${liveId}`, {
      skipAuth: true,
    })
    const responseBody = response.data

    if (!responseBody.success || !responseBody.data) {
      if (responseBody.error?.code === 'LIVE_NOT_FOUND') {
        throw new LiveWatchNotFoundError(responseBody.error.message)
      }

      throw new LiveWatchContractError(responseBody.error?.message)
    }

    return mapLiveDetailDto(responseBody.data)
  } catch (error) {
    if (axios.isAxiosError(error) && error.response?.status === 404) {
      throw new LiveWatchNotFoundError()
    }

    throw error
  }
}

const getMockLiveWatch = async (
  scenario: LiveWatchMockScenario,
): Promise<LiveWatchViewData> => {
  await wait(MOCK_DELAY_MS)

  if (scenario === 'error') {
    throw new Error('LIVE_WATCH_MOCK_ERROR')
  }

  if (scenario === 'not-found') {
    throw new LiveWatchNotFoundError()
  }

  return getLiveWatchMockData(scenario)
}

export const getLiveWatchViewData = (
  liveId: number,
  scenario: LiveWatchMockScenario = 'default',
): Promise<LiveWatchViewData> => {
  if (LIVE_WATCH_API_ENABLED) {
    return requestLiveWatch(liveId)
  }

  return getMockLiveWatch(scenario)
}

export const isLiveWatchApiEnabled = () => LIVE_WATCH_API_ENABLED
