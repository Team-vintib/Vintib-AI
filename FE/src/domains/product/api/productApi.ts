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
  ProductAiModelCut,
  ProductDetailViewData,
  SimilarProductPricePoint,
} from '@/domains/product/types/productDetail.types'
import type {
  ProductRegistrationAiFinding,
  ProductRegistrationAiPhotoResult,
  ProductRegistrationDraft,
  ProductRegistrationPhotoDraft,
  ProductRegistrationPhotoRole,
  ProductRegistrationSubmitResult,
} from '@/domains/product/types/productRegistration.types'
import { mapAiColorKeyToOptionId } from '@/domains/product/constants/aiColorPalette'
import { mapAiSectionToLabel } from '@/domains/product/constants/aiSectionLabels'
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
  'DRAFT' | 'ON_SALE' | 'AUCTION_SCHEDULED' | 'AUCTION_IN_PROGRESS' | 'AUCTION_FAILED' | 'SOLD'

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
  brand: string | null
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
  aiModelCut?: ProductAiModelCut | null
  updatedAt: string
}

interface ProductCreateRequest {
  title: string
  description: string
  categoryId: number | null
  brand: string | null
  conditionGrade: ProductConditionGrade | ''
  sizeLabel: string
  color: string | null
  material: string | null
  measurements: Record<string, number> | null
  defects: string[] | null
  aiModelEnabled: boolean
  aiModelGender: 'MALE' | 'FEMALE' | null
}

interface ProductCreateResponse extends Partial<ProductListDto> {
  productId?: number | string | null
}

// PATCH /products/{id}(부분 수정)이 실제로 받는 필드 — BE의 ProductUpdateRequest.java 그대로.
// aiModelEnabled/aiModelGender는 이 엔드포인트에 없다 — '기본 정보' 스텝을 나갈 때 이미
// 확정돼 draft 생성 시점(POST)에 실려 갔으므로 여기서 다시 보낼 필요가 없다.
// excludedQualityFindingKeys는 판매자가 하자를 인정/제외하는 시점 자체가 DRAFT 생성 이후라,
// 최종 확정값은 PATCH로만 보낼 수 있다(CH002 — 인정된 것만 보내던 이전 방식을 대체).
interface ProductUpdateRequest {
  title: string
  description: string
  categoryId: number | null
  brand: string | null
  conditionGrade: ProductConditionGrade | ''
  sizeLabel: string
  color: string | null
  material: string | null
  measurements: Record<string, number> | null
  defects: string[] | null
  // CH001/042: pricing 스텝의 AI 가격 추천 폴링 결과(product_match_key). 계산 전이면
  // null — BE는 null이면 미반영(기존 값 유지, null로 덮어쓰지 않음)한다.
  matchKey: string | null
  // CH002: 판매자가 "하자 아님"으로 표시한 finding의 key 목록. BE는 원본 검수 결과를 그대로
  // 갖고 있어서(quality_inspection_result) 이 key들만 있으면 상세 화면에서 isExcluded로
  // 표시할 수 있다. null이면 미반영, 빈 배열이면 제외 목록 전부 해제.
  excludedQualityFindingKeys: string[] | null
}

interface ProductImageUploadUrlResponse {
  key: string
  uploadUrl: string
  expiresInSeconds: number
}

// 이미지 용도(BE `ProductImageRole`, -310). FRONT/BACK은 AI 품질 검수용 앞·뒤 사진이고
// 상품당 한 장씩만 등록된다. **필수 필드라 빠지면 등록이 400으로 거절된다.**
type ProductImageRoleDto = 'FRONT' | 'BACK' | 'ADDITIONAL'

interface ProductImageRegisterRequest {
  key: string
  sortOrder: number
  isPrimary: boolean
  role: ProductImageRoleDto
}

const PRODUCT_IMAGE_ROLE_DTO_BY_DRAFT_ROLE: Record<
  ProductRegistrationPhotoRole,
  ProductImageRoleDto
> = {
  front: 'FRONT',
  back: 'BACK',
  additional: 'ADDITIONAL',
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

  const response = await http.get<
    ApiResponse<PageResponse<ProductListDto> | BackendPageResponse<ProductListDto>>
  >('/products', {
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

const SIMILAR_PRODUCT_LIMIT = 8

/**
 * 상품 상세 하단 유사 상품 추천 목록.
 *
 * 유사 상품 전용 엔드포인트는 없다. 상품 상세 응답의 `similarProducts`는 `id/title/price`뿐이라
 * 카드(브랜드·이미지·등급·판매방식·찜)를 못 채우므로, **같은 카테고리로 좁힌 상품 목록 API**를
 * 쓴다. BE의 유사 판정 기준(같은 카테고리 + 같은 브랜드 우선)을 그대로 따라 정렬한다.
 *
 * 카테고리를 모르면(상세에 categoryId가 없는 예전 응답 등) 빈 목록을 돌려준다 — 카테고리 없이
 * 전체 목록을 긁어오면 "유사"라고 부를 수 없는 결과가 섞인다.
 */
export const getSimilarProducts = async (
  productId: number,
  options: { categoryId?: number | null; brand?: string } = {},
): Promise<ProductListItem[]> => {
  if (!PRODUCT_API_ENABLED) {
    return PRODUCT_LIST_MOCK_DATA.filter((product) => product.id !== productId).slice(
      0,
      SIMILAR_PRODUCT_LIMIT,
    )
  }

  const { categoryId, brand } = options

  if (categoryId === null || categoryId === undefined) {
    return []
  }

  const { items } = await getProductList({
    categoryIds: [categoryId],
    size: 20,
    sort: 'LATEST',
  })

  return items
    .filter((product) => product.id !== productId && product.saleStatus !== 'SOLD')
    .sort((first, second) => {
      // 같은 브랜드를 앞으로. 그 외에는 목록 API가 준 최신순을 유지한다.
      const firstIsSameBrand = Boolean(brand) && first.brand === brand
      const secondIsSameBrand = Boolean(brand) && second.brand === brand

      return Number(secondIsSameBrand) - Number(firstIsSameBrand)
    })
    .slice(0, SIMILAR_PRODUCT_LIMIT)
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

export interface ProductAiModelCutStatusDto {
  status: 'NONE' | 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED'
  imageUrl: string | null
}

// 등록 시 켠 AI 착용컷의 생성 상태/결과를 조회한다(docs/requests/BE/039). 완료 화면에서
// 폴링용으로 쓴다 — mock 모드에서는 이 기능 자체가 없으니 즉시 NONE으로 응답한다.
export const getProductAiModelCutStatus = async (
  productId: number,
): Promise<ProductAiModelCutStatusDto> => {
  if (!PRODUCT_API_ENABLED) {
    return { status: 'NONE', imageUrl: null }
  }

  const response = await http.get<ApiResponse<ProductAiModelCutStatusDto>>(
    `/products/${productId}/ai-model-cut`,
  )

  return unwrapApiData(response.data)
}

// AI 하자 검수 result 원본(docs/requests/BE/041-quality-inspection-integration.md §2). BE가
// AI 응답을 그대로 실어 보내므로 이 안쪽 필드만 snake_case다(바깥 DTO는 camelCase).
export interface ProductQualityInspectionResultDto {
  inspection_id: string
  product_id: number
  condition_score: number
  condition_grade: 'S' | 'A' | 'B' | 'C'
  summary: string
  image_summaries: { image_index: number; summary: string }[]
  findings: {
    key: string
    defect_type: 'STAIN' | 'DIRT_MARK' | 'HOLE_TEAR' | 'DISCOLORATION' | 'PILLING' | 'FRAY'
    label: string
    status: 'DETECTED' | 'SUSPECTED'
    image_index: number
    no: number
    bbox: [number, number, number, number]
    confidence: number
    severity: 'MINOR' | 'MODERATE' | 'MAJOR'
    statement_required: boolean
    needs_seller_review: boolean
    description: string | null
    section: string
    section_no: number
  }[]
}

export interface ProductQualityInspectionStatusDto {
  status: 'NONE' | 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED'
  result: ProductQualityInspectionResultDto | null
}

// 앞/뒤 사진이 둘 다 등록되면 백그라운드로 도는 하자 검수 job의 상태/결과를 조회한다
// (docs/requests/BE/041). FE는 AI 게이트웨이를 직접 폴링하지 않고 이 BE 엔드포인트만 부른다
// (기존 aiGatewayApi.ts의 pollAiJob 직접-폴링 방식은 이 기능에는 더 이상 쓰지 않는다).
export const getProductQualityInspectionStatus = async (
  productId: number,
): Promise<ProductQualityInspectionStatusDto> => {
  if (!PRODUCT_API_ENABLED) {
    return { status: 'NONE', result: null }
  }

  const response = await http.get<ApiResponse<ProductQualityInspectionStatusDto>>(
    `/products/${productId}/quality-inspection`,
  )

  return unwrapApiData(response.data)
}

// docs/requests/FE/036 매핑표대로 AI 원본(snake_case)을 화면 렌더링용 타입(camelCase,
// ProductRegistrationAiFinding)으로 변환한다. photoIdByImageIndex는 앞=0/뒤=1로 업로드한
// 실제 photoId를 호출부가 넘겨준다(AI는 photoId라는 개념 자체를 모른다).
export const mapQualityInspectionResultToPhotoResults = (
  result: ProductQualityInspectionResultDto,
  photoIdByImageIndex: Record<number, string>,
): ProductRegistrationAiPhotoResult[] => {
  return Object.entries(photoIdByImageIndex).map(([imageIndexKey, photoId]) => {
    const imageIndex = Number(imageIndexKey)
    const findings: ProductRegistrationAiFinding[] = result.findings
      .filter((finding) => finding.image_index === imageIndex)
      .map((finding) => ({
        key: finding.key,
        defectType: finding.defect_type,
        label: finding.label,
        status: finding.status,
        imageIndex: finding.image_index,
        no: finding.no,
        bbox: finding.bbox,
        confidence: finding.confidence,
        severity: finding.severity,
        statementRequired: finding.statement_required,
        needsSellerReview: finding.needs_seller_review,
        description: finding.description,
        section: finding.section,
        sectionLabel: mapAiSectionToLabel(finding.section),
        isActualDefect: true,
      }))
    const summary =
      result.image_summaries.find((imageSummary) => imageSummary.image_index === imageIndex)
        ?.summary ?? null

    return { photoId, findings, confirmed: false, summary }
  })
}

// ── 상품 등록 사진 기반 카테고리·색상 자동 분류(사전업로드) ──────────────────────────
// docs/requests/FE/042-product-classify-preupload-integration.md. 상품이 아직 생성되기
// 전(사전업로드)에 사진 1장만으로 분류하는 완전 무상태 API라, jobId는 BE가 저장하지 않고
// FE가 직접 들고 있다가 상태 조회에 써야 한다.

interface ProductPreUploadUrlResponse {
  key: string
  uploadUrl: string
  expiresInSeconds: number
}

interface ProductClassifyJobResponse {
  jobId: string
}

interface ProductClassifyCategorySuggestionDto {
  majorCategoryId: number
  categoryId: number
  action: string
  score: number
}

interface ProductClassifyColorSuggestionDto {
  colorId: string
  action: string
  score: number
}

interface ProductClassifyResultDto {
  category: ProductClassifyCategorySuggestionDto | null
  colorPrimary: ProductClassifyColorSuggestionDto | null
  taxonomyVersion: string
}

export interface ProductClassifyStatusDto {
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED'
  result: ProductClassifyResultDto | null
  error: string | null
}

export const createProductPreUploadUrl = async (file: File) => {
  const response = await http.post<ApiResponse<ProductPreUploadUrlResponse>>(
    '/products/pre-upload/upload-url',
    { fileName: file.name, contentType: file.type },
  )

  return unwrapApiData(response.data)
}

export const uploadToPreUploadUrl = async (uploadUrl: string, file: File) => {
  await axios.put(uploadUrl, file, {
    headers: { 'Content-Type': file.type },
  })
}

export const triggerProductClassify = async (key: string) => {
  const response = await http.post<ApiResponse<ProductClassifyJobResponse>>(
    '/products/pre-upload/classify',
    { key },
  )

  return unwrapApiData(response.data).jobId
}

export const getProductClassifyStatus = async (jobId: string) => {
  const response = await http.get<ApiResponse<ProductClassifyStatusDto>>(
    `/products/pre-upload/classify/${jobId}`,
  )

  return unwrapApiData(response.data)
}

// AI 원본(카테고리 depth2/depth3 숫자 id, 색상 팔레트 코드)을 화면 select가 쓰는 문자열
// id로 변환한다. category/colorPrimary가 null이면(소분류 미지원 등) 그대로 null을 돌려준다.
export const mapClassifyResultToSuggestions = (result: ProductClassifyResultDto) => {
  const category = result.category
    ? {
        majorId: String(result.category.majorCategoryId),
        minorId: String(result.category.categoryId),
      }
    : null

  const mappedColorId = result.colorPrimary
    ? mapAiColorKeyToOptionId(result.colorPrimary.colorId)
    : null
  const color = mappedColorId ? { colorId: mappedColorId } : null

  return { category, color }
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

// AI 품질 검증(SY043)이 '상태/하자' 스텝 진입 시 미리 만들어두는 DRAFT 상품 생성 호출.
// submitProduct의 신규 분기와 로직을 공유한다 — 상품 생성 시점만 앞당겨졌을 뿐 필드는 동일하다.
export const createDraftProduct = async (
  draft: ProductRegistrationDraft,
  { categories = [] }: ProductSubmitOptions = {},
): Promise<number> => {
  const createResponse = await http.post<ApiResponse<ProductCreateResponse>>('/products', {
    title: draft.name.trim(),
    description: draft.description.trim(),
    categoryId: findCategoryId(draft, categories),
    brand: draft.brand.trim() || null,
    conditionGrade: draft.conditionGrade,
    sizeLabel: draft.size,
    color: resolveRegistrationColor(draft),
    material: draft.material.trim() || null,
    measurements: resolveRegistrationMeasurements(draft),
    defects: resolveRegistrationDefects(draft),
    aiModelEnabled: draft.aiModelEnabled,
    aiModelGender: draft.aiModelEnabled ? draft.aiModelGender : null,
  } satisfies ProductCreateRequest)

  return getCreatedProductId(unwrapApiData(createResponse.data))
}

export const submitProduct = async (
  draft: ProductRegistrationDraft,
  options: ProductSubmitOptions = {},
): Promise<ProductRegistrationSubmitResult> => {
  let productId: number

  if (draft.draftProductId) {
    // SY043: '상태/하자' 스텝 진입 시 이미 DRAFT 상품+이미지가 만들어져 있다 — 나머지
    // 필드만 부분 수정한다. PATCH가 aiModelEnabled/aiModelGender를 안 받지만, 이 값들은
    // '기본 정보' 스텝을 나갈 때 이미 확정돼 draft 생성 시점에 실려 갔으므로 다시 보낼
    // 필요가 없다(docs/requests/BE/046 참고).
    //
    // 다만 "이미 올라가 있겠지"라고 믿지는 않는다 — 사전 업로드가 실패해도 draftProductId는
    // 남아 있어서, 사진 0장인 상품이 그대로 등록 완료되던 문제가 있었다. 실제 상태를 확인하고
    // 비어 있으면 여기서 올린다.
    productId = draft.draftProductId
    const { categories = [] } = options

    await ensureProductImages(productId, draft.photos)

    await http.patch<ApiResponse<ProductCreateResponse>>(`/products/${productId}`, {
      title: draft.name.trim(),
      description: draft.description.trim(),
      categoryId: findCategoryId(draft, categories),
      brand: draft.brand.trim() || null,
      conditionGrade: draft.conditionGrade,
      sizeLabel: draft.size,
      color: resolveRegistrationColor(draft),
      material: draft.material.trim() || null,
      measurements: resolveRegistrationMeasurements(draft),
      defects: resolveRegistrationDefects(draft),
      matchKey: draft.priceMatchKey,
      excludedQualityFindingKeys: resolveExcludedQualityFindingKeys(draft),
    } satisfies ProductUpdateRequest)
  } else {
    productId = await createDraftProduct(draft, options)
    await uploadProductImages(productId, draft.photos)
  }

  await publishProduct(productId, draft)

  return {
    productId: String(productId),
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

/**
 * 상품에 이미지가 붙어 있는지 확인하고, 없으면 지금 올린다.
 *
 * 등록 마지막 단계에서 부르는 안전망이다. 사전 업로드(검수 스텝)가 실패한 채로 등록이 끝나면
 * 사진 없는 상품이 만들어지는데, 사용자는 그 사실을 알 방법이 없다.
 */
const ensureProductImages = async (productId: number, photos: ProductRegistrationPhotoDraft[]) => {
  let hasImages: boolean

  try {
    hasImages = (await getProductDetail(productId)).images.length > 0
  } catch {
    // 상세 조회가 실패하면(간헐적 500 — docs/requests/BE/029) 붙어 있는지 알 수 없다.
    // 이때 무작정 다시 올리면 이미지가 중복되므로 그대로 둔다. 사전 업로드가 실패한 경우는
    // draftProductId가 남지 않아 애초에 이 경로로 오지 않는다.
    return
  }

  if (hasImages) return

  await uploadProductImages(productId, photos)
}

/**
 * 등록 화면의 사진을 상품에 붙인다. 사진 한 장마다 세 단계를 돈다.
 *   ① presigned URL 발급 → ② S3에 PUT → ③ 서버에 "이 key가 이 상품 이미지"라고 등록
 *
 * **올릴 파일이 하나도 없으면 예외를 던진다.** 예전에는 조용히 건너뛰어서, 사진이 한 장도 없는
 * 상품이 등록 완료까지 가버렸다(실제로 106·109번 상품이 그렇게 만들어졌다).
 */
export const uploadProductImages = async (
  productId: number,
  photos: ProductRegistrationPhotoDraft[],
) => {
  const orderedPhotos = [...photos]
    .filter((photo) => Boolean(photo.file))
    .sort((left, right) => {
      if (left.isRepresentative !== right.isRepresentative) {
        return left.isRepresentative ? -1 : 1
      }

      return photos.indexOf(left) - photos.indexOf(right)
    })

  if (orderedPhotos.length === 0) {
    throw new Error('업로드할 상품 사진이 없습니다. 사진을 다시 선택해 주세요.')
  }

  for (const [index, photo] of orderedPhotos.entries()) {
    if (!photo.file) continue

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
        role: PRODUCT_IMAGE_ROLE_DTO_BY_DRAFT_ROLE[photo.role],
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
    brand: product.brand || '',
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
    brand: product.brand?.trim() || '',
    title: product.title,
    description: product.description?.trim() || '',
    category: product.categoryName?.trim() || '',
    categoryId: product.categoryId ?? null,
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
    aiModelCut: product.aiModelCut ?? null,
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
const toSaleTypeParam = (saleType: ProductSaleTypeTab['id']): ProductSaleTypeDto | undefined => {
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

const fallbackCategoryLabel = (categoryId: number | null) =>
  categoryId ? `카테고리 #${categoryId}` : ''

const findCategoryId = (draft: ProductRegistrationDraft, categories: CategoryDto[]) => {
  const numericCategoryId = Number(draft.categoryId)

  if (Number.isInteger(numericCategoryId) && numericCategoryId > 0) {
    return numericCategoryId
  }

  const matchedCategory = categories.find(
    (category) => getCategoryCode(category.name) === draft.categoryId,
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

// 판매자가 "하자 아님"으로 뒤집은(=isActualDefect false) finding의 key만 제출한다(CH002).
// BE는 원본 검수 결과(quality_inspection_result)를 이미 통째로 갖고 있어서, 이 key들만
// 있으면 상세 화면에서 isExcluded로 표시할 수 있다 — 나머지 필드를 다시 보낼 필요가 없다.
const resolveExcludedQualityFindingKeys = (draft: ProductRegistrationDraft): string[] =>
  draft.aiPhotoResults.flatMap((result) =>
    result.findings.filter((finding) => !finding.isActualDefect).map((finding) => finding.key),
  )

export const getCategoryCode = (categoryName: string) => {
  if (categoryName.includes('아우터')) return 'outer'
  if (categoryName.includes('상의')) return 'top'
  if (categoryName.includes('하의')) return 'bottom'
  if (categoryName.includes('원피스')) return 'dress'
  if (categoryName.includes('신발')) return 'shoes'
  if (categoryName.includes('액세서리')) return 'accessory'

  return ''
}
