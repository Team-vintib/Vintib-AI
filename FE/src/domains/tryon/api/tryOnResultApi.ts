import { TRYON_RESULT_MOCK_DATA } from '@/domains/tryon/constants/tryOnResultMockData'
import { http } from '@/shared/api/http'

import type { TryOnResult } from '@/domains/tryon/types/tryOnResult.types'
import type { ApiResponse } from '@/shared/types/api.types'

const TRYON_API_ENABLED = import.meta.env.VITE_TRYON_API_ENABLED === 'true'

// BE 응답: 시착 결과에는 아직 카테고리가 없다(→ docs/requests/BE/020). category는 null로 둔다.
interface TryOnResultDto {
  id: number
  productId: number
  imageUrl: string
  createdAt: string
}

const toTryOnResult = (dto: TryOnResultDto): TryOnResult => ({
  id: dto.id,
  productId: dto.productId,
  imageUrl: dto.imageUrl,
  createdAt: dto.createdAt,
  category: null,
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
    return TRYON_RESULT_MOCK_DATA.map((result) => ({ ...result }))
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
    const found = TRYON_RESULT_MOCK_DATA.find((result) => result.id === resultId)

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

export const deleteTryOnResult = async (
  userId: number | null | undefined,
  resultId: number,
): Promise<void> => {
  if (!TRYON_API_ENABLED) {
    return
  }

  const requiredUserId = getRequiredUserId(userId)
  await http.delete(`/users/${requiredUserId}/tryons/${resultId}`)
}
