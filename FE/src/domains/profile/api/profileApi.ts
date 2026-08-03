import { http } from '@/shared/api/http'

import type {
  FollowResponse,
  FollowUser,
  FollowUserPage,
  ProfileImageKind,
  ProfileImageUploadUrl,
  ProfileMutationResult,
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

export const updateProfileBio = async (
  userId: number,
  description: string,
): Promise<ProfileMutationResult> => {
  const response = await http.patch<ApiResponse<ProfileMutationResult>>(`/users/${userId}/bio`, {
    description,
  })

  return unwrapApiData(response.data, '소개글을 저장하지 못했습니다.')
}

export const uploadProfileImage = async (
  userId: number,
  kind: ProfileImageKind,
  file: File,
): Promise<ProfileMutationResult> => {
  const contentType = file.type || 'application/octet-stream'
  const resourceName = kind === 'profile' ? 'profile-image' : 'cover-image'
  const uploadUrlResponse = await http.post<ApiResponse<ProfileImageUploadUrl>>(
    `/users/${userId}/${resourceName}/upload-url`,
    { contentType },
  )
  const uploadUrl = unwrapApiData(
    uploadUrlResponse.data,
    kind === 'profile'
      ? '프로필 이미지 업로드 URL을 발급하지 못했습니다.'
      : '커버 이미지 업로드 URL을 발급하지 못했습니다.',
  )

  const uploadResponse = await fetch(uploadUrl.uploadUrl, {
    method: 'PUT',
    headers: {
      'Content-Type': contentType,
    },
    body: file,
  })

  if (!uploadResponse.ok) {
    throw new Error(kind === 'profile' ? '프로필 이미지를 업로드하지 못했습니다.' : '커버 이미지를 업로드하지 못했습니다.')
  }

  const confirmResponse = await http.put<ApiResponse<ProfileMutationResult>>(
    `/users/${userId}/${resourceName}`,
    { key: uploadUrl.key },
  )

  return unwrapApiData(
    confirmResponse.data,
    kind === 'profile' ? '프로필 이미지를 저장하지 못했습니다.' : '커버 이미지를 저장하지 못했습니다.',
  )
}

export const deleteProfileImage = async (
  userId: number,
  kind: ProfileImageKind,
) => {
  const resourceName = kind === 'profile' ? 'profile-image' : 'cover-image'

  await http.delete(`/users/${userId}/${resourceName}`)
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
