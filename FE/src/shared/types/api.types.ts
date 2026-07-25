export interface ApiResponse<T> {
  data: T | null
  error?: ApiErrorBody | null
  message?: string
  success: boolean
}

export interface ApiFieldError {
  field: string
  reason: string
  value?: unknown
}

export interface ApiErrorBody {
  code: string
  details?: Record<string, unknown>
  errors?: ApiFieldError[] | null
  message: string
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
