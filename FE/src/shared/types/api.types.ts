export interface ApiResponse<T> {
  data: T
  message?: string
  success: boolean
}

export interface ApiErrorBody {
  code: string
  message: string
  details?: Record<string, unknown>
}

export interface PageMeta {
  page: number
  size: number
  totalElements: number
  totalPages: number
}

export interface PageResponse<T> {
  items: T[]
  meta: PageMeta
}
