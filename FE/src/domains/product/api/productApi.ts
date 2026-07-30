import axios from 'axios'

import { PRODUCT_LIST_MOCK_DATA } from '@/domains/product/constants/productListMockData'
import { PRODUCT_DETAIL_MOCK_DATA } from '@/domains/product/constants/productDetailMockData'
import type {
  ProductConditionGrade,
  ProductListItem,
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
  sellerNickname: string
  images: ProductImageDto[]
  color?: string | null
  material?: string | null
  updatedAt: string
}

interface ProductCreateRequest {
  title: string
  description: string
  categoryId: number | null
  brandId: number | null
  conditionGrade: ProductConditionGrade | ''
  sizeLabel: string
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
  categoryIds?: string[]
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

const FALLBACK_IMAGE_URL = PRODUCT_LIST_MOCK_DATA[0]?.imageUrl ?? ''
const FALLBACK_BRAND_NAME = '브랜드 미상'
const FALLBACK_CATEGORY_NAME = '빈티지 상품'
const FALLBACK_SELLER_PRODUCT_COUNT = 0
const FALLBACK_SELLER_FOLLOWER_COUNT = 0

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
      saleType: saleType === 'ALL' ? undefined : saleType,
    },
  })
  const pageResponse = normalizePageResponse(unwrapApiData(response.data))

  return {
    items: pageResponse.items.map(toProductListItem),
    meta: pageResponse.meta,
  }
}

export const getProductDetail = async (productId: number): Promise<ProductDetailViewData> => {
  const response = await http.get<ApiResponse<ProductDetailDto>>(`/products/${productId}`)

  return toProductDetailViewData(unwrapApiData(response.data))
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
  const createResponse = await http.post<ApiResponse<ProductListDto>>('/products', {
    title: draft.name.trim(),
    description: draft.description.trim(),
    categoryId: findCategoryId(draft, categories),
    brandId: findBrandId(draft.brand, brands),
    conditionGrade: draft.conditionGrade,
    sizeLabel: draft.size,
  } satisfies ProductCreateRequest)
  const createdProduct = unwrapApiData(createResponse.data)

  await uploadProductImages(createdProduct.id, draft.photos)

  if (draft.saleType === 'DIRECT') {
    await http.patch<ApiResponse<ProductListDto>>(`/products/${createdProduct.id}/status`, {
      price: Number(draft.directSalePrice),
    })
  }

  if (draft.saleType === 'AUCTION') {
    await http.patch<ApiResponse<ProductListDto>>(`/products/${createdProduct.id}/auction-schedule`)
  }

  return {
    productId: String(createdProduct.id),
    submittedAt: new Date().toISOString(),
  }
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

const toProductListItem = (product: ProductListDto): ProductListItem => {
  const mockFallback = PRODUCT_LIST_MOCK_DATA.find((item) => item.id === product.id)

  return {
    id: product.id,
    brand: product.brandName || mockFallback?.brand || fallbackBrandLabel(product.brandId),
    name: product.title,
    price: product.price ?? 0,
    conditionGrade: product.conditionGrade,
    saleType: toProductSaleType(product.saleType),
    imageUrl: product.primaryImageUrl || mockFallback?.imageUrl || FALLBACK_IMAGE_URL,
    imageAlt: `${product.title} 상품 이미지`,
    isLiked: product.isWished ?? false,
  }
}

const toProductDetailViewData = (product: ProductDetailDto): ProductDetailViewData => {
  const mockFallback = {
    ...PRODUCT_DETAIL_MOCK_DATA,
    seller: { ...PRODUCT_DETAIL_MOCK_DATA.seller },
    linkedLive: PRODUCT_DETAIL_MOCK_DATA.linkedLive ? { ...PRODUCT_DETAIL_MOCK_DATA.linkedLive } : null,
    similarProducts: PRODUCT_DETAIL_MOCK_DATA.similarProducts.map((similarProduct) => ({
      ...similarProduct,
    })),
    sellerDisclosedDefects: PRODUCT_DETAIL_MOCK_DATA.sellerDisclosedDefects.map((defect) => ({
      ...defect,
    })),
    aiQualityAnalysis: {
      ...PRODUCT_DETAIL_MOCK_DATA.aiQualityAnalysis,
      findings: PRODUCT_DETAIL_MOCK_DATA.aiQualityAnalysis.findings.map((finding) => ({
        ...finding,
      })),
    },
  }
  const sortedImages = [...(product.images ?? [])].sort((left, right) => {
    if (left.isPrimary !== right.isPrimary) {
      return left.isPrimary ? -1 : 1
    }

    return left.sortOrder - right.sortOrder
  })

  return {
    ...mockFallback,
    id: product.id,
    brand: product.brandName || fallbackBrandLabel(product.brandId),
    title: product.title,
    description: product.description || '',
    category: product.categoryName || fallbackCategoryLabel(product.categoryId),
    conditionLabel: `${product.conditionGrade}급`,
    sizeLabel: product.sizeLabel,
    material: product.material || mockFallback.material,
    color: product.color || mockFallback.color,
    price: product.price ?? 0,
    saleType: product.saleType,
    saleStatus: product.saleStatus,
    isLiked: product.isWished ?? false,
    images: sortedImages.map((image, index) => ({
      id: String(image.id),
      url: image.url,
      alt: `${product.title} 상품 이미지 ${index + 1}`,
      label: image.isPrimary ? '대표' : `${index + 1}번`,
    })),
    seller: {
      id: product.sellerId,
      nickname: product.sellerNickname,
      followerCount: FALLBACK_SELLER_FOLLOWER_COUNT,
      productCount: FALLBACK_SELLER_PRODUCT_COUNT,
    },
  }
}

const toProductSaleType = (saleType: ProductSaleTypeDto): ProductSaleType =>
  saleType === 'AUCTION' ? 'AUCTION' : 'DIRECT'

const fallbackBrandLabel = (brandId: number | null) =>
  brandId ? `${FALLBACK_BRAND_NAME} #${brandId}` : FALLBACK_BRAND_NAME

const fallbackCategoryLabel = (categoryId: number | null) =>
  categoryId ? `${FALLBACK_CATEGORY_NAME} #${categoryId}` : FALLBACK_CATEGORY_NAME

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

export const getCategoryCode = (categoryName: string) => {
  if (categoryName.includes('아우터')) return 'outer'
  if (categoryName.includes('상의')) return 'top'
  if (categoryName.includes('하의')) return 'bottom'
  if (categoryName.includes('원피스')) return 'dress'
  if (categoryName.includes('신발')) return 'shoes'
  if (categoryName.includes('액세서리')) return 'accessory'

  return ''
}
