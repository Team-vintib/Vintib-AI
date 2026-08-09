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

// mock 모드는 이 base64 문자열을 그대로 localStorage에 저장한다. 원본 파일(최대 5MB)을
// 그대로 넣으면 base64 인코딩만으로 ~6.7MB가 돼 브라우저 localStorage 용량 제한(보통
// 5MB 안팎)을 그 자체로 넘어 저장이 실패한다 — 저장 전에 리사이즈·재압축해서 크기를 줄인다.
const MOCK_STORED_IMAGE_MAX_DIMENSION_PX = 1024
const MOCK_STORED_IMAGE_QUALITY = 0.82

export const readImageFileAsCompressedDataUrl = (file: File, fallbackMessage: string) =>
  new Promise<string>((resolve, reject) => {
    const objectUrl = URL.createObjectURL(file)
    const image = new Image()

    image.addEventListener('load', () => {
      URL.revokeObjectURL(objectUrl)

      const scale = Math.min(
        1,
        MOCK_STORED_IMAGE_MAX_DIMENSION_PX / Math.max(image.naturalWidth, image.naturalHeight),
      )
      const canvas = document.createElement('canvas')
      canvas.width = Math.max(1, Math.round(image.naturalWidth * scale))
      canvas.height = Math.max(1, Math.round(image.naturalHeight * scale))

      const context = canvas.getContext('2d')

      if (!context) {
        reject(new Error(fallbackMessage))
        return
      }

      context.drawImage(image, 0, 0, canvas.width, canvas.height)
      resolve(canvas.toDataURL('image/jpeg', MOCK_STORED_IMAGE_QUALITY))
    })
    image.addEventListener('error', () => {
      URL.revokeObjectURL(objectUrl)
      reject(new Error(fallbackMessage))
    })
    image.src = objectUrl
  })
