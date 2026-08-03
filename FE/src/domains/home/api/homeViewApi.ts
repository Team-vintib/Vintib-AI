import type {
  HomeCategoryProductSection,
  HomeFollowedSellerItem,
  HomeLiveCardItem,
  HomeProductCardItem,
  HomeProductSaleStatus,
  HomeRecommendedProductItem,
  HomeViewData,
} from '@/domains/home/types/homeView.types'
import { http } from '@/shared/api/http'
import type { ApiResponse } from '@/shared/types/api.types'

type HomeLiveBroadcastStatus = 'LIVE' | 'SCHEDULED'
type HomeProductSellType = 'NORMAL' | 'AUCTION_SCHEDULED'
type HomeProductSellStatus = 'ON_SALE' | 'RESERVED' | 'SOLD_OUT'

interface HomeLiveCardResponse {
  liveId: number
  title: string
  hostNickname: string
  thumbnailUrl: string
  broadcastStatus: HomeLiveBroadcastStatus
  scheduledAt: string | null
  startedAt?: string | null
  viewerCount: number | null
  productCount: number | null
  reservationCount?: number | null
  categoryName?: string | null
}

interface HomeProductCardResponse {
  productId: number
  name: string
  brand: string
  thumbnailUrl: string
  sellType: HomeProductSellType
  sellStatus: HomeProductSellStatus
  price: number | null
  auctionScheduled: boolean
  sellerName?: string | null
  categoryName?: string | null
  isWished?: boolean | null
  startingBid?: number | null
  auctionStartsAt?: string | null
}

interface HomeCategoryProductSectionResponse {
  id: string
  title: string
  categoryName: string
  products: HomeProductCardResponse[]
}

interface HomeContentResponse {
  liveNow: HomeLiveCardResponse[]
  scheduledLives: HomeLiveCardResponse[]
  onSaleProducts: HomeProductCardResponse[]
  upcomingAuctionProducts: HomeProductCardResponse[]
  categoryProductSections?: HomeCategoryProductSectionResponse[]
}

interface HomeFollowedSellerResponse {
  sellerId: number
  sellerName: string
  profileImageUrl: string
  coverImageUrl: string
  followerCount: number
  followingCount?: number | null
  productCount: number
  liveCount?: number | null
  liveId: number | null
  liveStatus: HomeLiveBroadcastStatus | null
  liveTitle: string | null
  liveAt: string | null
}

interface FollowingContentResponse {
  empty: boolean
  lives: HomeLiveCardResponse[]
  products: HomeProductCardResponse[]
  followedSellers?: HomeFollowedSellerResponse[]
}

interface GetHomeViewDataOptions {
  isAuthenticated?: boolean
}

const FALLBACK_SELLER_NAME = '판매자 정보 확인 중'
const FOLLOWING_RECOMMENDATION_REASON = '팔로우한 판매자의 상품'
const CATEGORY_SECTION_PRODUCT_LIMIT = 8
const MIDDLE_CATEGORY_ORDER = [
  '아우터',
  '상의',
  '하의',
  '원피스',
  '신발',
  '가방',
  '액세서리',
] as const
const MIDDLE_CATEGORY_NAMES = new Set<string>(MIDDLE_CATEGORY_ORDER)
const SMALL_CATEGORY_TO_MIDDLE_CATEGORY: Record<string, (typeof MIDDLE_CATEGORY_ORDER)[number]> = {
  자켓: '아우터',
  코트: '아우터',
  가디건: '아우터',
  패딩: '아우터',
  후드집업: '아우터',
  티셔츠: '상의',
  셔츠: '상의',
  니트: '상의',
  후드티: '상의',
  맨투맨: '상의',
  민소매: '상의',
  데님: '하의',
  슬랙스: '하의',
  카고팬츠: '하의',
  스커트: '하의',
  숏팬츠: '하의',
  '트레이닝/조거': '하의',
  코튼팬츠: '하의',
  원피스: '원피스',
  '원피스 및 점프슈트': '원피스',
  점프슈트: '원피스',
  스니커즈: '신발',
  부츠: '신발',
  구두: '신발',
  '샌들/슬리퍼': '신발',
  백팩: '가방',
  숄더백: '가방',
  토트백: '가방',
  크로스백: '가방',
  파우치: '가방',
  모자: '액세서리',
  벨트: '액세서리',
  스카프: '액세서리',
  주얼리: '액세서리',
  시계: '액세서리',
  선글라스: '액세서리',
}

export const getHomeViewData = async ({
  isAuthenticated = false,
}: GetHomeViewDataOptions = {}): Promise<HomeViewData> => {
  const homeContent = await getHomeContent()
  const followingContent = isAuthenticated ? await getOptionalFollowingContent() : null

  return toHomeViewData(homeContent, followingContent)
}

const getHomeContent = async () => {
  const { data } = await http.get<ApiResponse<HomeContentResponse>>('/home', { skipAuth: true })

  return unwrapApiData(data)
}

const getFollowingContent = async () => {
  const { data } = await http.get<ApiResponse<FollowingContentResponse>>('/home/following')

  return unwrapApiData(data)
}

const getOptionalFollowingContent = async () => {
  try {
    return await getFollowingContent()
  } catch {
    return null
  }
}

const unwrapApiData = <T>(response: ApiResponse<T>) => {
  if (!response.success || !response.data) {
    throw new Error(response.error?.message ?? '홈 데이터를 불러오지 못했습니다.')
  }

  return response.data
}

const toHomeViewData = (
  homeContent: HomeContentResponse,
  followingContent: FollowingContentResponse | null,
): HomeViewData => {
  const followingProducts = followingContent?.empty ? [] : (followingContent?.products ?? [])
  const categoryProductSections = homeContent.categoryProductSections?.length
    ? toMiddleCategoryProductSections(homeContent.categoryProductSections)
    : []
  const followedSellers = followingContent
    ? followingContent.empty
      ? []
      : (followingContent.followedSellers ?? []).map(toHomeFollowedSellerItem)
    : []

  return {
    liveNow: homeContent.liveNow.map(toHomeLiveCardItem),
    scheduledLives: homeContent.scheduledLives.map(toHomeLiveCardItem),
    directSaleProducts: homeContent.onSaleProducts.map(toHomeProductCardItem),
    upcomingAuctionProducts: homeContent.upcomingAuctionProducts.map(toHomeProductCardItem),
    followedSellers,
    recommendedProducts:
      followingProducts.length > 0
        ? followingProducts.map(toHomeRecommendedProductItem)
        : [],
    categoryProductSections,
  }
}

const toHomeLiveCardItem = (live: HomeLiveCardResponse): HomeLiveCardItem => ({
  id: live.liveId,
  status: live.broadcastStatus,
  title: live.title,
  thumbnailUrl: live.thumbnailUrl,
  hostName: live.hostNickname,
  scheduledAt: live.scheduledAt ?? undefined,
  startedAt: live.startedAt ?? undefined,
  scheduledProductCount: live.productCount ?? undefined,
  viewerCount: live.viewerCount ?? undefined,
  reservationCount: live.reservationCount ?? undefined,
  categoryName: live.categoryName ?? undefined,
})

const toHomeProductCardItem = (product: HomeProductCardResponse): HomeProductCardItem => {
  const isAuction = product.auctionScheduled || product.sellType === 'AUCTION_SCHEDULED'

  return {
    id: product.productId,
    title: product.name,
    saleType: isAuction ? 'AUCTION' : 'DIRECT_SALE',
    saleStatus: toHomeProductSaleStatus(product),
    primaryImageUrl: product.thumbnailUrl,
    sellerName: product.sellerName ?? FALLBACK_SELLER_NAME,
    price: product.price ?? undefined,
    startingBid: product.startingBid ?? undefined,
    auctionStartsAt: product.auctionStartsAt ?? undefined,
    brandName: product.brand,
    categoryName: product.categoryName ?? undefined,
    isWished: product.isWished ?? false,
  }
}

const toHomeFollowedSellerItem = (
  seller: HomeFollowedSellerResponse,
): HomeFollowedSellerItem => ({
  id: seller.sellerId,
  liveId: seller.liveId ?? undefined,
  name: seller.sellerName,
  profileImageUrl: seller.profileImageUrl,
  coverImageUrl: seller.coverImageUrl,
  specialty: '',
  followerCount: seller.followerCount,
  followingCount: seller.followingCount ?? 0,
  newProductCount: seller.productCount,
  liveCount: seller.liveCount ?? 0,
  liveStatus: seller.liveStatus ?? undefined,
  liveTitle: seller.liveTitle ?? undefined,
  liveAt: seller.liveAt ?? undefined,
})

const toMiddleCategoryProductSections = (
  sections: HomeCategoryProductSectionResponse[],
): HomeCategoryProductSection[] => {
  const sectionProducts = sections.flatMap((section) =>
    section.products.map((product) => ({
      product,
      categoryName:
        toMiddleCategoryName(product.categoryName) ?? toMiddleCategoryName(section.categoryName),
    })),
  )
  const seenProductIds = new Set<number>()
  const productsByCategoryName = new Map<string, HomeProductCardItem[]>()

  sectionProducts.forEach(({ product, categoryName }) => {
    if (!categoryName || seenProductIds.has(product.productId)) {
      return
    }

    seenProductIds.add(product.productId)
    const products = productsByCategoryName.get(categoryName) ?? []

    if (products.length < CATEGORY_SECTION_PRODUCT_LIMIT) {
      products.push(toHomeProductCardItem(product))
      productsByCategoryName.set(categoryName, products)
    }
  })

  return MIDDLE_CATEGORY_ORDER.flatMap((categoryName) => {
    const products = productsByCategoryName.get(categoryName) ?? []

    return {
      id: toCategorySectionId(categoryName),
      title: categoryName,
      categoryName,
      products,
    }
  })
}

const toMiddleCategoryName = (categoryName?: string | null) => {
  if (!categoryName) {
    return null
  }

  if (MIDDLE_CATEGORY_NAMES.has(categoryName)) {
    return categoryName
  }

  return SMALL_CATEGORY_TO_MIDDLE_CATEGORY[categoryName] ?? null
}

const toCategorySectionId = (categoryName: string) =>
  categoryName
    .replace(/\s+/g, '-')
    .replace(/[^\w가-힣/-]/g, '')
    .toLowerCase()

const toHomeRecommendedProductItem = (
  product: HomeProductCardResponse,
): HomeRecommendedProductItem => ({
  ...toHomeProductCardItem(product),
  recommendationReason: FOLLOWING_RECOMMENDATION_REASON,
})

const toHomeProductSaleStatus = (product: HomeProductCardResponse): HomeProductSaleStatus => {
  if (product.auctionScheduled || product.sellType === 'AUCTION_SCHEDULED') {
    return 'AUCTION_SCHEDULED'
  }

  return product.sellStatus
}
