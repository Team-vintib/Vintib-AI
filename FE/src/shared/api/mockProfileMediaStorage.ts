const STORAGE_KEY = 'vidtib:mock-profile-media'
const FALLBACK_USER_KEY = 'current'

interface MockProfileMedia {
  profileImageUrl: string | null
  defaultTryOnImageUrl: string | null
}

type MockProfileMediaMap = Record<string, Partial<MockProfileMedia>>

const getUserKey = (userId?: number | null) => (userId ? String(userId) : FALLBACK_USER_KEY)

const getFallbackMedia = (): MockProfileMedia => ({
  profileImageUrl: null,
  defaultTryOnImageUrl: null,
})

const readAllMedia = (): MockProfileMediaMap => {
  try {
    const storedValue = window.localStorage.getItem(STORAGE_KEY)

    if (!storedValue) {
      return {}
    }

    return JSON.parse(storedValue) as MockProfileMediaMap
  } catch {
    return {}
  }
}

const writeAllMedia = (mediaMap: MockProfileMediaMap) => {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(mediaMap))
}

const writeUserMedia = (userId: number | null | undefined, nextMedia: Partial<MockProfileMedia>) => {
  const mediaMap = readAllMedia()
  const userKey = getUserKey(userId)

  mediaMap[userKey] = {
    ...mediaMap[userKey],
    ...nextMedia,
  }

  writeAllMedia(mediaMap)
}

export const readMockProfileMedia = (userId?: number | null): MockProfileMedia => {
  const mediaMap = readAllMedia()

  return {
    ...getFallbackMedia(),
    ...mediaMap[FALLBACK_USER_KEY],
    ...mediaMap[getUserKey(userId)],
  }
}

export const saveMockProfileImage = (userId: number | null | undefined, imageUrl: string) => {
  writeUserMedia(userId, { profileImageUrl: imageUrl })
}

export const deleteMockProfileImage = (userId?: number | null) => {
  writeUserMedia(userId, { profileImageUrl: null })
}

export const saveMockDefaultTryOnImage = (
  userId: number | null | undefined,
  imageUrl: string,
) => {
  writeUserMedia(userId, { defaultTryOnImageUrl: imageUrl })
}

export const deleteMockDefaultTryOnImage = (userId?: number | null) => {
  writeUserMedia(userId, { defaultTryOnImageUrl: null })
}

export const readImageFileAsDataUrl = (file: File, fallbackMessage: string) =>
  new Promise<string>((resolve, reject) => {
    const reader = new FileReader()

    reader.addEventListener('load', () => {
      if (typeof reader.result === 'string') {
        resolve(reader.result)
        return
      }

      reject(new Error(fallbackMessage))
    })
    reader.addEventListener('error', () => {
      reject(new Error(fallbackMessage))
    })
    reader.readAsDataURL(file)
  })
