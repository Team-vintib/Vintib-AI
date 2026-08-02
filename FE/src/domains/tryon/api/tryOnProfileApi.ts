import {
  deleteMockDefaultTryOnImage,
  readImageFileAsDataUrl,
  readMockProfileMedia,
  saveMockDefaultTryOnImage,
} from '@/shared/api/mockProfileMediaStorage'
import { http } from '@/shared/api/http'

import { EMPTY_TRYON_PROFILE } from '@/domains/tryon/constants/tryOnProfileMockData'
import type { SaveTryOnProfileRequest, TryOnProfile } from '@/domains/tryon/types/tryOnProfile.types'
import type { ApiResponse } from '@/shared/types/api.types'

const TRYON_API_ENABLED = import.meta.env.VITE_TRYON_API_ENABLED === 'true'
const STORAGE_KEY = 'vidtib:mock-tryon-profile'
const FALLBACK_USER_KEY = 'current'

type TryOnProfileMap = Record<string, Partial<TryOnProfile>>

const getUserKey = (userId?: number | null) => (userId ? String(userId) : FALLBACK_USER_KEY)

export const getMyTryOnProfile = async (userId?: number | null): Promise<TryOnProfile> => {
  if (!TRYON_API_ENABLED) {
    return readMockTryOnProfile(userId)
  }

  const response = await http.get<ApiResponse<TryOnProfile>>('/me/tryon')
  return unwrapApiData(response.data, 'AI 시착 정보를 불러오지 못했습니다.')
}

export const saveMyTryOnProfile = async (
  request: SaveTryOnProfileRequest,
  userId?: number | null,
): Promise<TryOnProfile> => {
  if (!TRYON_API_ENABLED) {
    return saveMockTryOnProfile(request, userId)
  }

  const formData = new FormData()

  if (request.bodyPhoto) {
    formData.append('bodyPhoto', request.bodyPhoto)
  }

  appendOptionalFormValue(formData, 'heightCm', request.heightCm)
  appendOptionalFormValue(formData, 'weightKg', request.weightKg)
  appendOptionalFormValue(formData, 'chest', request.chest)
  appendOptionalFormValue(formData, 'waist', request.waist)
  appendOptionalFormValue(formData, 'hip', request.hip)

  const response = await http.put<ApiResponse<TryOnProfile>>('/me/tryon', formData)

  return unwrapApiData(response.data, 'AI 시착 정보를 저장하지 못했습니다.')
}

export const deleteMyTryOnProfile = async (userId?: number | null): Promise<TryOnProfile> => {
  if (!TRYON_API_ENABLED) {
    deleteMockDefaultTryOnImage(userId)
    writeMockTryOnProfile(userId, { ...EMPTY_TRYON_PROFILE, updatedAt: new Date().toISOString() })
    return readMockTryOnProfile(userId)
  }

  const response = await http.delete<ApiResponse<TryOnProfile>>('/me/tryon')
  return response.data.data ?? { ...EMPTY_TRYON_PROFILE, updatedAt: new Date().toISOString() }
}

export const isTryOnApiEnabled = () => TRYON_API_ENABLED

const appendOptionalFormValue = (formData: FormData, key: string, value?: string) => {
  const trimmedValue = value?.trim()

  if (trimmedValue) {
    formData.append(key, trimmedValue)
  }
}

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
