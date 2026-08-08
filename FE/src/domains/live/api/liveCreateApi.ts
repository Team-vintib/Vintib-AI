import { http } from '@/shared/api/http'

import type { LiveCreateProduct } from '@/domains/live/types/liveCreate.types'
import {
  getBrands,
  getCategories,
  getProductPrimaryImageUrl,
  type CategoryDto,
} from '@/domains/product/api/productApi'
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
  categoryId?: number | null
  brandId?: number | null
  title: string
  conditionGrade?: string | null
  saleType?: string | null
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
  // ProductResponse(`GET /products`)는 categoryId/brandId만 내려주고 이름은 안 준다 —
  // 상품 등록 화면과 동일하게 마스터 목록을 받아 여기서 이름으로 변환한다.
  const [categories, brands] = await Promise.all([
    getCategories().catch(() => []),
    getBrands().catch(() => []),
  ])
  const categoryById = new Map(categories.map((category) => [category.id, category]))
  const brandNameById = new Map(brands.map((brand) => [brand.id, brand.name]))

  return Promise.all(
    sellerProducts.map((product) => toLiveCreateProduct(product, categoryById, brandNameById)),
  )
}

// 상품의 categoryId는 소분류(depth 3)라 이름만 보여주면 "니트"처럼 뭐가 뭔지 알기 어렵다 —
// 부모(대분류)까지 같이 "아우터 > 니트"로 붙여 보여준다.
const buildCategoryLabel = (categoryId: number, categoryById: Map<number, CategoryDto>) => {
  const leaf = categoryById.get(categoryId)

  if (!leaf) {
    return null
  }

  const parent = leaf.parentId ? categoryById.get(leaf.parentId) : null

  return parent ? `${parent.name} > ${leaf.name}` : leaf.name
}

const toLiveCreateProduct = async (
  product: LiveCreateProductDto,
  categoryById: Map<number, CategoryDto>,
  brandNameById: Map<number, string>,
): Promise<LiveCreateProduct> => ({
  id: product.id,
  name: product.title,
  brand: (product.brandId && brandNameById.get(product.brandId)) || '-',
  category:
    (product.categoryId && buildCategoryLabel(product.categoryId, categoryById)) || '카테고리 미상',
  condition: product.conditionGrade || product.saleStatus || '상태 미상',
  price: product.price ?? 0,
  isAuctionScheduled: product.saleType === 'AUCTION' || product.saleStatus === 'AUCTION_SCHEDULED',
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
