import { http } from '@/shared/api/http'

import type {
  FollowResponse,
  FollowUser,
  FollowUserPage,
  PublicProfile,
} from '@/domains/profile/types/profile.types'
import type { ApiResponse, PageMeta, PageResponse } from '@/shared/types/api.types'

interface BackendPageResponse<T> {
  content: T[]
  page: number
  size: number
  totalElements: number
  totalPages: number
  hasNext: boolean
}

export const getPublicProfile = async (userId: number): Promise<PublicProfile> => {
  const response = await http.get<ApiResponse<PublicProfile>>(`/users/${userId}/profile`)

  return unwrapApiData(response.data, '프로필 정보를 불러오지 못했습니다.')
}

export const followUser = async (userId: number): Promise<FollowResponse> => {
  const response = await http.post<ApiResponse<FollowResponse>>(`/users/${userId}/followers`)

  return unwrapApiData(response.data, '팔로우하지 못했습니다.')
}

export const unfollowUser = async (userId: number) => {
  await http.delete(`/users/${userId}/followers`)
}

export const getFollowers = async (
  userId: number,
  { page = 1, size = 20 }: { page?: number; size?: number } = {},
): Promise<FollowUserPage> => getFollowUsers(userId, 'followers', { page, size })

export const getFollowings = async (
  userId: number,
  { page = 1, size = 20 }: { page?: number; size?: number } = {},
): Promise<FollowUserPage> => getFollowUsers(userId, 'followings', { page, size })

const getFollowUsers = async (
  userId: number,
  path: 'followers' | 'followings',
  { page, size }: { page: number; size: number },
): Promise<FollowUserPage> => {
  const response = await http.get<ApiResponse<PageResponse<FollowUser> | BackendPageResponse<FollowUser>>>(
    `/users/${userId}/${path}`,
    {
      params: {
        page: Math.max(page - 1, 0),
        size,
      },
    },
  )
  const pageResponse = normalizePageResponse(
    unwrapApiData(response.data, '팔로우 목록을 불러오지 못했습니다.'),
  )

  return {
    items: pageResponse.items,
    meta: pageResponse.meta,
  }
}

const unwrapApiData = <T>(response: ApiResponse<T>, fallbackMessage: string) => {
  if (!response.success || !response.data) {
    throw new Error(response.error?.message ?? fallbackMessage)
  }

  return response.data
}

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
    } satisfies PageMeta,
  }
}

