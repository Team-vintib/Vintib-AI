import { homeMockData } from '@/domains/home/constants/homeMockData'
import type {
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
  viewerCount: number | null
  productCount: number | null
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
}

interface HomeContentResponse {
  liveNow: HomeLiveCardResponse[]
  scheduledLives: HomeLiveCardResponse[]
  onSaleProducts: HomeProductCardResponse[]
  upcomingAuctionProducts: HomeProductCardResponse[]
}

interface FollowingContentResponse {
  empty: boolean
  lives: HomeLiveCardResponse[]
  products: HomeProductCardResponse[]
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
  const followingLives = followingContent?.empty ? [] : followingContent?.lives ?? []
  const followingProducts = followingContent?.empty ? [] : followingContent?.products ?? []

  return {
    liveNow: mergeLiveItems(
      followingLives.filter((live) => live.broadcastStatus === 'LIVE').map(toHomeLiveCardItem),
      homeContent.liveNow.map(toHomeLiveCardItem),
    ),
    scheduledLives: mergeLiveItems(
      followingLives.filter((live) => live.broadcastStatus === 'SCHEDULED').map(toHomeLiveCardItem),
      homeContent.scheduledLives.map(toHomeLiveCardItem),
    ),
    directSaleProducts: homeContent.onSaleProducts.map(toHomeProductCardItem),
    upcomingAuctionProducts: homeContent.upcomingAuctionProducts.map(toHomeProductCardItem),
    followedSellers: homeMockData.followedSellers,
    recommendedProducts:
      followingProducts.length > 0
        ? followingProducts.map(toHomeRecommendedProductItem)
        : homeMockData.recommendedProducts,
    contentCards: homeMockData.contentCards,
  }
}

const toHomeLiveCardItem = (live: HomeLiveCardResponse): HomeLiveCardItem => ({
  id: live.liveId,
  status: live.broadcastStatus,
  title: live.title,
  thumbnailUrl: live.thumbnailUrl,
  hostName: live.hostNickname,
  scheduledAt: live.scheduledAt ?? undefined,
  scheduledProductCount: live.productCount ?? undefined,
  viewerCount: live.viewerCount ?? undefined,
})

const toHomeProductCardItem = (product: HomeProductCardResponse): HomeProductCardItem => {
  const isAuction = product.auctionScheduled || product.sellType === 'AUCTION_SCHEDULED'

  return {
    id: product.productId,
    title: product.name,
    saleType: isAuction ? 'AUCTION' : 'DIRECT_SALE',
    saleStatus: toHomeProductSaleStatus(product),
    primaryImageUrl: product.thumbnailUrl,
    sellerName: FALLBACK_SELLER_NAME,
    price: product.price ?? undefined,
    brandName: product.brand,
    isWished: false,
  }
}

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

const mergeLiveItems = (
  primaryItems: HomeLiveCardItem[],
  fallbackItems: HomeLiveCardItem[],
): HomeLiveCardItem[] => {
  const liveItems = new Map<number, HomeLiveCardItem>()

  for (const live of [...primaryItems, ...fallbackItems]) {
    liveItems.set(live.id, live)
  }

  return [...liveItems.values()]
}
