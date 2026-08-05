import axios from 'axios'

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

const mapLiveProductDto = (dto: LiveProductDto): LiveWatchProduct => ({
  id: dto.productId,
  title: dto.productTitle,
  brandName: dto.brandName ?? null,
  price: dto.price ?? null,
  thumbnailUrl: dto.thumbnailUrl ?? null,
  saleType: dto.saleType ?? null,
  // material·measurements·defectSummary는 LiveProductResponse에 없음(BE 016 §6-B).
  // 필요 시 상품 상세(GET /products/{id})에서 상세 패널로 가져온다.
  material: null,
  condition: dto.conditionGrade ?? null,
  measurements: null,
  defectSummary: null,
})

const mapLiveDetailDto = (dto: LiveDetailDto): LiveWatchViewData => ({
  id: dto.id,
  hostId: dto.hostId,
  hostNickname: dto.hostNickname,
  hostProfileImageUrl: dto.hostProfileImageUrl ?? null,
  isHost: dto.isHost ?? false,
  isReminderSet: dto.isReminderSet ?? false,
  title: dto.title,
  description: dto.description ?? null,
  posterUrl: dto.thumbnailUrl || null,
  status: dto.status,
  scheduledAt: dto.scheduledAt,
  startedAt: dto.startedAt,
  endedAt: dto.endedAt,
  currentViewerCount: dto.currentViewerCount ?? null,
  peakViewerCount: dto.peakViewerCount,
  currentProductId: dto.currentProductId ?? null,
  products: [...dto.products]
    .sort((first, second) => first.sortOrder - second.sortOrder)
    .map(mapLiveProductDto),
  categories: dto.categories ?? [],
})

const requestLiveWatch = async (liveId: number): Promise<LiveWatchViewData> => {
  try {
    // skipAuth 없음: 로그인 상태면 토큰이 붙어 isHost/isReminderSet가 채워지고,
    // 비회원은 토큰 없이 공개 조회되어 두 값 모두 false로 온다 (BE 016 §2.2).
    const response = await http.get<ApiResponse<LiveDetailDto>>(`/lives/${liveId}`)
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

const getEmptyLiveWatch = async (
  liveId: number,
  scenario: LiveWatchMockScenario,
): Promise<LiveWatchViewData> => {
  await wait(MOCK_DELAY_MS)

  if (scenario === 'error') {
    throw new Error('LIVE_WATCH_ERROR')
  }

  if (scenario === 'not-found') {
    throw new LiveWatchNotFoundError()
  }

  return {
    id: liveId,
    hostId: 0,
    hostNickname: '',
    hostProfileImageUrl: null,
    isHost: false,
    isReminderSet: false,
    title: '',
    description: null,
    posterUrl: null,
    status: 'ENDED',
    scheduledAt: null,
    startedAt: null,
    endedAt: null,
    currentViewerCount: null,
    peakViewerCount: 0,
    currentProductId: null,
    products: [],
    categories: [],
  }
}

export const getLiveWatchViewData = (
  liveId: number,
  scenario: LiveWatchMockScenario = 'default',
): Promise<LiveWatchViewData> => {
  if (LIVE_WATCH_API_ENABLED) {
    return requestLiveWatch(liveId)
  }

  return getEmptyLiveWatch(liveId, scenario)
}

export const isLiveWatchApiEnabled = () => LIVE_WATCH_API_ENABLED

export interface LiveReminderResult {
  liveId: number
  isReminderSet: boolean
}

const unwrapReminderResult = (body: ApiResponse<LiveReminderResult>): LiveReminderResult => {
  if (!body.success || !body.data) {
    throw new Error(body.error?.message ?? '알림 설정을 변경하지 못했습니다.')
  }

  return body.data
}

// 예약 라이브 시작 알림 신청/취소 (BE 016 §5). 인증 필요.
// 같은 상태로 두 번 호출해도 200이므로 응답의 isReminderSet로 토글 상태를 확정한다.
export const registerLiveReminder = async (liveId: number): Promise<LiveReminderResult> => {
  const { data } = await http.post<ApiResponse<LiveReminderResult>>(`/lives/${liveId}/reminders`)

  return unwrapReminderResult(data)
}

export const cancelLiveReminder = async (liveId: number): Promise<LiveReminderResult> => {
  const { data } = await http.delete<ApiResponse<LiveReminderResult>>(`/lives/${liveId}/reminders`)

  return unwrapReminderResult(data)
}
