import { http } from '@/shared/api/http'

import type {
  LiveBroadcastStatus,
  LiveCategory,
  LiveListDto,
  LiveListItem,
  LiveListMockScenario,
  LiveListQuery,
  LiveListViewData,
} from '@/domains/live/types/liveList.types'
import type { ApiResponse, PageResponse } from '@/shared/types/api.types'

interface BackendPageResponse<T> {
  content: T[]
  page: number
  size: number
  totalElements: number
  totalPages: number
  hasNext: boolean
}

const MOCK_DELAY_MS = 450
const LIVE_LIST_API_ENABLED = import.meta.env.VITE_LIVE_LIST_API_ENABLED !== 'false'
const PUBLIC_LIVE_STATUSES: LiveBroadcastStatus[] = ['LIVE', 'SCHEDULED']
const LIVE_CATEGORIES: LiveCategory[] = ['아우터', '상의', '하의', '가방', '신발', '액세서리']

export class LiveListContractError extends Error {
  constructor(message = '라이브 목록 응답 형식을 확인할 수 없습니다.') {
    super(message)
    this.name = 'LiveListContractError'
  }
}

const wait = (delay: number) =>
  new Promise<void>((resolve) => {
    window.setTimeout(resolve, delay)
  })

const isLiveCategory = (categoryName: string): categoryName is LiveCategory =>
  LIVE_CATEGORIES.includes(categoryName as LiveCategory)

const isPublicLiveStatus = (
  status: LiveListDto['broadcastStatus'],
): status is Exclude<LiveBroadcastStatus, 'ENDED'> =>
  PUBLIC_LIVE_STATUSES.includes(status as LiveBroadcastStatus)

const mapLiveListDto = (dto: LiveListDto): LiveListItem | null => {
  if (!isPublicLiveStatus(dto.broadcastStatus)) {
    return null
  }

  const categoryName = dto.categories?.[0]?.name ?? dto.categoryName ?? ''
  const category = isLiveCategory(categoryName) ? categoryName : null

  const broadcastAt = dto.broadcastStatus === 'LIVE' ? dto.startedAt : dto.scheduledAt

  if (!broadcastAt) {
    throw new LiveListContractError('방송 상태에 맞는 시작 시각이 없습니다.')
  }

  return {
    id: dto.liveId,
    title: dto.title,
    sellerName: dto.hostNickname,
    thumbnailUrl: dto.thumbnailUrl || '',
    status: dto.broadcastStatus,
    viewerCount: dto.viewerCount,
    category,
    broadcastAt,
  }
}

const requestLiveList = async (query: LiveListQuery): Promise<LiveListViewData> => {
  const response = await http.get<ApiResponse<PageResponse<LiveListDto> | BackendPageResponse<LiveListDto>>>(
    '/lives',
    {
      params: toLiveListParams(query),
      skipAuth: true,
    },
  )
  const responseBody = response.data

  if (!responseBody.success || !responseBody.data) {
    throw new LiveListContractError(responseBody.error?.message)
  }

  const pageResponse = normalizePageResponse(responseBody.data)

  return {
    items: pageResponse.items
      .map(mapLiveListDto)
      .filter((item): item is LiveListItem => item !== null),
    totalElements: pageResponse.meta.totalElements,
    totalPages: pageResponse.meta.totalPages,
  }
}

const toLiveListParams = (query: LiveListQuery) => ({
  categoryIds: query.categoryId,
  status: query.status,
  sort: query.sort,
  page: Math.max(query.page - 1, 0),
  size: query.size,
})

const normalizePageResponse = <T>(
  response: PageResponse<T> | BackendPageResponse<T>,
): PageResponse<T> => {
  if ('items' in response) {
    return response
  }

  return {
    items: response.content,
    meta: {
      page: response.page + 1,
      size: response.size,
      totalElements: response.totalElements,
      totalPages: response.totalPages,
    },
  }
}

const getEmptyLiveList = async (scenario: LiveListMockScenario): Promise<LiveListViewData> => {
  await wait(MOCK_DELAY_MS)

  if (scenario === 'error') {
    throw new Error('LIVE_LIST_ERROR')
  }

  return {
    items: [],
    totalElements: 0,
    totalPages: 0,
  }
}

export const getLiveListViewData = (
  query: LiveListQuery,
  scenario: LiveListMockScenario = 'default',
): Promise<LiveListViewData> => {
  if (LIVE_LIST_API_ENABLED) {
    return requestLiveList(query)
  }

  return getEmptyLiveList(scenario)
}

export const isLiveListApiEnabled = () => LIVE_LIST_API_ENABLED
