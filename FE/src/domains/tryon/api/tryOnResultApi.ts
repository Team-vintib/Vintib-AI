import { TRYON_RESULT_MOCK_DATA } from '@/domains/tryon/constants/tryOnResultMockData'
import { http } from '@/shared/api/http'

import type { TryOnGenerationStatus, TryOnResult } from '@/domains/tryon/types/tryOnResult.types'
import type { ApiResponse } from '@/shared/types/api.types'

const TRYON_API_ENABLED = import.meta.env.VITE_TRYON_API_ENABLED === 'true'
const MOCK_STORAGE_PREFIX = 'vidtib:mock-tryon-results'

export class TryOnResultSaveUnavailableError extends Error {
  constructor() {
    super('AI 시착 생성·저장 API 연결을 기다리고 있습니다.')
    this.name = 'TryOnResultSaveUnavailableError'
  }
}

export class TryOnGenerationUnavailableError extends Error {
  constructor() {
    super('실제 AI 시착 생성은 mock 모드에서 지원하지 않습니다.')
    this.name = 'TryOnGenerationUnavailableError'
  }
}

// BE 응답: 시착 결과에는 아직 카테고리가 없다(→ docs/requests/BE/020). category는 null로 둔다.
interface TryOnResultDto {
  id: number
  productId: number
  status?: TryOnGenerationStatus
  imageUrl: string | null
  fitTitle?: string | null
  fitDescription?: string | null
  createdAt: string
}

const toTryOnResult = (dto: TryOnResultDto): TryOnResult => ({
  id: dto.id,
  productId: dto.productId,
  status: dto.status,
  imageUrl: dto.imageUrl,
  createdAt: dto.createdAt,
  category: null,
  fitTitle: dto.fitTitle ?? null,
  fitDescription: dto.fitDescription ?? null,
})

const unwrapApiData = <T>(response: ApiResponse<T>, fallbackMessage: string) => {
  if (!response.success || response.data === null) {
    throw new Error(response.error?.message ?? fallbackMessage)
  }

  return response.data
}

const getRequiredUserId = (userId?: number | null) => {
  if (!userId) {
    throw new Error('시착 결과를 조회할 회원 ID가 없습니다.')
  }

  return userId
}

export const getMyTryOnResults = async (userId?: number | null): Promise<TryOnResult[]> => {
  if (!TRYON_API_ENABLED) {
    return readMockResults(userId)
  }

  const requiredUserId = getRequiredUserId(userId)
  const response = await http.get<ApiResponse<TryOnResultDto[]>>(
    `/users/${requiredUserId}/tryons`,
  )

  return unwrapApiData(response.data, '시착 결과를 불러오지 못했습니다.').map(toTryOnResult)
}

export const getTryOnResultDetail = async (
  userId: number | null | undefined,
  resultId: number,
): Promise<TryOnResult> => {
  if (!TRYON_API_ENABLED) {
    const found = readMockResults(userId).find((result) => result.id === resultId)

    if (!found) {
      throw new Error('시착 결과를 찾을 수 없습니다.')
    }

    return { ...found }
  }

  const requiredUserId = getRequiredUserId(userId)
  const response = await http.get<ApiResponse<TryOnResultDto>>(
    `/users/${requiredUserId}/tryons/${resultId}`,
  )

  return toTryOnResult(unwrapApiData(response.data, '시착 결과를 불러오지 못했습니다.'))
}

// AI 시착 job을 접수한다(비동기) — 응답은 접수증(status=PENDING)이지 완성된 결과가 아니다.
// 완료 여부는 getTryOnResultDetail()로 폴링해서 확인한다.
export const createTryOnResult = async (
  userId: number | null | undefined,
  productId: number,
): Promise<TryOnResult> => {
  if (!TRYON_API_ENABLED) {
    throw new TryOnGenerationUnavailableError()
  }

  const requiredUserId = getRequiredUserId(userId)
  const response = await http.post<ApiResponse<TryOnResultDto>>(
    `/users/${requiredUserId}/tryons`,
    undefined,
    { params: { productId } },
  )

  return toTryOnResult(unwrapApiData(response.data, 'AI 시착 생성 요청에 실패했습니다.'))
}

export const deleteTryOnResult = async (
  userId: number | null | undefined,
  resultId: number,
): Promise<void> => {
  if (!TRYON_API_ENABLED) {
    writeMockResults(
      userId,
      readMockResults(userId).filter((result) => result.id !== resultId),
    )
    return
  }

  const requiredUserId = getRequiredUserId(userId)
  await http.delete(`/users/${requiredUserId}/tryons/${resultId}`)
}

export const saveTryOnResult = async (
  userId: number | null | undefined,
  result: TryOnResult,
): Promise<TryOnResult> => {
  if (TRYON_API_ENABLED) {
    // BE에는 GET/DELETE만 있고 생성 이미지를 저장할 POST endpoint가 아직 없다.
    throw new TryOnResultSaveUnavailableError()
  }

  const savedResult = { ...result }
  const previous = readMockResults(userId).filter((item) => item.id !== result.id)
  writeMockResults(userId, [savedResult, ...previous])
  return savedResult
}

export const isTryOnResultApiEnabled = () => TRYON_API_ENABLED

const getMockStorageKey = (userId?: number | null) =>
  `${MOCK_STORAGE_PREFIX}:${userId ?? 'guest'}`

const readMockResults = (userId?: number | null): TryOnResult[] => {
  if (typeof window === 'undefined') {
    return TRYON_RESULT_MOCK_DATA.map((result) => ({ ...result }))
  }

  try {
    const stored = window.localStorage.getItem(getMockStorageKey(userId))
    if (!stored) {
      return TRYON_RESULT_MOCK_DATA.map((result) => ({ ...result }))
    }

    const parsed: unknown = JSON.parse(stored)
    if (!Array.isArray(parsed)) {
      return TRYON_RESULT_MOCK_DATA.map((result) => ({ ...result }))
    }

    return parsed.filter(isTryOnResult).map((result) => ({ ...result }))
  } catch {
    return TRYON_RESULT_MOCK_DATA.map((result) => ({ ...result }))
  }
}

const writeMockResults = (userId: number | null | undefined, results: TryOnResult[]) => {
  if (typeof window === 'undefined') return

  window.localStorage.setItem(getMockStorageKey(userId), JSON.stringify(results))
}

const isTryOnResult = (value: unknown): value is TryOnResult =>
  Boolean(
    value &&
      typeof value === 'object' &&
      'id' in value &&
      'productId' in value &&
      'imageUrl' in value &&
      'createdAt' in value &&
      typeof value.id === 'number' &&
      typeof value.productId === 'number' &&
      typeof value.imageUrl === 'string' &&
      typeof value.createdAt === 'string',
  )
