import axios, { AxiosError } from 'axios'

import type { ApiErrorBody } from '@/shared/types/api.types'

const DEFAULT_TIMEOUT_MS = 10_000

export const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api',
  timeout: DEFAULT_TIMEOUT_MS,
  headers: {
    'Content-Type': 'application/json',
  },
})

http.interceptors.request.use((config) => {
  const accessToken = window.localStorage.getItem('vintib_access_token')

  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`
  }

  return config
})

export function normalizeApiError(error: unknown): ApiErrorBody {
  if (axios.isAxiosError<ApiErrorBody>(error)) {
    return getAxiosErrorBody(error)
  }

  return {
    code: 'UNKNOWN_ERROR',
    message: '알 수 없는 오류가 발생했습니다.',
  }
}

function getAxiosErrorBody(error: AxiosError<ApiErrorBody>): ApiErrorBody {
  if (error.response?.data?.code && error.response.data.message) {
    return error.response.data
  }

  if (error.code === 'ECONNABORTED') {
    return {
      code: 'REQUEST_TIMEOUT',
      message: '요청 시간이 초과되었습니다.',
    }
  }

  return {
    code: 'NETWORK_ERROR',
    message: '네트워크 연결을 확인해주세요.',
  }
}
