import axios, { AxiosError } from 'axios'

import type { ApiErrorBody, ApiResponse } from '@/shared/types/api.types'

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
  if (axios.isAxiosError<ApiResponse<unknown> | ApiErrorBody>(error)) {
    return getAxiosErrorBody(error)
  }

  return {
    code: 'UNKNOWN_ERROR',
    message: '알 수 없는 오류가 발생했습니다.',
  }
}

function getAxiosErrorBody(error: AxiosError<ApiResponse<unknown> | ApiErrorBody>): ApiErrorBody {
  if (isApiResponse(error.response?.data) && error.response.data.error) {
    return error.response.data.error
  }

  if (isApiErrorBody(error.response?.data)) {
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

function isApiResponse(data: unknown): data is ApiResponse<unknown> {
  return Boolean(data && typeof data === 'object' && 'success' in data)
}

function isApiErrorBody(data: unknown): data is ApiErrorBody {
  return Boolean(
    data &&
    typeof data === 'object' &&
    'code' in data &&
    'message' in data &&
    typeof data.code === 'string' &&
    typeof data.message === 'string',
  )
}
