export const AUTH_ACCESS_TOKEN_KEY = 'vintib_access_token'
export const AUTH_REFRESH_TOKEN_KEY = 'vintib_refresh_token'
export const AUTH_USER_KEY = 'vintib_auth_user'
export const AUTH_STORAGE_TYPE_KEY = 'vintib_auth_storage_type'

export type AuthStorageType = 'local' | 'session'

export interface StoredAuthSession {
  accessToken?: string
  refreshToken?: string
  user?: unknown
}

const getStorage = (type: AuthStorageType) => {
  if (typeof window === 'undefined') {
    return null
  }

  return type === 'local' ? window.localStorage : window.sessionStorage
}

export const getStoredAccessToken = () =>
  getStorage('local')?.getItem(AUTH_ACCESS_TOKEN_KEY) ||
  getStorage('session')?.getItem(AUTH_ACCESS_TOKEN_KEY) ||
  ''

export const readStoredAuthSession = (): StoredAuthSession => {
  const storageType = readStoredAuthStorageType()
  const primaryStorage = getStorage(storageType)
  const fallbackStorage = getStorage(storageType === 'local' ? 'session' : 'local')

  return {
    accessToken:
      primaryStorage?.getItem(AUTH_ACCESS_TOKEN_KEY) ||
      fallbackStorage?.getItem(AUTH_ACCESS_TOKEN_KEY) ||
      undefined,
    refreshToken:
      primaryStorage?.getItem(AUTH_REFRESH_TOKEN_KEY) ||
      fallbackStorage?.getItem(AUTH_REFRESH_TOKEN_KEY) ||
      undefined,
    user: parseStoredUser(
      primaryStorage?.getItem(AUTH_USER_KEY) || fallbackStorage?.getItem(AUTH_USER_KEY) || '',
    ),
  }
}

export const writeStoredAuthSession = (
  session: StoredAuthSession,
  storageType: AuthStorageType,
) => {
  clearStoredAuthSession()

  const storage = getStorage(storageType)

  if (!storage) {
    return
  }

  if (session.accessToken) {
    storage.setItem(AUTH_ACCESS_TOKEN_KEY, session.accessToken)
  }

  if (session.refreshToken) {
    storage.setItem(AUTH_REFRESH_TOKEN_KEY, session.refreshToken)
  }

  if (session.user) {
    storage.setItem(AUTH_USER_KEY, JSON.stringify(session.user))
  }

  getStorage('local')?.setItem(AUTH_STORAGE_TYPE_KEY, storageType)
}

export const clearStoredAuthSession = () => {
  ;(['local', 'session'] as const).forEach((storageType) => {
    const storage = getStorage(storageType)

    storage?.removeItem(AUTH_ACCESS_TOKEN_KEY)
    storage?.removeItem(AUTH_REFRESH_TOKEN_KEY)
    storage?.removeItem(AUTH_USER_KEY)
  })

  getStorage('local')?.removeItem(AUTH_STORAGE_TYPE_KEY)
}

const readStoredAuthStorageType = (): AuthStorageType => {
  const storageType = getStorage('local')?.getItem(AUTH_STORAGE_TYPE_KEY)

  return storageType === 'session' ? 'session' : 'local'
}

const parseStoredUser = (value: string): unknown => {
  if (!value) {
    return undefined
  }

  try {
    return JSON.parse(value)
  } catch {
    return undefined
  }
}
