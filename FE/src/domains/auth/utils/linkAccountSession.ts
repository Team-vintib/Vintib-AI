import type { LinkAccountSessionPayload } from '@/domains/auth/types/auth.types'

export const LINK_ACCOUNT_STORAGE_KEY = 'vintib_ssafy_link_account'

export const readLinkAccountSession = () => {
  const rawPayload = window.sessionStorage.getItem(LINK_ACCOUNT_STORAGE_KEY)

  if (!rawPayload) {
    return null
  }

  try {
    return JSON.parse(rawPayload) as LinkAccountSessionPayload
  } catch {
    return null
  }
}

export const writeLinkAccountSession = (payload: LinkAccountSessionPayload) => {
  window.sessionStorage.setItem(LINK_ACCOUNT_STORAGE_KEY, JSON.stringify(payload))
}

export const clearLinkAccountSession = () => {
  window.sessionStorage.removeItem(LINK_ACCOUNT_STORAGE_KEY)
}
