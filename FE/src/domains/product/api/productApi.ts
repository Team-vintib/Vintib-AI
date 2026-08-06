import axios from 'axios'

import type {
  ProductCategoryOption,
  ProductConditionGrade,
  ProductListItem,
  ProductSaleStatus,
  ProductSaleType,
  ProductSaleTypeTab,
  ProductSortOption,
} from '@/domains/product/types/productList.types'
import type {
  AiQualityAnalysis,
  ProductDetailViewData,
  SimilarProductPricePoint,
} from '@/domains/product/types/productDetail.types'
import type {
  ProductRegistrationDraft,
  ProductRegistrationPhotoDraft,
  ProductRegistrationSubmitResult,
} from '@/domains/product/types/productRegistration.types'
import { buildMockProductDetail } from '@/domains/product/constants/productDetailMockData'
import {
  PRODUCT_CATEGORY_MOCK_DATA,
  PRODUCT_LIST_MOCK_DATA,
} from '@/domains/product/constants/productListMockData'
import { http } from '@/shared/api/http'
import type { ApiResponse, PageMeta, PageResponse } from '@/shared/types/api.types'

// VITE_PRODUCT_API_ENABLED=false 일 때만 mock 목록을 사용합니다(기본값은 실 API).
const PRODUCT_API_ENABLED = import.meta.env.VITE_PRODUCT_API_ENABLED !== 'false'

type ProductSaleTypeDto = 'DIRECT_SALE' | 'AUCTION'
type ProductSaleStatusDto =
  | 'DRAFT'
  | 'ON_SALE'
  | 'AUCTION_SCHEDULED'
  | 'AUCTION_IN_PROGRESS'
  | 'AUCTION_FAILED'
  | 'SOLD'

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
  conditionGrade: ProductConditionGrade | null
  sizeLabel: string
  saleType: ProductSaleTypeDto
  saleStatus: ProductSaleStatusDto
  price: number | null
  primaryImageUrl?: string | null
  isWished?: boolean
  isLiked?: boolean
  createdAt: string
}

interface ProductWishDto {
  product: Pick<ProductListDto, 'id'>
  wishedAt: string
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
  similarProducts?: SimilarProductPricePoint[] | null
  aiQualityAnalysis?: AiQualityAnalysis | null
  updatedAt: string
}

// BE 확인 필요 — 등록 화면에서 사용자가 확정한 AI 품질 검증 결과를 담을 필드다.
// 현재 POST /products는 이 필드를 받지 않는다(docs/requests/BE/042-product-registration-ai-pipeline.md
// §3에서 저장/노출을 요청 중). BE가 반영하기 전까지는 보내도 무시될 뿐이라 안전하게 앞서 채워둔다.
interface ProductCreateAiQualityFindingRequest {
  photoRole: 'front' | 'back'
  description: string
  box: { x: number; y: number; width: number; height: number }
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
  aiModelEnabled: boolean
  aiModelGender: 'MALE' | 'FEMALE' | null
  aiQualityFindings: ProductCreateAiQualityFindingRequest[]
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
  sellerId?: number
  size?: number
  sort?: ProductSortOption
}

interface ProductSubmitOptions {
  brands?: BrandDto[]
  categories?: CategoryDto[]
}

export const getProductList = async ({
  categoryIds = [],
  conditionGrades = [],
  maxPrice = null,
  minPrice = null,
  page = 1,
  saleType = 'ALL',
  sellerId,
  size = 20,
  sort = 'LATEST',
}: ProductListParams = {}) => {
  if (!PRODUCT_API_ENABLED) {
    const filteredItems = PRODUCT_LIST_MOCK_DATA.filter((product) => {
      const matchesCategory =
        !categoryIds.length ||
        (product.categoryId !== null &&
          product.categoryId !== undefined &&
          categoryIds.includes(product.categoryId))
      const matchesCondition =
        !conditionGrades.length || conditionGrades.includes(product.conditionGrade)
      const matchesPrice =
        (minPrice === null || product.price >= minPrice) &&
        (maxPrice === null || product.price <= maxPrice)
      const matchesSaleType = saleType === 'ALL' || product.saleType === saleType

      return matchesCategory && matchesCondition && matchesPrice && matchesSaleType
    })
    const sortedItems = [...filteredItems]

    if (sort === 'PRICE_ASC') {
      sortedItems.sort((left, right) => left.price - right.price)
    } else if (sort === 'PRICE_DESC') {
      sortedItems.sort((left, right) => right.price - left.price)
    }

    const safePage = Math.max(page, 1)
    const safeSize = Math.max(size, 1)
    const startIndex = (safePage - 1) * safeSize
    const pagedItems = sortedItems.slice(startIndex, startIndex + safeSize)

    return {
      items: pagedItems,
      meta: {
        page: safePage,
        size: safeSize,
        totalElements: sortedItems.length,
        totalPages: Math.max(Math.ceil(sortedItems.length / safeSize), 1),
      } satisfies PageMeta,
    }
  }

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
      sellerId,
    },
  })
  const pageResponse = normalizePageResponse(unwrapApiData(response.data))
  const items = await Promise.all(pageResponse.items.map(toProductListItem))

  return {
    items,
    meta: pageResponse.meta,
  }
}

// 유사 상품 추천 목록. 실제 유사 판정·목록 API는 미구현(유사 기준도 BE 소관, docs/requests/BE 참고) →
// 현재는 mock(목록 mock에서 현재 상품 제외). BE 엔드포인트가 확정되면 이 자리를 실제 호출로 교체한다.
export const getSimilarProducts = async (productId: number): Promise<ProductListItem[]> => {
  if (PRODUCT_API_ENABLED) {
    return []
  }

  return PRODUCT_LIST_MOCK_DATA.filter((product) => product.id !== productId).slice(0, 8)
}

export const getProductDetail = async (productId: number): Promise<ProductDetailViewData> => {
  if (!PRODUCT_API_ENABLED) {
    return buildMockProductDetail(productId)
  }

  const response = await http.get<ApiResponse<ProductDetailDto>>(`/products/${productId}`)

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
  if (!PRODUCT_API_ENABLED) {
    return PRODUCT_CATEGORY_MOCK_DATA
  }

  const response = await http.get<ApiResponse<CategoryDto[]>>('/categories', { skipAuth: true })

  return unwrapApiData(response.data)
}

// 소분류(depth 3)를 부모 대분류(depth 2)로 묶어 필터/탭 옵션을 만든다. 같은 이름의 대분류가
// 성별(남성/여성/공용)마다 따로 있어 이름으로 병합한다(예: "아우터"는 성별 3개를 합쳐 하나).
export const buildProductCategoryOptions = (categories: CategoryDto[]): ProductCategoryOption[] => {
  const childrenByParentId = new Map<number, number[]>()

  categories
    .filter((category) => category.depth === 3)
    .forEach((category) => {
      const parentId = category.parentId
      if (parentId === null) return

      const siblingIds = childrenByParentId.get(parentId) ?? []
      siblingIds.push(category.id)
      childrenByParentId.set(parentId, siblingIds)
    })

  const groupedOptions = new Map<string, ProductCategoryOption>()

  categories
    .filter((category) => category.depth === 2)
    .forEach((category) => {
      const label = category.name.trim()
      if (!label) return

      const categoryIds = [category.id, ...(childrenByParentId.get(category.id) ?? [])]
      const existingOption = groupedOptions.get(label)

      if (existingOption) {
        existingOption.categoryIds.push(...categoryIds)
        return
      }

      groupedOptions.set(label, {
        id: category.id,
        label,
        categoryIds,
      })
    })

  return [...groupedOptions.values()].map((option) => ({
    ...option,
    categoryIds: [...new Set(option.categoryIds)],
  }))
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

export const getWishProductIds = async (userId: number) => {
  const productIds: number[] = []
  let page = 0
  let totalPages = 1

  do {
    const response = await http.get<
      ApiResponse<PageResponse<ProductWishDto> | BackendPageResponse<ProductWishDto>>
    >(`/users/${userId}/wishes`, {
      params: {
        page,
        size: 100,
      },
    })
    const pageResponse = normalizePageResponse(unwrapApiData(response.data))

    productIds.push(...pageResponse.items.map((wish) => wish.product.id))
    totalPages = pageResponse.meta.totalPages
    page += 1
  } while (page < totalPages)

  return productIds
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
    aiModelEnabled: draft.aiModelEnabled,
    aiModelGender: draft.aiModelEnabled ? draft.aiModelGender : null,
    aiQualityFindings: resolveRegistrationAiQualityFindings(draft),
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
    conditionGrade: normalizeConditionGrade(product.conditionGrade),
    saleType: toProductSaleType(product.saleType),
    saleStatus: product.saleStatus satisfies ProductSaleStatus,
    categoryId: product.categoryId,
    categoryName: product.categoryName ?? fallbackCategoryLabel(product.categoryId),
    imageUrl,
    imageAlt: `${product.title} 상품 이미지`,
    isLiked: product.isWished ?? product.isLiked,
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
    brand: product.brandName?.trim() || '',
    title: product.title,
    description: product.description?.trim() || '',
    category: product.categoryName?.trim() || '',
    conditionLabel: toConditionLabel(product.conditionGrade),
    sizeLabel: product.sizeLabel?.trim() || '',
    material: product.material?.trim() || '',
    color: product.color?.trim() || '',
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
    similarProducts: normalizeSimilarProducts(product.similarProducts),
    sellerDisclosedDefects: (product.defects ?? [])
      .map((defect) => defect.trim())
      .filter(Boolean)
      .map((defect) => ({
        title: defect,
        description: '',
      })),
    aiQualityAnalysis: product.aiQualityAnalysis ?? null,
  }
}

// 종료·취소·예약 방송은 상품 상세의 "라이브 입장" 대상이 아니다.
// BE status가 실제 LIVE인 경우에만 연결 라이브를 노출한다.
const toLinkedLive = (
  linkedLive: ProductDetailDto['linkedLive'],
): ProductDetailViewData['linkedLive'] => {
  if (!linkedLive || linkedLive.status?.trim().toUpperCase() !== 'LIVE') {
    return null
  }

  return {
    id: linkedLive.liveId,
    title: linkedLive.title,
    startsAt: linkedLive.startedAt ?? '',
    status: 'LIVE',
    thumbnailUrl: linkedLive.thumbnailUrl,
  }
}

const normalizeConditionGrade = (
  conditionGrade: ProductConditionGrade | null | undefined,
): ProductConditionGrade | '' =>
  conditionGrade && ['S', 'A', 'B', 'C'].includes(conditionGrade) ? conditionGrade : ''

const toConditionLabel = (conditionGrade: ProductConditionGrade | null | undefined) => {
  const normalizedGrade = normalizeConditionGrade(conditionGrade)
  return normalizedGrade ? `${normalizedGrade}급` : ''
}

const normalizeSimilarProducts = (
  products: SimilarProductPricePoint[] | null | undefined,
): SimilarProductPricePoint[] =>
  (products ?? []).filter(
    (product) =>
      Number.isInteger(product.id) &&
      product.id > 0 &&
      product.title.trim() !== '' &&
      Number.isFinite(product.price) &&
      product.price >= 0,
  )

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

const resolveRegistrationColor = (draft: ProductRegistrationDraft) => draft.color || null

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

// 사용자가 "하자 제외"로 뒤집지 않은(=하자로 인정한) finding만 제출한다.
const resolveRegistrationAiQualityFindings = (
  draft: ProductRegistrationDraft,
): ProductCreateAiQualityFindingRequest[] =>
  draft.aiPhotoResults.flatMap((result) => {
    const photo = draft.photos.find((item) => item.id === result.photoId)

    if (!photo || (photo.role !== 'front' && photo.role !== 'back')) {
      return []
    }

    return result.findings
      .filter((finding) => finding.isActualDefect)
      .map((finding) => ({
        photoRole: photo.role as 'front' | 'back',
        description: finding.description,
        box: finding.box,
      }))
  })

export const getCategoryCode = (categoryName: string) => {
  if (categoryName.includes('아우터')) return 'outer'
  if (categoryName.includes('상의')) return 'top'
  if (categoryName.includes('하의')) return 'bottom'
  if (categoryName.includes('원피스')) return 'dress'
  if (categoryName.includes('신발')) return 'shoes'
  if (categoryName.includes('액세서리')) return 'accessory'

  return ''
}
