import { http } from '@/shared/api/http'

import type { LiveCreateProduct } from '@/domains/live/types/liveCreate.types'
import { getProductPrimaryImageUrl } from '@/domains/product/api/productApi'
import type { ApiResponse } from '@/shared/types/api.types'

export type LiveCreateStatus = 'LIVE' | 'SCHEDULED' | 'ENDED' | 'CANCELED'

export interface LiveCreateResponse {
  id: number
  hostId: number
  title: string
  thumbnailUrl: string | null
  status: LiveCreateStatus
  scheduledAt: string | null
  startedAt: string | null
  createdAt: string
}

interface CreateLiveRequest {
  title: string
  thumbnailUrl: string | null
  productIds: number[]
}

interface LiveThumbnailUploadUrlResponse {
  key: string
  uploadUrl: string
  url: string
  expiresInSeconds: number
}

interface ScheduleLiveRequest extends CreateLiveRequest {
  scheduledAt: string
}

interface BackendPageResponse<T> {
  content: T[]
  page: number
  size: number
  totalElements: number
  totalPages: number
  hasNext: boolean
}

interface LiveCreateProductDto {
  id: number
  sellerId: number
  categoryName?: string | null
  brandName?: string | null
  title: string
  conditionGrade?: string | null
  saleStatus?: string | null
  price: number | null
  primaryImageUrl?: string | null
}

export const createLiveNow = async (request: CreateLiveRequest) => {
  const { data } = await http.post<ApiResponse<LiveCreateResponse>>('/lives', request)

  return unwrapLiveCreateResponse(data)
}

export const scheduleLive = async (request: ScheduleLiveRequest) => {
  const { data } = await http.post<ApiResponse<LiveCreateResponse>>('/lives/schedule', request)

  return unwrapLiveCreateResponse(data)
}

export const uploadLiveThumbnail = async (userId: number, file: File): Promise<string> => {
  const contentType = file.type || 'application/octet-stream'
  const uploadUrlResponse = await http.post<ApiResponse<LiveThumbnailUploadUrlResponse>>(
    `/users/${userId}/lives/thumbnail/upload-url`,
    { contentType },
  )
  const uploadUrl = unwrapApiData(uploadUrlResponse.data, '썸네일 업로드 URL을 발급하지 못했습니다.')

  const uploadResponse = await fetch(uploadUrl.uploadUrl, {
    method: 'PUT',
    headers: { 'Content-Type': contentType },
    body: file,
  })

  if (!uploadResponse.ok) {
    throw new Error('썸네일 이미지를 업로드하지 못했습니다.')
  }

  return uploadUrl.url
}

export const getLiveCreateProducts = async (sellerId: number): Promise<LiveCreateProduct[]> => {
  const { data } = await http.get<ApiResponse<BackendPageResponse<LiveCreateProductDto>>>(
    '/products',
    {
      params: {
        page: 0,
        size: 100,
      },
    },
  )

  if (!data.success || !data.data) {
    throw new Error(data.error?.message ?? '라이브에 연결할 상품을 불러오지 못했습니다.')
  }

  const sellerProducts = data.data.content.filter((product) => product.sellerId === sellerId)

  return Promise.all(sellerProducts.map(toLiveCreateProduct))
}

const toLiveCreateProduct = async (product: LiveCreateProductDto): Promise<LiveCreateProduct> => ({
  id: product.id,
  name: product.title,
  brand: product.brandName || '브랜드 미상',
  category: product.categoryName || '카테고리 미상',
  condition: product.conditionGrade || product.saleStatus || '상태 미상',
  price: product.price ?? 0,
  thumbnailUrl:
    product.primaryImageUrl || (await getProductPrimaryImageUrl(product.id).catch(() => '')),
})

const unwrapLiveCreateResponse = (response: ApiResponse<LiveCreateResponse>) => {
  if (!response.success || !response.data) {
    throw new Error(response.error?.message ?? '라이브를 생성하지 못했습니다.')
  }

  return response.data
}

const unwrapApiData = <T>(response: ApiResponse<T>, fallbackMessage: string) => {
  if (!response.success || !response.data) {
    throw new Error(response.error?.message ?? fallbackMessage)
  }

  return response.data
}
