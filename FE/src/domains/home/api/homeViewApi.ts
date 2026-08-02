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
  productCount: number
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
    ? homeContent.categoryProductSections.map(toHomeCategoryProductSection)
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
  newProductCount: seller.productCount,
  liveStatus: seller.liveStatus ?? undefined,
  liveTitle: seller.liveTitle ?? undefined,
  liveAt: seller.liveAt ?? undefined,
})

const toHomeCategoryProductSection = (
  section: HomeCategoryProductSectionResponse,
): HomeCategoryProductSection => ({
  id: section.id,
  title: section.title,
  categoryName: section.categoryName,
  products: section.products.map(toHomeProductCardItem),
})

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
