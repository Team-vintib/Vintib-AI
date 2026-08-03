import axios from 'axios'

import type {
  ProductConditionGrade,
  ProductListItem,
  ProductSaleStatus,
  ProductSaleType,
  ProductSaleTypeTab,
  ProductSortOption,
} from '@/domains/product/types/productList.types'
import type { ProductDetailViewData } from '@/domains/product/types/productDetail.types'
import type {
  ProductRegistrationDraft,
  ProductRegistrationPhotoDraft,
  ProductRegistrationSubmitResult,
} from '@/domains/product/types/productRegistration.types'
import { http } from '@/shared/api/http'
import type { ApiResponse, PageMeta, PageResponse } from '@/shared/types/api.types'

type ProductSaleTypeDto = 'DIRECT_SALE' | 'AUCTION'
type ProductSaleStatusDto =
  | 'DRAFT'
  | 'ON_SALE'
  | 'AUCTION_SCHEDULED'
  | 'AUCTION_IN_PROGRESS'
  | 'AUCTION_FAILED'
  | 'SOLD'
  | 'PRIVATE'

export interface BrandDto {
  id: number
  name: string
  nameEn: string | null
}

export interface CategoryDto {
  id: number
  parentId: number | null
  name: string
  depth: number
}

interface ProductImageDto {
  id: number
  url: string
  sortOrder: number
  isPrimary: boolean
}

interface ProductListDto {
  id: number
  sellerId: number
  categoryId: number
  categoryName?: string | null
  brandId: number | null
  brandName?: string | null
  title: string
  description: string | null
  conditionGrade: ProductConditionGrade
  sizeLabel: string
  saleType: ProductSaleTypeDto
  saleStatus: ProductSaleStatusDto
  price: number | null
  primaryImageUrl?: string | null
  isWished?: boolean
  isLiked?: boolean
  createdAt: string
}

interface BackendPageResponse<T> {
  content: T[]
  page: number
  size: number
  totalElements: number
  totalPages: number
  hasNext: boolean
}

interface ProductDetailDto extends ProductListDto {
  sellerNickname?: string | null
  sellerFollowerCount?: number
  sellerProductCount?: number
  images: ProductImageDto[]
  color?: string | null
  material?: string | null
  defects?: string[]
  measurements?: Record<string, number>
  linkedLive?: {
    liveId: number
    title: string
    status: string
    scheduledAt: string | null
    startedAt: string | null
    thumbnailUrl: string
  } | null
  updatedAt: string
}

interface ProductCreateRequest {
  title: string
  description: string
  categoryId: number | null
  brandId: number | null
  conditionGrade: ProductConditionGrade | ''
  sizeLabel: string
  color: string | null
  material: string | null
  measurements: Record<string, number> | null
  defects: string[] | null
}

interface ProductCreateResponse extends Partial<ProductListDto> {
  productId?: number | string | null
}

interface ProductImageUploadUrlResponse {
  key: string
  uploadUrl: string
  expiresInSeconds: number
}

interface ProductImageRegisterRequest {
  key: string
  sortOrder: number
  isPrimary: boolean
}

interface ProductListParams {
  categoryIds?: number[]
  conditionGrades?: string[]
  maxPrice?: number | null
  minPrice?: number | null
  page?: number
  saleType?: ProductSaleTypeTab['id']
  size?: number
  sort?: ProductSortOption
}

interface ProductSubmitOptions {
  brands?: BrandDto[]
  categories?: CategoryDto[]
}

const EMPTY_AI_QUALITY_ANALYSIS = {
  status: 'NOT_REQUESTED',
  originalImageUrl: '',
  originalImageAlt: '',
  analyzedImageUrl: '',
  analyzedImageAlt: '',
  summary: '',
  findings: [],
  disclaimer: '',
} satisfies ProductDetailViewData['aiQualityAnalysis']

export const getProductList = async ({
  categoryIds = [],
  conditionGrades = [],
  maxPrice = null,
  minPrice = null,
  page = 1,
  saleType = 'ALL',
  size = 20,
  sort = 'LATEST',
}: ProductListParams = {}) => {
  const response = await http.get<ApiResponse<PageResponse<ProductListDto> | BackendPageResponse<ProductListDto>>>('/products', {
    params: {
      page: Math.max(page - 1, 0),
      size,
      sort,
      keyword: undefined,
      categoryIds: categoryIds.length ? categoryIds.join(',') : undefined,
      conditionGrades: conditionGrades.length ? conditionGrades.join(',') : undefined,
      minPrice: minPrice ?? undefined,
      maxPrice: maxPrice ?? undefined,
      saleType: toSaleTypeParam(saleType),
    },
    skipAuth: true,
  })
  const pageResponse = normalizePageResponse(unwrapApiData(response.data))
  const items = await Promise.all(pageResponse.items.map(toProductListItem))

  return {
    items,
    meta: pageResponse.meta,
  }
}

export const getProductDetail = async (productId: number): Promise<ProductDetailViewData> => {
  const response = await http.get<ApiResponse<ProductDetailDto>>(`/products/${productId}`, {
    skipAuth: true,
  })

  return toProductDetailViewData(unwrapApiData(response.data))
}

export const getProductPrimaryImageUrl = async (productId: number) => {
  const response = await http.get<ApiResponse<ProductDetailDto>>(`/products/${productId}`, {
    skipAuth: true,
  })
  const product = unwrapApiData(response.data)

  return getPrimaryImageUrl(product)
}

// 미낙찰 상품 처리(440) — 상품을 상시 판매(가격 지정)로 전환하거나 경매 예정으로 되돌린다.
// 상품 등록의 판매 방식 설정(publishProduct)과 같은 엔드포인트를 재사용한다.
export const convertProductToDirectSale = async (productId: number, price: number) => {
  await http.patch<ApiResponse<ProductListDto>>(`/products/${productId}/status`, { price })
}

export const scheduleProductAuction = async (productId: number) => {
  await http.patch<ApiResponse<ProductListDto>>(`/products/${productId}/auction-schedule`)
}

export const getBrands = async () => {
  const response = await http.get<ApiResponse<BrandDto[]>>('/brands', { skipAuth: true })

  return unwrapApiData(response.data)
}

export const getCategories = async () => {
  const response = await http.get<ApiResponse<CategoryDto[]>>('/categories', { skipAuth: true })

  return unwrapApiData(response.data)
}

export const addWish = async (userId: number, productId: number) => {
  const response = await http.post<ApiResponse<{ productId: number; createdAt: string }>>(
    `/users/${userId}/wishes`,
    { productId },
  )

  return unwrapApiData(response.data)
}

export const removeWish = async (userId: number, productId: number) => {
  await http.delete(`/users/${userId}/wishes/${productId}`)
}

export const submitProduct = async (
  draft: ProductRegistrationDraft,
  { brands = [], categories = [] }: ProductSubmitOptions = {},
): Promise<ProductRegistrationSubmitResult> => {
  const createResponse = await http.post<ApiResponse<ProductCreateResponse>>('/products', {
    title: draft.name.trim(),
    description: draft.description.trim(),
    categoryId: findCategoryId(draft, categories),
    brandId: findBrandId(draft.brand, brands),
    conditionGrade: draft.conditionGrade,
    sizeLabel: draft.size,
    color: resolveRegistrationColor(draft),
    material: draft.material.trim() || null,
    measurements: resolveRegistrationMeasurements(draft),
    defects: resolveRegistrationDefects(draft),
  } satisfies ProductCreateRequest)
  const createdProduct = unwrapApiData(createResponse.data)
  const createdProductId = getCreatedProductId(createdProduct)

  await publishProduct(createdProductId, draft)
  await uploadProductImages(createdProductId, draft.photos)

  return {
    productId: String(createdProductId),
    submittedAt: new Date().toISOString(),
  }
}

const publishProduct = async (productId: number, draft: ProductRegistrationDraft) => {
  if (draft.saleType === 'DIRECT') {
    await convertProductToDirectSale(productId, Number(draft.directSalePrice))
    return
  }

  if (draft.saleType === 'AUCTION') {
    await scheduleProductAuction(productId)
    return
  }
}

const getCreatedProductId = (product: ProductCreateResponse) => {
  const rawProductId = product.id ?? product.productId
  const productId = Number(rawProductId)

  if (!Number.isInteger(productId) || productId < 1) {
    throw new Error('Product create response does not include a valid product id.')
  }

  return productId
}

const uploadProductImages = async (productId: number, photos: ProductRegistrationPhotoDraft[]) => {
  const orderedPhotos = [...photos].sort((left, right) => {
    if (left.isRepresentative !== right.isRepresentative) {
      return left.isRepresentative ? -1 : 1
    }

    return photos.indexOf(left) - photos.indexOf(right)
  })

  for (const [index, photo] of orderedPhotos.entries()) {
    if (!photo.file) {
      continue
    }

    const uploadUrlResponse = await http.post<ApiResponse<ProductImageUploadUrlResponse>>(
      `/products/${productId}/images/upload-url`,
      {
        fileName: photo.file.name,
        contentType: photo.file.type,
      },
    )
    const uploadData = unwrapApiData(uploadUrlResponse.data)

    await axios.put(uploadData.uploadUrl, photo.file, {
      headers: {
        'Content-Type': photo.file.type,
      },
    })

    await http.post<ApiResponse<ProductImageDto>, void, ProductImageRegisterRequest>(
      `/products/${productId}/images`,
      {
        key: uploadData.key,
        sortOrder: index,
        isPrimary: photo.isRepresentative,
      },
    )
  }
}

const unwrapApiData = <T>(response: ApiResponse<T>) => {
  if (!response.success || !response.data) {
    throw new Error(response.error?.message ?? '상품 API 요청에 실패했습니다.')
  }

  return response.data
}

const normalizePageResponse = <T>(
  response: PageResponse<T> | BackendPageResponse<T>,
): PageResponse<T> => {
  if ('items' in response) {
    return response
  }

  return {
    items: response.content,
    meta: {
      page: response.page + 1,
      size: response.size,
      totalElements: response.totalElements,
      totalPages: response.totalPages,
    } satisfies PageMeta,
  }
}

const toProductListItem = async (product: ProductListDto): Promise<ProductListItem> => {
  const imageUrl =
    product.primaryImageUrl || (await getProductPrimaryImageUrl(product.id).catch(() => ''))

  return {
    id: product.id,
    brand: product.brandName || fallbackBrandLabel(product.brandId),
    name: product.title,
    price: product.price ?? 0,
    conditionGrade: product.conditionGrade,
    saleType: toProductSaleType(product.saleType),
    saleStatus: product.saleStatus satisfies ProductSaleStatus,
    categoryId: product.categoryId,
    categoryName: product.categoryName ?? fallbackCategoryLabel(product.categoryId),
    imageUrl,
    imageAlt: `${product.title} 상품 이미지`,
    isLiked: product.isWished ?? product.isLiked ?? false,
  }
}

const toProductDetailViewData = (product: ProductDetailDto): ProductDetailViewData => {
  const sortedImages = getSortedProductImages(product)
  const images = sortedImages.length
    ? sortedImages.map((image, index) => ({
        id: String(image.id),
        url: image.url,
        alt: `${product.title} 상품 이미지 ${index + 1}`,
        label: image.isPrimary ? '대표' : `${index + 1}번`,
      }))
    : []

  return {
    id: product.id,
    brand: product.brandName || fallbackBrandLabel(product.brandId),
    title: product.title,
    description: product.description || '',
    category: product.categoryName || fallbackCategoryLabel(product.categoryId),
    conditionLabel: `${product.conditionGrade}급`,
    sizeLabel: product.sizeLabel,
    material: product.material || '',
    color: product.color || '',
    price: product.price ?? 0,
    saleType: product.saleType,
    saleStatus: product.saleStatus,
    isLiked: product.isWished ?? product.isLiked ?? false,
    images,
    seller: {
      id: product.sellerId,
      nickname: product.sellerNickname?.trim() || '',
      followerCount: product.sellerFollowerCount ?? 0,
      productCount: product.sellerProductCount ?? 0,
    },
    linkedLive: toLinkedLive(product.linkedLive),
    measurements: product.measurements ?? {},
    similarProducts: [],
    sellerDisclosedDefects: (product.defects ?? []).map((defect) => ({
      title: defect,
      description: '',
    })),
    aiQualityAnalysis: {
      ...EMPTY_AI_QUALITY_ANALYSIS,
      findings: [],
    },
  }
}

// BE 상세 계약(010)의 linkedLive를 FE 뷰 타입(ProductLinkedLive)으로 변환한다.
// startedAt이 있으면 방송 중(LIVE), 없으면 방송 예정(SCHEDULED)으로 본다.
const toLinkedLive = (
  linkedLive: ProductDetailDto['linkedLive'],
): ProductDetailViewData['linkedLive'] => {
  if (!linkedLive) {
    return null
  }

  return {
    id: linkedLive.liveId,
    title: linkedLive.title,
    startsAt: linkedLive.startedAt ?? linkedLive.scheduledAt ?? '',
    status: linkedLive.startedAt ? 'LIVE' : 'SCHEDULED',
    thumbnailUrl: linkedLive.thumbnailUrl,
  }
}

const toProductSaleType = (saleType: ProductSaleTypeDto): ProductSaleType =>
  saleType === 'AUCTION' ? 'AUCTION' : 'DIRECT'

// 목록 필터 탭 id(FE 표시용 'DIRECT')를 BE 계약(010)의 saleType 값으로 변환한다.
// 'ALL'은 전체 조회라 파라미터를 보내지 않는다.
const toSaleTypeParam = (
  saleType: ProductSaleTypeTab['id'],
): ProductSaleTypeDto | undefined => {
  if (saleType === 'ALL') {
    return undefined
  }

  return saleType === 'DIRECT' ? 'DIRECT_SALE' : 'AUCTION'
}

const getPrimaryImageUrl = (product: ProductDetailDto) =>
  getSortedProductImages(product)[0]?.url ?? ''

const getSortedProductImages = (product: Pick<ProductDetailDto, 'images'>) =>
  [...(product.images ?? [])].sort((left, right) => {
    if (left.isPrimary !== right.isPrimary) {
      return left.isPrimary ? -1 : 1
    }

    return left.sortOrder - right.sortOrder
  })

const fallbackBrandLabel = (brandId: number | null) =>
  brandId ? `브랜드 #${brandId}` : ''

const fallbackCategoryLabel = (categoryId: number | null) =>
  categoryId ? `카테고리 #${categoryId}` : ''

const findBrandId = (brandName: string, brands: BrandDto[]) => {
  const normalizedBrandName = brandName.trim().toLowerCase()
  const matchedBrand = brands.find(
    (brand) =>
      brand.name.toLowerCase() === normalizedBrandName ||
      brand.nameEn?.toLowerCase() === normalizedBrandName,
  )

  return matchedBrand?.id ?? null
}

const findCategoryId = (draft: ProductRegistrationDraft, categories: CategoryDto[]) => {
  const numericCategoryId = Number(draft.categoryId)

  if (Number.isInteger(numericCategoryId) && numericCategoryId > 0) {
    return numericCategoryId
  }

  const matchedCategory = categories.find((category) =>
    getCategoryCode(category.name) === draft.categoryId,
  )

  return matchedCategory?.id ?? null
}

const resolveRegistrationColor = (draft: ProductRegistrationDraft) => {
  if (draft.color === 'etc') {
    return draft.customColor.trim() || null
  }

  return draft.color || null
}

const resolveRegistrationMeasurements = (draft: ProductRegistrationDraft) => {
  const measurements = Object.entries(draft.measurements).reduce<Record<string, number>>(
    (result, [key, value]) => {
      const parsedValue = Number(String(value).trim())

      if (Number.isFinite(parsedValue) && parsedValue > 0) {
        result[key] = Math.round(parsedValue)
      }

      return result
    },
    {},
  )

  return Object.keys(measurements).length ? measurements : null
}

const resolveRegistrationDefects = (draft: ProductRegistrationDraft) => {
  if (!draft.hasDefect) {
    return []
  }

  const description = draft.sellerDefectDescription.trim()

  return description ? [description] : []
}

export const getCategoryCode = (categoryName: string) => {
  if (categoryName.includes('아우터')) return 'outer'
  if (categoryName.includes('상의')) return 'top'
  if (categoryName.includes('하의')) return 'bottom'
  if (categoryName.includes('원피스')) return 'dress'
  if (categoryName.includes('신발')) return 'shoes'
  if (categoryName.includes('액세서리')) return 'accessory'

  return ''
}
