import {
  deleteMockDefaultTryOnImage,
  readImageFileAsDataUrl,
  readMockProfileMedia,
  saveMockDefaultTryOnImage,
} from '@/shared/api/mockProfileMediaStorage'
import { http } from '@/shared/api/http'
import axios from 'axios'

import { EMPTY_TRYON_PROFILE } from '@/domains/tryon/constants/tryOnProfileMockData'
import type { SaveTryOnProfileRequest, TryOnProfile } from '@/domains/tryon/types/tryOnProfile.types'
import type { ApiResponse } from '@/shared/types/api.types'

const TRYON_API_ENABLED = import.meta.env.VITE_TRYON_API_ENABLED === 'true'
const STORAGE_KEY = 'vidtib:mock-tryon-profile'
const FALLBACK_USER_KEY = 'current'

type TryOnProfileMap = Record<string, Partial<TryOnProfile>>

interface TryOnProfileUpdateRequest {
  bodyPhotoKey?: string
  heightCm?: number
  weightKg?: number
  chest?: number
  waist?: number
  hip?: number
}

interface TryOnProfileUploadUrlResponse {
  key: string
  uploadUrl: string
  expiresInSeconds: number
}

const getUserKey = (userId?: number | null) => (userId ? String(userId) : FALLBACK_USER_KEY)

export const getMyTryOnProfile = async (userId?: number | null): Promise<TryOnProfile> => {
  if (!TRYON_API_ENABLED) {
    return readMockTryOnProfile(userId)
  }

  const requiredUserId = getRequiredUserId(userId)

  try {
    const response = await http.get<ApiResponse<Omit<TryOnProfile, 'id'>>>(`/users/${requiredUserId}/tryon`)
    return toTryOnProfile(unwrapApiData(response.data, 'AI 시착 정보를 불러오지 못했습니다.'))
  } catch (error) {
    if (isNotFoundError(error)) {
      return { ...EMPTY_TRYON_PROFILE }
    }

    throw error
  }
}

export const saveMyTryOnProfile = async (
  request: SaveTryOnProfileRequest,
  userId?: number | null,
): Promise<TryOnProfile> => {
  if (!TRYON_API_ENABLED) {
    return saveMockTryOnProfile(request, userId)
  }

  const requiredUserId = getRequiredUserId(userId)
  const body: TryOnProfileUpdateRequest = {}
  
  if (request.bodyPhoto) {
    body.bodyPhotoKey = await uploadTryOnBodyPhoto(requiredUserId, request.bodyPhoto)
  }

  appendOptionalNumber(body, 'heightCm', request.heightCm)
  appendOptionalNumber(body, 'weightKg', request.weightKg)
  appendOptionalNumber(body, 'chest', request.chest)
  appendOptionalNumber(body, 'waist', request.waist)
  appendOptionalNumber(body, 'hip', request.hip)

  const response = await http.put<ApiResponse<Omit<TryOnProfile, 'id'>>>(`/users/${requiredUserId}/tryon`, body)

  return toTryOnProfile(unwrapApiData(response.data, 'AI 시착 정보를 저장하지 못했습니다.'))
}

export const deleteMyTryOnProfile = async (userId?: number | null): Promise<TryOnProfile> => {
  if (!TRYON_API_ENABLED) {
    deleteMockDefaultTryOnImage(userId)
    writeMockTryOnProfile(userId, { ...EMPTY_TRYON_PROFILE, updatedAt: new Date().toISOString() })
    return readMockTryOnProfile(userId)
  }

  const requiredUserId = getRequiredUserId(userId)
  try {
    await http.delete(`/users/${requiredUserId}/tryon`)
  } catch (error) {
    if (!isNotFoundError(error)) {
      throw error
    }
  }
  return { ...EMPTY_TRYON_PROFILE, updatedAt: new Date().toISOString() }
}

export const isTryOnApiEnabled = () => TRYON_API_ENABLED

const uploadTryOnBodyPhoto = async (userId: number, file: File) => {
  const uploadUrlResponse = await http.post<ApiResponse<TryOnProfileUploadUrlResponse>>(
    `/users/${userId}/tryon/upload-url`,
    { contentType: file.type || 'application/octet-stream' },
  )
  const uploadUrl = unwrapApiData(uploadUrlResponse.data, 'AI 시착용 사진 업로드 URL을 발급하지 못했습니다.')

  const uploadResponse = await fetch(uploadUrl.uploadUrl, {
    method: 'PUT',
    headers: {
      'Content-Type': file.type || 'application/octet-stream',
    },
    body: file,
  })

  if (!uploadResponse.ok) {
    throw new Error('AI 시착용 사진을 업로드하지 못했습니다.')
  }

  return uploadUrl.key
}

const appendOptionalNumber = (
  body: TryOnProfileUpdateRequest,
  key: keyof Omit<TryOnProfileUpdateRequest, 'bodyPhotoKey'>,
  value?: string,
) => {
  const trimmedValue = value?.trim()

  if (trimmedValue) {
    body[key] = Number(trimmedValue)
  }
}

const getRequiredUserId = (userId?: number | null) => {
  if (!userId) {
    throw new Error('AI 시착 정보를 저장할 회원 ID가 없습니다.')
  }

  return userId
}

const toTryOnProfile = (response: Omit<TryOnProfile, 'id'>): TryOnProfile => ({
  ...response,
  id: null,
})

const isNotFoundError = (error: unknown) =>
  axios.isAxiosError(error) && error.response?.status === 404

const saveMockTryOnProfile = async (
  request: SaveTryOnProfileRequest,
  userId?: number | null,
): Promise<TryOnProfile> => {
  const currentProfile = readMockTryOnProfile(userId)
  let bodyPhotoUrl = currentProfile.bodyPhotoUrl

  if (request.removeBodyPhoto) {
    bodyPhotoUrl = null
    deleteMockDefaultTryOnImage(userId)
  } else if (request.bodyPhoto) {
    bodyPhotoUrl = await readImageFileAsDataUrl(request.bodyPhoto, 'AI 시착용 사진을 읽지 못했습니다.')
    saveMockDefaultTryOnImage(userId, bodyPhotoUrl)
  }

  const nextProfile: TryOnProfile = {
    id: currentProfile.id ?? 1,
    bodyPhotoUrl,
    heightCm: toOptionalNumber(request.heightCm),
    weightKg: toOptionalNumber(request.weightKg),
    chest: toOptionalNumber(request.chest),
    waist: toOptionalNumber(request.waist),
    hip: toOptionalNumber(request.hip),
    updatedAt: new Date().toISOString(),
  }

  writeMockTryOnProfile(userId, nextProfile)
  return nextProfile
}

const readMockTryOnProfile = (userId?: number | null): TryOnProfile => {
  const profileMap = readAllMockTryOnProfiles()
  const storedProfile = {
    ...profileMap[FALLBACK_USER_KEY],
    ...profileMap[getUserKey(userId)],
  }
  const media = readMockProfileMedia(userId)

  return {
    ...EMPTY_TRYON_PROFILE,
    ...storedProfile,
    bodyPhotoUrl: storedProfile.bodyPhotoUrl ?? media.defaultTryOnImageUrl ?? null,
  }
}

const writeMockTryOnProfile = (userId: number | null | undefined, profile: Partial<TryOnProfile>) => {
  const profileMap = readAllMockTryOnProfiles()
  const userKey = getUserKey(userId)

  profileMap[userKey] = {
    ...profileMap[userKey],
    ...profile,
  }

  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(profileMap))
}

const readAllMockTryOnProfiles = (): TryOnProfileMap => {
  try {
    const storedValue = window.localStorage.getItem(STORAGE_KEY)

    if (!storedValue) {
      return {}
    }

    return JSON.parse(storedValue) as TryOnProfileMap
  } catch {
    return {}
  }
}

const toOptionalNumber = (value?: string) => {
  const trimmedValue = value?.trim()

  if (!trimmedValue) {
    return null
  }

  return Number(trimmedValue)
}

const unwrapApiData = <T>(response: ApiResponse<T>, fallbackMessage: string) => {
  if (!response.success || response.data === null) {
    throw new Error(response.error?.message ?? fallbackMessage)
  }

  return response.data
}
