export interface ApiFieldError {
  field: string
  value: string
  reason: string
}

export interface ApiError {
  code: string
  message: string
  errors: ApiFieldError[] | null
}

export interface ApiResponse<T> {
  success: boolean
  data: T | null
  error: ApiError | null
}
