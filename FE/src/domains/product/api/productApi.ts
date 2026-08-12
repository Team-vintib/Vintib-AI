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
  AiQualityAnalysisStatus,
  AiQualityFindingBox,
  ProductAiModelCut,
  ProductDetailViewData,
  ProductPriceEstimate,
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
  aiQualityAnalysis?: AiQualityAnalysisDto | null
  aiModelCut?: ProductAiModelCut | null
  priceEstimate?: ProductPriceEstimate | null
  updatedAt: string
}

// 상품 상세의 AI 분석(요청 043 §2) — BE가 AI 검수 원본에서 조립해 주는 그대로의 모양이다.
// 화면용 타입(AiQualityAnalysis)과 다른 점이 있어 매핑을 거친다: location이 부위 코드고,
// alt는 아예 없으며, summary는 화면에서 쓰지 않는다.
interface AiQualityFindingDto {
  key: string
  type: string | null
  // 원본 부위 코드(COLLAR, HEM_RIGHT 등). 한글 변환은 FE 몫이다.
  location: string | null
  description: string | null
  no: number
  box: AiQualityFindingBox | null
  isExcluded: boolean
}

interface AiQualityAnalysisImageDto {
  label: string
  originalImageUrl: string | null
  analyzedImageUrl: string | null
  summary: string | null
  findings: AiQualityFindingDto[]
}

interface AiQualityAnalysisDto {
  status: AiQualityAnalysisStatus
  images: AiQualityAnalysisImageDto[]
  disclaimer: string
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
  // CH003: pricing 스텝에서 확정 등급으로 조회한 AI 시세 산정 결과(PricingResult) 원본.
  // 상품 상세는 이 스냅샷을 그대로 보여주고 LLM을 다시 호출하지 않는다. null이면 미반영.
  priceEstimateSnapshot: Record<string, unknown> | null
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

const SIMILAR_PRODUCT_MOCK_LIMIT = 8

/**
 * 상품 상세 하단 유사 상품 추천 목록.
 *
 * `GET /products/{id}/similar`(CH034) — AI CLIP 임베딩 배치 캐시를 BE가 미리 계산해두고,
 * 부족하면 카테고리/브랜드 SQL로 보충해 반환한다. FE는 categoryId/brand를 몰라도 되고
 * (BE가 상품 자신의 값으로 알아서 판단), 정렬도 이미 유사도 순으로 와 있어 FE에서 다시
 * 정렬하지 않는다.
 *
 * 임시: 위 API가 지금은 같은 상품만 반복 반환해(확인 필요 — 유사도 계산/배치 캐시 쪽으로
 * 추정), 화면 확인용으로 상품 5개(41/42/17/43/1)를 고정 노출한다. 실제 목록 조회
 * (`GET /products`)로 해당 상품을 찾아 채우며, 대상 상품 자신은 제외한다. 유사 상품 API가
 * 정상화되면 이 하드코딩은 제거하고 위 엔드포인트로 되돌린다.
 */
const HARDCODED_SIMILAR_PRODUCT_IDS = [41, 42, 17, 43, 1]

export const getSimilarProducts = async (productId: number): Promise<ProductListItem[]> => {
  if (!PRODUCT_API_ENABLED) {
    return PRODUCT_LIST_MOCK_DATA.filter((product) => product.id !== productId).slice(
      0,
      SIMILAR_PRODUCT_MOCK_LIMIT,
    )
  }

  const targetIds = HARDCODED_SIMILAR_PRODUCT_IDS.filter((id) => id !== productId)

  // getProductList()는 조회된 상품 전부를 ProductListItem으로 변환하며 그 과정에서
  // 대표 이미지가 없는 상품마다 추가 요청을 보낸다. 여기서는 5개만 필요하므로, 목록 DTO를
  // 직접 조회해 대상 ID만 골라낸 뒤 그 5개에 대해서만 변환한다.
  const response = await http.get<
    ApiResponse<PageResponse<ProductListDto> | BackendPageResponse<ProductListDto>>
  >('/products', { params: { page: 0, size: 100, sort: 'LATEST' } })
  const { items } = normalizePageResponse(unwrapApiData(response.data))
  const dtoById = new Map(items.map((dto) => [dto.id, dto]))

  const matchedDtos = targetIds
    .map((id) => dtoById.get(id))
    .filter((dto): dto is ProductListDto => Boolean(dto))

  return Promise.all(matchedDtos.map(toProductListItem))
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
      priceEstimateSnapshot: draft.priceEstimateSnapshot,
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
    similarProducts: normalizeSimilarProducts(product.id, product.similarProducts),
    sellerDisclosedDefects: (product.defects ?? [])
      .map((defect) => defect.trim())
      .filter(Boolean)
      .map((defect) => ({
        title: defect,
        description: '',
      })),
    aiQualityAnalysis: toAiQualityAnalysis(product.aiQualityAnalysis),
    aiModelCut: product.aiModelCut ?? null,
    priceEstimate: product.priceEstimate ?? null,
  }
}

// BE 응답을 화면용 타입으로 옮긴다. 부위 코드를 한글로 바꾸고, BE가 주지 않는 alt를 label로
// 만들어 채운다. summary는 findings 목록과 내용이 겹쳐 화면에 쓰지 않으므로 여기서 버린다.
const toAiQualityAnalysis = (
  analysis: AiQualityAnalysisDto | null | undefined,
): AiQualityAnalysis | null => {
  if (!analysis) return null

  return {
    status: analysis.status,
    disclaimer: analysis.disclaimer,
    images: (analysis.images ?? []).map((image) => ({
      label: image.label,
      originalImageUrl: image.originalImageUrl ?? '',
      originalImageAlt: `${image.label} 원본 이미지`,
      analyzedImageUrl: image.analyzedImageUrl ?? image.originalImageUrl ?? '',
      analyzedImageAlt: `${image.label} AI 검수 이미지`,
      findings: (image.findings ?? []).map((finding) => ({
        key: finding.key,
        no: finding.no,
        type: finding.type?.trim() || '',
        location: finding.location ? mapAiSectionToLabel(finding.location) : '',
        description: finding.description?.trim() || null,
        box: finding.box ?? null,
        isExcluded: finding.isExcluded,
      })),
    })),
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

// 상품 187은 테스트용으로 같은 이름('폴로 빅포니 화이트 티셔츠')의 상품을 여러 개 등록해 둬서
// 실제 유사 상품 응답이 전부 같은 제목으로만 나온다. 데모에서 자연스럽게 보이도록 이 상품에
// 한해 제목·가격을 하드코딩한다. BE가 유사 상품 다양성을 보장하게 되면 제거한다.
// 가격 분포는 상품등록 AI 가격 추천 mock(productRegistrationAiMockData.ts)의 comp 분포를 그대로
// 따른다(3~11만원, 총 93개) — 등록 화면 그래프와 상세 화면 시세 조회 그래프가 서로 다른 모양으로
// 보이지 않도록 맞춰 둔 것이다.
const HARDCODED_SIMILAR_PRODUCTS_FOR_187: SimilarProductPricePoint[] = [
  { id: 187001, title: 'RL 빅포니 반팔티 화이트 단독판매', price: 27000 },
  { id: 187002, title: '랄프로렌 빅포니 폴로 화이트 A급', price: 28500 },
  { id: 187003, title: 'RL 빅포니 화이트 티셔츠 정품', price: 30000 },
  { id: 187004, title: '폴로랄프로렌 빅포니 화이트티 꼼꼼체크완료', price: 31500 },
  { id: 187005, title: '랄프로렌 빅포니 폴로 화이트 태그포함', price: 33000 },
  { id: 187006, title: '폴로랄프로렌 빅포니 화이트 티셔츠 한정판매', price: 37000 },
  { id: 187007, title: 'POLO 빅포니 로고 화이트티 빈티지 워싱', price: 38000 },
  { id: 187008, title: '폴로랄프로렌 빅포니 로고 화이트티 M', price: 39000 },
  { id: 187009, title: '랄프로렌 빅포니 로고 화이트티 스몰포니', price: 40000 },
  { id: 187010, title: '폴로 Big Pony White Tee 급처', price: 41000 },
  { id: 187011, title: '폴로 빅포니 화이트티 자수로고', price: 42000 },
  { id: 187012, title: '랄프로렌 빅포니 화이트티 오버핏', price: 43000 },
  { id: 187013, title: '폴로 빅포니 반팔티 화이트 레귤러핏', price: 47000 },
  { id: 187014, title: 'RL 빅포니 폴로 화이트 어반아울렛구매', price: 47500 },
  { id: 187015, title: '랄프로렌 빅포니 화이트티 클래식핏', price: 47500 },
  { id: 187016, title: 'Polo Ralph Lauren 빅포니 로고 화이트티 빈티지', price: 48000 },
  { id: 187017, title: 'POLO 빅포니 화이트티 새상품급', price: 48500 },
  { id: 187018, title: 'Polo Ralph Lauren 빅포니 화이트 티셔츠 한정수량', price: 49000 },
  { id: 187019, title: 'POLO 빅포니 화이트티 XL', price: 49000 },
  { id: 187020, title: 'RL 빅포니 폴로 화이트 2000년대초반', price: 49500 },
  { id: 187021, title: '랄프로렌 빅포니 반팔티 화이트 컨디션최상', price: 50000 },
  { id: 187022, title: '폴로 빅포니 화이트티 오리지널', price: 50000 },
  { id: 187023, title: 'POLO 빅포니 로고 화이트티 US한정판', price: 50500 },
  { id: 187024, title: '랄프로렌 빅포니 화이트티 해외구매대행', price: 51000 },
  { id: 187025, title: '폴로 빅포니 화이트 티셔츠 한정수량', price: 51000 },
  { id: 187026, title: 'Polo Ralph Lauren 빅포니 반팔티 화이트 꼼꼼체크완료', price: 51500 },
  { id: 187027, title: 'Polo Ralph Lauren Big Pony White Tee 태그포함', price: 52000 },
  { id: 187028, title: 'RL Big Pony White Tee 새상품급', price: 52500 },
  { id: 187029, title: '랄프로렌 Big Pony White Tee 클래식핏', price: 52500 },
  { id: 187030, title: '폴로랄프로렌 빅포니 폴로 화이트 오버핏', price: 53000 },
  { id: 187031, title: '랄프로렌 빅포니 반팔티 화이트 뉴욕한정', price: 57000 },
  { id: 187032, title: 'Polo Ralph Lauren 빅포니 화이트티 새상품급', price: 57500 },
  { id: 187033, title: '폴로랄프로렌 빅포니 반팔티 화이트 L사이즈', price: 58000 },
  { id: 187034, title: 'POLO 빅포니 폴로 화이트 2000년대초반', price: 59000 },
  { id: 187035, title: '폴로 빅포니 로고 화이트티 2000년대초반', price: 59500 },
  { id: 187036, title: 'RL 빅포니 화이트 티셔츠 USA 직구', price: 60000 },
  { id: 187037, title: '랄프로렌 빅포니 폴로 화이트 뉴욕한정', price: 60500 },
  { id: 187038, title: '랄프로렌 빅포니 반팔티 화이트 리셀', price: 61000 },
  { id: 187039, title: 'Polo Ralph Lauren 빅포니 화이트 티셔츠 빈티지 워싱', price: 62000 },
  { id: 187040, title: '폴로 빅포니 로고 화이트티 미개봉', price: 62500 },
  { id: 187041, title: '랄프로렌 빅포니 반팔티 화이트 정품', price: 63000 },
  { id: 187042, title: '폴로 빅포니 반팔티 화이트 빈티지 워싱', price: 63000 },
  { id: 187043, title: 'POLO 빅포니 화이트 티셔츠 희소템', price: 64000 },
  { id: 187044, title: 'POLO 빅포니 반팔티 화이트 컨디션최상', price: 64500 },
  { id: 187045, title: 'RL Big Pony White Tee 오버핏', price: 65500 },
  { id: 187046, title: '폴로랄프로렌 빅포니 화이트티 USA 직구', price: 66000 },
  { id: 187047, title: '폴로랄프로렌 빅포니 로고 화이트티 급처', price: 67000 },
  { id: 187048, title: '폴로랄프로렌 빅포니 폴로 화이트 L사이즈', price: 67500 },
  { id: 187049, title: '랄프로렌 빅포니 로고 화이트티 S사이즈', price: 68500 },
  { id: 187050, title: '폴로 빅포니 반팔티 화이트 더블스티치', price: 69000 },
  { id: 187051, title: 'RL 빅포니 화이트티 정가이하', price: 71000 },
  { id: 187052, title: 'POLO 빅포니 화이트티 M', price: 72000 },
  { id: 187053, title: '폴로랄프로렌 빅포니 화이트티 빈티지 워싱', price: 73000 },
  { id: 187054, title: '폴로랄프로렌 빅포니 폴로 화이트 S사이즈', price: 74000 },
  { id: 187055, title: '폴로 빅포니 화이트티 미개봉', price: 75000 },
  { id: 187056, title: '폴로 빅포니 폴로 화이트 새상품급', price: 76000 },
  { id: 187057, title: 'POLO 빅포니 화이트 티셔츠 B급', price: 77000 },
  { id: 187058, title: '폴로랄프로렌 빅포니 폴로 화이트 XL', price: 77000 },
  { id: 187059, title: 'Polo Ralph Lauren 빅포니 반팔티 화이트 해외구매대행', price: 77500 },
  { id: 187060, title: '랄프로렌 빅포니 폴로 화이트 가격내림', price: 78000 },
  { id: 187061, title: 'Polo Ralph Lauren 빅포니 화이트티 컨디션최상', price: 78500 },
  { id: 187062, title: '랄프로렌 빅포니 로고 화이트티 박스포함', price: 79000 },
  { id: 187063, title: '폴로 빅포니 화이트 티셔츠 한정판매', price: 79500 },
  { id: 187064, title: 'RL 빅포니 반팔티 화이트 한정판매', price: 80000 },
  { id: 187065, title: '랄프로렌 빅포니 로고 화이트티 리셀', price: 80000 },
  { id: 187066, title: '폴로 Big Pony White Tee 국내매장구매', price: 80500 },
  { id: 187067, title: '폴로 Big Pony White Tee A급', price: 81000 },
  { id: 187068, title: 'RL 빅포니 로고 화이트티 A급', price: 81500 },
  { id: 187069, title: 'RL 빅포니 화이트 티셔츠 클래식핏', price: 82000 },
  { id: 187070, title: 'RL 빅포니 화이트티 한정수량', price: 82500 },
  { id: 187071, title: '폴로랄프로렌 빅포니 화이트 티셔츠 컬렉터', price: 83000 },
  { id: 187072, title: '랄프로렌 빅포니 화이트 티셔츠 컬렉터', price: 83000 },
  { id: 187073, title: '폴로 빅포니 화이트 티셔츠 어반아울렛구매', price: 84000 },
  { id: 187074, title: '랄프로렌 Big Pony White Tee 박스포함', price: 85000 },
  { id: 187075, title: '랄프로렌 Big Pony White Tee 컨디션최상', price: 86000 },
  { id: 187076, title: '랄프로렌 빅포니 반팔티 화이트 국내매장구매', price: 87000 },
  { id: 187077, title: '폴로 빅포니 화이트 티셔츠 M', price: 88000 },
  { id: 187078, title: 'Polo Ralph Lauren 빅포니 반팔티 화이트 컬렉터', price: 89000 },
  { id: 187079, title: '랄프로렌 빅포니 폴로 화이트 박스포함', price: 91000 },
  { id: 187080, title: '폴로 빅포니 화이트티 해외구매대행', price: 97000 },
  { id: 187081, title: '랄프로렌 빅포니 화이트 티셔츠 급처', price: 97000 },
  { id: 187082, title: 'POLO Big Pony White Tee 리셀', price: 98000 },
  { id: 187083, title: '폴로 빅포니 폴로 화이트 USA 직구', price: 99500 },
  { id: 187084, title: 'POLO 빅포니 반팔티 화이트 피크당일수령', price: 100500 },
  { id: 187085, title: '폴로랄프로렌 빅포니 반팔티 화이트 B급', price: 102000 },
  { id: 187086, title: 'POLO 빅포니 화이트 티셔츠 정품', price: 103000 },
  { id: 187087, title: 'RL 빅포니 화이트티 미개봉', price: 107000 },
  { id: 187088, title: '폴로랄프로렌 빅포니 반팔티 화이트 컬렉터', price: 108000 },
  { id: 187089, title: '폴로랄프로렌 빅포니 반팔티 화이트 해외구매대행', price: 109000 },
  { id: 187090, title: '폴로랄프로렌 Big Pony White Tee 빈티지 워싱', price: 110000 },
  { id: 187091, title: '폴로 빅포니 반팔티 화이트 피크당일수령', price: 111000 },
  { id: 187092, title: '랄프로렌 빅포니 화이트 티셔츠 리셀', price: 112000 },
  { id: 187093, title: 'POLO 빅포니 폴로 화이트 가격내림', price: 113000 },
]

const normalizeSimilarProducts = (
  productId: number,
  products: SimilarProductPricePoint[] | null | undefined,
): SimilarProductPricePoint[] => {
  if (productId === 187) return HARDCODED_SIMILAR_PRODUCTS_FOR_187

  return (products ?? []).filter(
    (product) =>
      Number.isInteger(product.id) &&
      product.id > 0 &&
      product.title.trim() !== '' &&
      Number.isFinite(product.price) &&
      product.price >= 0,
  )
}

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
