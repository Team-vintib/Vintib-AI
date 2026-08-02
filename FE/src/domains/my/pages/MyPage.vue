<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '@/domains/auth/stores/authStore'
import { useBusinessVerificationStore } from '@/domains/biz/stores/businessVerificationStore'
import {
  deleteMyDefaultTryOnImage,
  deleteMyProfileImage,
  getMyPageViewData,
  getMyInterestOptions,
  getMyInterests,
  removeMyWish,
  updateMyDefaultTryOnImage,
  updateMyInterests,
  updateMyProfile,
  updateMyProfileImage,
} from '@/domains/my/api/myApi'
import {
  MY_BUSINESS_STATUS_LABELS,
  MY_LIVE_STATUS_LABELS,
  MY_ORDER_STATUS_LABELS,
  MY_PRODUCT_STATUS_LABELS,
  MY_SECTION_OPTIONS,
  MY_SETTLEMENT_STATUS_LABELS,
} from '@/domains/my/constants/myMockData'
import type {
  MyLiveStatus,
  MyOrderStatus,
  MyPageViewData,
  MyProductStatus,
  MyProfileUpdateRequest,
  MySectionId,
} from '@/domains/my/types/my.types'
import { normalizeApiError } from '@/shared/api/http'
import type { InterestBrand, InterestCategory } from '@/shared/api/mockInterestStorage'
import { readImageFileAsDataUrl } from '@/shared/api/mockProfileMediaStorage'
import { ROUTE_NAMES, ROUTE_PATHS } from '@/shared/constants/routes'
import DefaultLayout from '@/shared/layouts/DefaultLayout.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const businessVerificationStore = useBusinessVerificationStore()

const viewData = ref<MyPageViewData | null>(null)
const selectedSection = ref<MySectionId>('dashboard')
const loadState = ref<'idle' | 'loading' | 'success' | 'error' | 'guest'>('idle')
const errorMessage = ref('')
const profileForm = ref<MyProfileUpdateRequest>({
  nickname: '',
  phoneNumber: '',
  postalCode: null,
  address: '',
  detailAddress: '',
  gender: 'FEMALE',
})
const profileSaveState = ref<'idle' | 'saving' | 'success' | 'error'>('idle')
const profileSaveMessage = ref('')
const profileImageInput = ref<HTMLInputElement | null>(null)
const selectedProfileImageFile = ref<File | null>(null)
const profileImagePreviewUrl = ref('')
const isProfileImageRemoved = ref(false)
const selectedProfileImageName = ref('')
const tryOnImageInput = ref<HTMLInputElement | null>(null)
const selectedTryOnImageFile = ref<File | null>(null)
const tryOnImagePreviewUrl = ref('')
const isTryOnImageRemoved = ref(false)
const selectedTryOnImageName = ref('')
const interestBrandOptions = ref<InterestBrand[]>([])
const interestCategoryOptions = ref<InterestCategory[]>([])
const selectedInterestBrandIds = ref<number[]>([])
const selectedInterestCategoryIds = ref<number[]>([])
const interestBrandSearchQuery = ref('')
const isInterestLoading = ref(false)
const interestLoadMessage = ref('')
const wishRemoveProductId = ref<number | null>(null)
const wishActionMessage = ref('')
type ProductFilterId = 'ALL' | Extract<MyProductStatus, 'ON_SALE' | 'SOLD'>
const productFilterOptions = [
  { id: 'ALL', label: '전체' },
  { id: 'ON_SALE', label: '판매 중' },
  { id: 'SOLD', label: '판매 완료' },
] satisfies Array<{ id: ProductFilterId; label: string }>
const selectedProductFilter = ref<ProductFilterId>('ALL')
type OrderFilterId = 'ALL' | 'IN_PROGRESS' | 'COMPLETED' | 'REFUND'
const orderFilterOptions = [
  { id: 'ALL', label: '전체' },
  { id: 'IN_PROGRESS', label: '진행 중' },
  { id: 'COMPLETED', label: '완료' },
  { id: 'REFUND', label: '환불' },
] satisfies Array<{ id: OrderFilterId; label: string }>
const selectedOrderFilter = ref<OrderFilterId>('ALL')
type SaleFilterId = 'ALL' | 'IN_PROGRESS' | 'COMPLETED' | 'REFUND'
const saleFilterOptions = [
  { id: 'ALL', label: '전체' },
  { id: 'IN_PROGRESS', label: '진행 중' },
  { id: 'COMPLETED', label: '완료' },
  { id: 'REFUND', label: '환불' },
] satisfies Array<{ id: SaleFilterId; label: string }>
const selectedSaleFilter = ref<SaleFilterId>('ALL')
type LiveFilterId = 'ALL' | MyLiveStatus
const liveFilterOptions = [
  { id: 'ALL', label: '전체' },
  { id: 'LIVE', label: '진행 중' },
  { id: 'SCHEDULED', label: '예약' },
  { id: 'ENDED', label: '종료' },
] satisfies Array<{ id: LiveFilterId; label: string }>
const selectedLiveFilter = ref<LiveFilterId>('ALL')
type SocialTabId = 'followers' | 'followings'
const socialTabOptions = [
  { id: 'followers', label: '팔로워' },
  { id: 'followings', label: '팔로잉' },
] satisfies Array<{ id: SocialTabId; label: string }>
const selectedSocialTab = ref<SocialTabId>('followers')

const profile = computed(() => viewData.value?.summary.profile ?? null)
const isLoading = computed(() => loadState.value === 'loading')
const isGuest = computed(() => loadState.value === 'guest')
const hasLoadError = computed(() => loadState.value === 'error')
const isProfileSaving = computed(() => profileSaveState.value === 'saving')
const profileInitial = computed(() => (profile.value?.nickname || profile.value?.name || '회').slice(0, 1))
const profileImageDisplayUrl = computed(() => {
  if (isProfileImageRemoved.value) {
    return ''
  }

  return profileImagePreviewUrl.value || profile.value?.profileImageUrl || ''
})
const profileAvatarUrl = computed(() => profileImageDisplayUrl.value)
const tryOnImageDisplayUrl = computed(() => {
  if (isTryOnImageRemoved.value) {
    return ''
  }

  return tryOnImagePreviewUrl.value || profile.value?.defaultTryOnImageUrl || ''
})
const filteredInterestBrands = computed(() => {
  const normalizedQuery = interestBrandSearchQuery.value.trim().toLowerCase()

  if (!normalizedQuery) {
    return interestBrandOptions.value
  }

  return interestBrandOptions.value.filter((brand) =>
    `${brand.name} ${brand.nameEn ?? ''}`.toLowerCase().includes(normalizedQuery),
  )
})
const visibleInterestCategories = computed(() =>
  interestCategoryOptions.value.filter((category) => category.depth <= 2),
)
const filteredProducts = computed(() => {
  const products = viewData.value?.products ?? []

  if (selectedProductFilter.value === 'ALL') {
    return products
  }

  return products.filter((item) => item.status === selectedProductFilter.value)
})
const filteredOrders = computed(() => {
  const orders = viewData.value?.orders ?? []

  if (selectedOrderFilter.value === 'ALL') {
    return orders
  }

  return orders.filter((order) => isOrderInFilter(order.status, selectedOrderFilter.value))
})
const filteredSales = computed(() => {
  const sales = viewData.value?.sales ?? []

  if (selectedSaleFilter.value === 'ALL') {
    return sales
  }

  return sales.filter((sale) => isSaleInFilter(sale.status, selectedSaleFilter.value))
})
const filteredLives = computed(() => {
  const lives = viewData.value?.lives ?? []

  if (selectedLiveFilter.value === 'ALL') {
    return lives
  }

  return lives.filter((live) => live.status === selectedLiveFilter.value)
})
const visibleSocialUsers = computed(() => {
  if (!viewData.value) {
    return []
  }

  return selectedSocialTab.value === 'followers'
    ? viewData.value.followers
    : viewData.value.followings
})
const businessSubmission = computed(() => businessVerificationStore.submission)
const businessStatusDescription = computed(() => {
  const status = profile.value?.businessVerificationStatus

  if (status === 'APPROVED') {
    return '사업자 인증이 완료되어 판매자 기능을 사용할 수 있습니다.'
  }

  if (status === 'PENDING') {
    return '제출한 사업자 정보가 검토 중입니다.'
  }

  if (status === 'REJECTED') {
    return '사업자 인증이 반려되었습니다. 정보를 확인한 뒤 다시 신청해 주세요.'
  }

  return '사업자 인증을 완료하면 판매자 기능을 사용할 수 있습니다.'
})
const businessActionLabel = computed(() => {
  const status = profile.value?.businessVerificationStatus

  if (status === 'APPROVED') {
    return '재제출'
  }

  if (status === 'PENDING') {
    return businessSubmission.value ? '제출 내역 보기' : '인증 상태 확인'
  }

  if (status === 'REJECTED') {
    return '다시 신청'
  }

  return '사업자 인증하기'
})
const businessInfoCards = computed(() => {
  const submission = businessSubmission.value
  const canShowMockBusinessInfo = profile.value?.businessVerificationStatus === 'APPROVED'

  return [
    {
      label: '상호명',
      value: submission?.businessName ?? (canShowMockBusinessInfo ? 'VinTib Archive' : '-'),
    },
    {
      label: '대표자',
      value: submission?.representativeName ?? (canShowMockBusinessInfo ? profile.value?.name : '-') ?? '-',
    },
    {
      label: '사업자등록번호',
      value: submission?.businessRegistrationNumber ?? (canShowMockBusinessInfo ? '1234567890' : '-'),
    },
    {
      label: '제출 일시',
      value: submission
        ? formatBusinessDate(submission.submittedAt)
        : canShowMockBusinessInfo
          ? '2026. 8. 1. 오후 02:30'
          : '-',
    },
  ]
})
const currentSectionLabel = computed(
  () =>
    MY_SECTION_OPTIONS.find((section) => section.id === selectedSection.value)?.label ??
    '마이페이지',
)

const homeCards = computed(() => {
  const summary = viewData.value?.summary

  return [
    {
      label: '진행 중인 판매',
      value: summary?.productStatusCounts.onSale ?? 0,
      section: 'products',
      suffix: '건',
      tone: 'green',
    },
    {
      label: '배송 중',
      value: summary?.todoCounts.shippingPending ?? 0,
      section: 'sales',
      suffix: '건',
      tone: 'orange',
    },
    {
      label: '정산 예정',
      value: summary?.settlementSummary.pendingAmount ?? summary?.pendingSettlementAmount ?? 0,
      section: 'sales',
      suffix: 'P',
      tone: 'green',
    },
    {
      label: '예정 라이브',
      value: summary?.todoCounts.scheduledLives ?? 0,
      section: 'lives',
      suffix: '건',
      tone: 'red',
    },
  ] satisfies Array<{
    label: string
    value: number
    section: MySectionId
    suffix?: string
    tone: 'green' | 'orange' | 'red'
  }>
})

const profileStats = computed(() => {
  const summary = viewData.value?.summary

  return [
    { label: '팔로워', value: summary?.counts.followers ?? 0, suffix: '' },
    { label: '팔로잉', value: 42, suffix: '' },
    {
      label: '판매 완료',
      value: summary?.salesPerformance.soldCount ?? summary?.counts.sales ?? 0,
      suffix: '건',
    },
    { label: '보유 포인트', value: summary?.pointBalance ?? 0, suffix: 'P' },
  ]
})

const pointCards = computed(() => {
  const summary = viewData.value?.summary

  return [
    {
      label: '사용 가능',
      value: summary?.pointBalance ?? 0,
      helper: '즉시 사용 가능',
    },
    {
      label: '입찰 보류',
      value: 39000,
      helper: '경매 종료 시 반환',
    },
    {
      label: '거래 보관',
      value: summary?.settlementSummary.escrowAmount ?? 0,
      helper: '구매 확정 후 정산',
    },
    {
      label: '판매 정산',
      value: summary?.settlementSummary.pendingAmount ?? summary?.pendingSettlementAmount ?? 0,
      helper: '출금 신청 가능',
    },
  ]
})

const kpiCards = computed(() => {
  const summary = viewData.value?.summary

  return [
    {
      label: '판매 완료',
      value: summary?.salesPerformance.soldCount ?? 0,
      section: 'sales',
      suffix: '건',
      helper: `판매 전환율 ${summary?.salesPerformance.sellThroughRate ?? 0}%`,
    },
    {
      label: '누적 순수익',
      value: summary?.salesPerformance.netRevenue ?? 0,
      section: 'sales',
      suffix: 'P',
      helper: `평균 ${formatPoint(summary?.salesPerformance.averageOrderAmount ?? 0)}`,
    },
    {
      label: '정산 완료',
      value: summary?.settlementSummary.settledAmount ?? 0,
      section: 'sales',
      suffix: 'P',
      helper: `마지막 정산 ${formatShortDate(summary?.settlementSummary.lastSettledAt)}`,
    },
  ] satisfies Array<{
    label: string
    value: number
    section: MySectionId
    suffix?: string
    helper: string
  }>
})

const todoCards = computed(() => {
  const todo = viewData.value?.summary.todoCounts

  return [
    { label: '배송 대기', value: todo?.shippingPending ?? 0, section: 'sales' },
    { label: '환불 요청', value: todo?.refundRequests ?? 0, section: 'sales' },
    { label: '예약 라이브', value: todo?.scheduledLives ?? 0, section: 'lives' },
  ] satisfies Array<{ label: string; value: number; section: MySectionId }>
})

const productStatusCards = computed(() => {
  const counts = viewData.value?.summary.productStatusCounts

  return [
    { label: '판매중', value: counts?.onSale ?? 0 },
    { label: '경매 예정', value: counts?.auctionScheduled ?? 0 },
    { label: '판매 완료', value: counts?.sold ?? 0 },
  ]
})

const monthlyRevenue = computed(() => viewData.value?.summary.monthlyRevenue ?? [])
const maxMonthlyRevenue = computed(() =>
  Math.max(1, ...monthlyRevenue.value.map((item) => item.revenue)),
)

const getRevenueBarHeight = (revenue: number) =>
  `${Math.max(10, Math.round((revenue / maxMonthlyRevenue.value) * 100))}%`

const formatPoint = (value: number) => `${value.toLocaleString('ko-KR')}P`

const formatShortDate = (value?: string) => {
  if (!value) {
    return '-'
  }

  return new Intl.DateTimeFormat('ko-KR', {
    month: 'numeric',
    day: 'numeric',
  }).format(new Date(value))
}

const syncProfileForm = () => {
  if (!profile.value) {
    return
  }

  profileForm.value = {
    nickname: profile.value.nickname,
    phoneNumber: profile.value.phoneNumber,
    postalCode: profile.value.postalCode,
    address: profile.value.address,
    detailAddress: profile.value.detailAddress,
    gender: profile.value.gender,
  }
  profileSaveState.value = 'idle'
  profileSaveMessage.value = ''
  selectedProfileImageFile.value = null
  profileImagePreviewUrl.value = ''
  isProfileImageRemoved.value = false
  selectedProfileImageName.value = ''
  selectedTryOnImageFile.value = null
  tryOnImagePreviewUrl.value = ''
  isTryOnImageRemoved.value = false
  selectedTryOnImageName.value = ''
}

const validateProfileForm = () => {
  const form = profileForm.value
  const phoneNumber = form.phoneNumber.replaceAll('-', '').trim()

  if (form.nickname.trim().length < 2) {
    return '닉네임은 2자 이상 입력해 주세요.'
  }

  if (!/^\d{10,11}$/.test(phoneNumber)) {
    return '전화번호는 숫자 10~11자리로 입력해 주세요.'
  }

  if (!form.address.trim()) {
    return '주소를 입력해 주세요.'
  }

  return ''
}

const isInterestBrandSelected = (brandId: number) => selectedInterestBrandIds.value.includes(brandId)

const toggleInterestBrand = (brandId: number) => {
  profileSaveState.value = 'idle'
  profileSaveMessage.value = ''

  if (isInterestBrandSelected(brandId)) {
    selectedInterestBrandIds.value = selectedInterestBrandIds.value.filter(
      (selectedBrandId) => selectedBrandId !== brandId,
    )
    return
  }

  selectedInterestBrandIds.value = [...selectedInterestBrandIds.value, brandId]
}

const handleInterestCategoryChange = () => {
  profileSaveState.value = 'idle'
  profileSaveMessage.value = ''
}

const selectProductFilter = (filterId: ProductFilterId) => {
  selectedProductFilter.value = filterId
}

const getProductFilterCount = (filterId: ProductFilterId) => {
  const products = viewData.value?.products ?? []

  if (filterId === 'ALL') {
    return products.length
  }

  return products.filter((item) => item.status === filterId).length
}

const isOrderInFilter = (status: MyOrderStatus, filterId: OrderFilterId) => {
  if (filterId === 'IN_PROGRESS') {
    return status === 'CREATED' || status === 'PAID' || status === 'SHIPPING' || status === 'DELIVERED'
  }

  if (filterId === 'COMPLETED') {
    return status === 'CONFIRMED'
  }

  if (filterId === 'REFUND') {
    return status === 'REFUND_REQUESTED' || status === 'REFUNDED'
  }

  return true
}

const isSaleInFilter = (status: MyOrderStatus, filterId: SaleFilterId) => {
  if (filterId === 'IN_PROGRESS') {
    return status === 'CREATED' || status === 'PAID' || status === 'SHIPPING' || status === 'DELIVERED'
  }

  if (filterId === 'COMPLETED') {
    return status === 'CONFIRMED'
  }

  if (filterId === 'REFUND') {
    return status === 'REFUND_REQUESTED' || status === 'REFUNDED'
  }

  return true
}

const selectOrderFilter = (filterId: OrderFilterId) => {
  selectedOrderFilter.value = filterId
}

const selectSaleFilter = (filterId: SaleFilterId) => {
  selectedSaleFilter.value = filterId
}

const selectLiveFilter = (filterId: LiveFilterId) => {
  selectedLiveFilter.value = filterId
}

const selectSocialTab = (tabId: SocialTabId) => {
  selectedSocialTab.value = tabId
}

const goToOrderDetail = (orderId: number) => {
  void router.push({ name: ROUTE_NAMES.MY_ORDER_DETAIL, params: { orderId } })
}

const goToSaleDetail = (saleId: number) => {
  void router.push({ name: ROUTE_NAMES.MY_SALE_DETAIL, params: { saleId } })
}

const goToLiveDetail = (liveId: number, status: MyLiveStatus) => {
  void router.push({
    name: status === 'LIVE' ? ROUTE_NAMES.LIVE_BROADCAST : ROUTE_NAMES.LIVE_WATCH,
    params: { liveId },
  })
}

const getOrderFilterCount = (filterId: OrderFilterId) => {
  const orders = viewData.value?.orders ?? []

  if (filterId === 'ALL') {
    return orders.length
  }

  return orders.filter((order) => isOrderInFilter(order.status, filterId)).length
}

const getSaleFilterCount = (filterId: SaleFilterId) => {
  const sales = viewData.value?.sales ?? []

  if (filterId === 'ALL') {
    return sales.length
  }

  return sales.filter((sale) => isSaleInFilter(sale.status, filterId)).length
}

const getLiveFilterCount = (filterId: LiveFilterId) => {
  const lives = viewData.value?.lives ?? []

  if (filterId === 'ALL') {
    return lives.length
  }

  return lives.filter((live) => live.status === filterId).length
}

const getSocialTabCount = (tabId: SocialTabId) => {
  if (!viewData.value) {
    return 0
  }

  return tabId === 'followers' ? viewData.value.followers.length : viewData.value.followings.length
}

const formatOrderDate = (value: string) =>
  new Intl.DateTimeFormat('ko-KR', {
    year: 'numeric',
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))

const formatBusinessDate = (value: string | Date) =>
  new Intl.DateTimeFormat('ko-KR', {
    year: 'numeric',
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))

const getOrderTypeLabel = (type: 'DIRECT' | 'AUCTION') =>
  type === 'AUCTION' ? '경매 낙찰' : '즉시 구매'

const loadMyInterests = async (userId: number) => {
  isInterestLoading.value = true
  interestLoadMessage.value = ''

  try {
    const [options, interests] = await Promise.all([
      getMyInterestOptions(),
      getMyInterests(userId),
    ])

    interestBrandOptions.value = options.brands
    interestCategoryOptions.value = options.categories
    selectedInterestBrandIds.value = interests.brands.map((brand) => brand.id)
    selectedInterestCategoryIds.value = interests.categories.map((category) => category.id)
  } catch (error) {
    interestLoadMessage.value = normalizeApiError(error).message
  } finally {
    isInterestLoading.value = false
  }
}

const openProfileImagePicker = () => {
  profileImageInput.value?.click()
}

const openTryOnImagePicker = () => {
  tryOnImageInput.value?.click()
}

const handleProfileImageChange = async (event: Event) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]

  if (!file) {
    return
  }

  if (!file.type.startsWith('image/')) {
    profileSaveState.value = 'error'
    profileSaveMessage.value = '이미지 파일만 업로드할 수 있습니다.'
    input.value = ''
    return
  }

  if (file.size > 5 * 1024 * 1024) {
    profileSaveState.value = 'error'
    profileSaveMessage.value = '프로필 사진은 5MB 이하로 선택해 주세요.'
    input.value = ''
    return
  }

  try {
    profileImagePreviewUrl.value = await readImageFileAsDataUrl(file, '프로필 사진을 읽지 못했습니다.')
    selectedProfileImageFile.value = file
    isProfileImageRemoved.value = false
    selectedProfileImageName.value = file.name
    profileSaveState.value = 'idle'
    profileSaveMessage.value = ''
  } catch (error) {
    profileSaveState.value = 'error'
    profileSaveMessage.value = normalizeApiError(error).message
  }
}

const handleTryOnImageChange = async (event: Event) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]

  if (!file) {
    return
  }

  if (!file.type.startsWith('image/')) {
    profileSaveState.value = 'error'
    profileSaveMessage.value = '이미지 파일만 업로드할 수 있습니다.'
    input.value = ''
    return
  }

  if (file.size > 5 * 1024 * 1024) {
    profileSaveState.value = 'error'
    profileSaveMessage.value = 'AI 시착용 사진은 5MB 이하로 선택해 주세요.'
    input.value = ''
    return
  }

  try {
    tryOnImagePreviewUrl.value = await readImageFileAsDataUrl(file, 'AI 시착용 사진을 읽지 못했습니다.')
    selectedTryOnImageFile.value = file
    isTryOnImageRemoved.value = false
    selectedTryOnImageName.value = file.name
    profileSaveState.value = 'idle'
    profileSaveMessage.value = ''
  } catch (error) {
    profileSaveState.value = 'error'
    profileSaveMessage.value = normalizeApiError(error).message
  }
}

const removeProfileImage = () => {
  selectedProfileImageFile.value = null
  profileImagePreviewUrl.value = ''
  selectedProfileImageName.value = ''
  isProfileImageRemoved.value = true

  if (profileImageInput.value) {
    profileImageInput.value.value = ''
  }
}

const removeTryOnImage = () => {
  selectedTryOnImageFile.value = null
  tryOnImagePreviewUrl.value = ''
  selectedTryOnImageName.value = ''
  isTryOnImageRemoved.value = true

  if (tryOnImageInput.value) {
    tryOnImageInput.value.value = ''
  }
}

const submitProfileForm = async () => {
  if (!profile.value || !viewData.value) {
    return
  }

  const validationMessage = validateProfileForm()
  if (validationMessage) {
    profileSaveState.value = 'error'
    profileSaveMessage.value = validationMessage
    return
  }

  profileSaveState.value = 'saving'
  profileSaveMessage.value = ''

  try {
    const request: MyProfileUpdateRequest = {
      ...profileForm.value,
      nickname: profileForm.value.nickname.trim(),
      phoneNumber: profileForm.value.phoneNumber.replaceAll('-', '').trim(),
      postalCode: profileForm.value.postalCode?.trim() || null,
      address: profileForm.value.address.trim(),
      detailAddress: profileForm.value.detailAddress.trim(),
    }
    const nextProfile = await updateMyProfile(profile.value.id, request)
    let nextProfileImageUrl = profile.value.profileImageUrl
    let nextTryOnImageUrl = profile.value.defaultTryOnImageUrl

    if (isProfileImageRemoved.value) {
      const response = await deleteMyProfileImage(profile.value.id)
      nextProfileImageUrl = response.profileImageUrl
    } else if (selectedProfileImageFile.value) {
      const response = await updateMyProfileImage(profile.value.id, selectedProfileImageFile.value)
      nextProfileImageUrl = response.profileImageUrl
    }

    if (isTryOnImageRemoved.value) {
      const response = await deleteMyDefaultTryOnImage(profile.value.id)
      nextTryOnImageUrl = response.defaultTryOnImageUrl
    } else if (selectedTryOnImageFile.value) {
      const response = await updateMyDefaultTryOnImage(profile.value.id, selectedTryOnImageFile.value)
      nextTryOnImageUrl = response.defaultTryOnImageUrl
    }

    await updateMyInterests(profile.value.id, {
      brandIds: [...selectedInterestBrandIds.value],
      categoryIds: [...selectedInterestCategoryIds.value],
    })

    viewData.value = {
      ...viewData.value,
      summary: {
        ...viewData.value.summary,
        profile: {
          ...nextProfile,
          profileImageUrl: nextProfileImageUrl,
          defaultTryOnImageUrl: nextTryOnImageUrl,
        },
      },
    }
    selectedProfileImageFile.value = null
    profileImagePreviewUrl.value = ''
    selectedProfileImageName.value = ''
    isProfileImageRemoved.value = false
    selectedTryOnImageFile.value = null
    tryOnImagePreviewUrl.value = ''
    selectedTryOnImageName.value = ''
    isTryOnImageRemoved.value = false
    profileSaveState.value = 'success'
    profileSaveMessage.value = '내 정보가 저장되었습니다.'
  } catch (error) {
    profileSaveState.value = 'error'
    profileSaveMessage.value = normalizeApiError(error).message
  }
}

const setSectionFromQuery = () => {
  const section = route.query.section
  const nextSection = typeof section === 'string' ? section : 'dashboard'
  const normalizedSection = nextSection === 'followers' ? 'social' : nextSection
  const isKnownSection = MY_SECTION_OPTIONS.some((option) => option.id === normalizedSection)

  selectedSection.value = isKnownSection ? (normalizedSection as MySectionId) : 'dashboard'
}

const selectSection = async (section: MySectionId) => {
  if (section === 'points') {
    await router.push({ name: ROUTE_NAMES.POINT })
    return
  }

  selectedSection.value = section
  await router.replace({
    name: ROUTE_NAMES.MY,
    query: section === 'dashboard' ? {} : { section },
  })
}

const loadMyPage = async () => {
  await authStore.validateStoredSession()

  if (!authStore.user?.id) {
    loadState.value = 'guest'
    return
  }

  loadState.value = 'loading'
  errorMessage.value = ''

  try {
    const nextViewData = await getMyPageViewData(authStore.user.id)
    viewData.value = mergeSessionProfile(nextViewData)
    await loadMyInterests(authStore.user.id)
    loadState.value = 'success'
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message
    loadState.value = 'error'
  }
}

const mergeSessionProfile = (data: MyPageViewData): MyPageViewData => {
  const sessionUser = authStore.user

  if (!sessionUser) {
    return data
  }

  const profile = data.summary.profile
  const sessionName = sessionUser.name?.trim() || sessionUser.email || ''

  return {
    ...data,
    summary: {
      ...data.summary,
      profile: {
        ...profile,
        id: sessionUser.id,
        email: profile.email || sessionUser.email,
        name: profile.name || sessionName,
        nickname: profile.nickname || sessionUser.name?.trim() || '',
        onboardingCompleted:
          profile.onboardingCompleted || sessionUser.onboardingCompleted === true,
      },
    },
  }
}

const goToLogin = () => {
  void router.push({ name: ROUTE_NAMES.AUTH_LOGIN, query: { redirect: ROUTE_PATHS.MY } })
}

const goToProductDetail = (productId: number) => {
  void router.push({
    name: ROUTE_NAMES.PRODUCT_DETAIL,
    params: { productId },
  })
}

const removeWishItem = async (productId: number) => {
  if (!authStore.user?.id || !viewData.value) {
    return
  }

  wishRemoveProductId.value = productId
  wishActionMessage.value = ''

  try {
    await removeMyWish(authStore.user.id, productId)

    const nextWishes = viewData.value.wishes.filter((wish) => wish.product.id !== productId)

    viewData.value = {
      ...viewData.value,
      summary: {
        ...viewData.value.summary,
        counts: {
          ...viewData.value.summary.counts,
          wishes: nextWishes.length,
        },
      },
      wishes: nextWishes,
      wishMeta: {
        ...viewData.value.wishMeta,
        totalElements: nextWishes.length,
        totalPages: nextWishes.length > 0 ? 1 : 0,
      },
    }

    wishActionMessage.value = '찜한 상품에서 제거했습니다.'
  } catch (error) {
    wishActionMessage.value = normalizeApiError(error).message
  } finally {
    wishRemoveProductId.value = null
  }
}

const goToBusinessVerification = () => {
  const status = profile.value?.businessVerificationStatus

  if (status === 'PENDING' && businessSubmission.value) {
    void router.push({ name: ROUTE_NAMES.BIZ_VERIFY_PENDING })
    return
  }

  void router.push({ name: ROUTE_NAMES.BIZ_VERIFY })
}

const logout = async () => {
  await authStore.logoutSession()
  await router.replace({ name: ROUTE_NAMES.HOME })
}

watch(
  () => route.query.section,
  () => {
    setSectionFromQuery()
  },
  { immediate: true },
)

watch(
  profile,
  () => {
    syncProfileForm()
  },
  { immediate: true },
)

onMounted(() => {
  void loadMyPage()
})
</script>

<template>
  <DefaultLayout content-max-width="1440px">
    <section class="my-shell" aria-labelledby="my-page-title">
      <div v-if="isLoading" class="my-state" role="status">마이페이지 정보를 불러오는 중입니다.</div>

      <div v-else-if="isGuest" class="my-state">
        <strong>로그인이 필요합니다.</strong>
        <button type="button" @click="goToLogin">로그인으로 이동</button>
      </div>

      <div v-else-if="hasLoadError" class="my-state" role="alert">
        <strong>마이페이지 정보를 불러오지 못했습니다.</strong>
        <p>{{ errorMessage }}</p>
        <button type="button" @click="loadMyPage">다시 시도</button>
      </div>

      <template v-else-if="viewData && profile">
        <aside class="my-sidebar" aria-label="마이페이지 메뉴">
          <div class="my-sidebar__profile">
            <div class="my-sidebar__avatar" aria-hidden="true">
              <img v-if="profileAvatarUrl" :src="profileAvatarUrl" :alt="`${profile.name} 프로필 사진`" />
              <span v-else>{{ profileInitial }}</span>
            </div>
            <div>
              <strong>{{ profile.name }} 님</strong>
              <span>{{ profile.memberType === 'BUSINESS' ? '사업자 회원' : '일반 회원' }}</span>
            </div>
          </div>

          <nav class="my-sidebar__nav">
            <button
              v-for="section in MY_SECTION_OPTIONS"
              :key="section.id"
              type="button"
              :class="{ 'my-sidebar__nav-item--active': selectedSection === section.id }"
              @click="selectSection(section.id)"
            >
              {{ section.label }}
            </button>
          </nav>

          <div class="my-sidebar__footer">
            <button type="button" @click="logout">
              로그아웃
            </button>
          </div>
        </aside>

        <main class="my-content">
          <header v-if="selectedSection !== 'dashboard'" class="my-content__header">
            <div>
              <h1 id="my-page-title">{{ currentSectionLabel }}</h1>
              <p v-if="selectedSection === 'seller'">
                판매 성과와 정산, 처리할 일을 확인합니다.
              </p>
            </div>
          </header>

          <template v-if="selectedSection === 'dashboard'">
            <section class="my-profile-hero" aria-label="회원 요약">
              <div class="my-profile-hero__avatar" aria-hidden="true">
                <img v-if="profileAvatarUrl" :src="profileAvatarUrl" :alt="`${profile.name} 프로필 사진`" />
                <span v-else>{{ profileInitial }}</span>
              </div>
              <div class="my-profile-hero__body">
                <div class="my-profile-hero__title">
                  <h2>{{ profile.name }} 님</h2>
                  <span>{{ MY_BUSINESS_STATUS_LABELS[profile.businessVerificationStatus] }}</span>
                </div>
                <p>
                  {{ profile.nickname }} · {{ profile.email }} · 가입 2024.03.15
                </p>
                <div class="my-profile-hero__stats">
                  <button
                    v-for="stat in profileStats"
                    :key="stat.label"
                    type="button"
                    @click="stat.label === '보유 포인트' ? selectSection('points') : undefined"
                  >
                    <strong>{{ stat.value.toLocaleString('ko-KR') }}{{ stat.suffix }}</strong>
                    <span>{{ stat.label }}</span>
                  </button>
                </div>
              </div>
              <button class="my-profile-hero__edit" type="button" @click="selectSection('profile')">
                정보 수정
              </button>
            </section>

            <section class="my-dashboard my-dashboard--home" aria-label="마이페이지 현황">
              <button
                v-for="card in homeCards"
                :key="card.label"
                class="my-dashboard__card"
                :class="`my-dashboard__card--${card.tone}`"
                type="button"
                @click="selectSection(card.section)"
              >
                <span>{{ card.label }}</span>
                <strong>
                  {{ card.value.toLocaleString('ko-KR') }}{{ card.suffix ?? '' }}
                </strong>
              </button>
            </section>

            <section class="my-card my-point-panel" aria-label="포인트 현황">
              <div class="my-card__title">
                <h2>포인트 현황</h2>
                <button type="button" @click="selectSection('points')">자세히 보기</button>
              </div>
              <div class="my-point-panel__grid">
                <article v-for="point in pointCards" :key="point.label">
                  <span>{{ point.label }}</span>
                  <strong>{{ formatPoint(point.value) }}</strong>
                  <p>{{ point.helper }}</p>
                </article>
              </div>
              <div class="my-point-panel__actions">
                <button type="button" @click="selectSection('points')">포인트 충전</button>
                <button type="button" @click="selectSection('points')">출금 신청</button>
              </div>
            </section>
          </template>

          <template v-else-if="selectedSection === 'seller'">
            <section class="my-dashboard" aria-label="판매자 대시보드 요약">
              <button
                v-for="card in kpiCards"
                :key="card.label"
                class="my-dashboard__card"
                type="button"
                @click="selectSection(card.section)"
              >
                <span>{{ card.label }}</span>
                <strong>
                  {{ card.value.toLocaleString('ko-KR') }}{{ card.suffix ?? '' }}
                </strong>
                <small>{{ card.helper }}</small>
              </button>
            </section>

            <section class="my-dashboard-grid" aria-label="판매 대시보드">
              <article class="my-card my-card--revenue">
                <div class="my-card__title">
                  <h2>월별 수익</h2>
                  <strong>{{ formatPoint(viewData.summary.salesPerformance.grossRevenue) }}</strong>
                </div>
                <div class="my-revenue-chart">
                  <div v-for="item in monthlyRevenue" :key="item.month" class="my-revenue-chart__item">
                    <span>{{ formatPoint(item.revenue) }}</span>
                    <div>
                      <i :style="{ height: getRevenueBarHeight(item.revenue) }" />
                    </div>
                    <b>{{ item.month }}</b>
                    <small>{{ item.soldCount }}건</small>
                  </div>
                </div>
              </article>

              <article class="my-card my-card--todo">
                <div class="my-card__title">
                  <h2>처리할 일</h2>
                  <button type="button" @click="selectSection('sales')">전체 보기</button>
                </div>
                <button
                  v-for="todo in todoCards"
                  :key="todo.label"
                  class="my-todo-row"
                  type="button"
                  @click="selectSection(todo.section)"
                >
                  <span>{{ todo.label }}</span>
                  <strong>{{ todo.value }}</strong>
                </button>
              </article>
            </section>

            <section class="my-card my-card--split" aria-label="판매 운영 현황">
              <div>
                <div class="my-card__title">
                  <h2>상품 상태</h2>
                  <button type="button" @click="selectSection('products')">관리</button>
                </div>
                <div class="my-status-grid">
                  <div v-for="status in productStatusCards" :key="status.label">
                    <span>{{ status.label }}</span>
                    <strong>{{ status.value }}</strong>
                  </div>
                </div>
              </div>
              <div>
                <div class="my-card__title">
                  <h2>최근 판매</h2>
                  <button type="button" @click="selectSection('sales')">내역</button>
                </div>
                <article v-for="sale in viewData.sales.slice(0, 3)" :key="sale.id" class="my-text-row">
                  <div>
                    <strong>{{ sale.productName }}</strong>
                    <p>{{ sale.buyerNickname }} · {{ sale.paidAmount.toLocaleString('ko-KR') }}P</p>
                  </div>
                  <span>{{ MY_SETTLEMENT_STATUS_LABELS[sale.settlementStatus] }}</span>
                </article>
              </div>
            </section>
          </template>

          <section v-else class="my-card" :aria-label="currentSectionLabel">
            <template v-if="selectedSection === 'profile'">
              <form class="my-profile-form" @submit.prevent="submitProfileForm">
                <div class="my-card__title">
                  <h2>기본 정보</h2>
                  <button type="submit" :disabled="isProfileSaving">
                    {{ isProfileSaving ? '저장 중' : '기본 정보 저장' }}
                  </button>
                </div>

                <p
                  v-if="profileSaveMessage"
                  class="my-profile-form__message"
                  :class="{ 'my-profile-form__message--error': profileSaveState === 'error' }"
                >
                  {{ profileSaveMessage }}
                </p>

                <div class="my-profile-photo">
                  <div class="my-profile-photo__preview" aria-hidden="true">
                    <img
                      v-if="profileImageDisplayUrl"
                      :src="profileImageDisplayUrl"
                      :alt="`${profile.name} 프로필 사진 미리보기`"
                    />
                    <span v-else>{{ profileInitial }}</span>
                  </div>
                  <div class="my-profile-photo__body">
                    <strong>프로필 사진</strong>
                    <p>마이페이지와 판매자 정보에 표시되는 사진입니다. AI 시착용 사진과 별도로 관리됩니다.</p>
                    <p v-if="selectedProfileImageName" class="my-profile-photo__file">
                      {{ selectedProfileImageName }}
                    </p>
                    <div class="my-profile-photo__actions">
                      <button type="button" @click="openProfileImagePicker">사진 선택</button>
                      <button v-if="profileImageDisplayUrl" type="button" @click="removeProfileImage">
                        사진 삭제
                      </button>
                    </div>
                  </div>
                  <input
                    ref="profileImageInput"
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    class="my-profile-photo__input"
                    aria-label="프로필 사진 선택"
                    @change="handleProfileImageChange"
                  />
                </div>

                <div class="my-tryon-photo">
                  <div class="my-tryon-photo__preview" aria-hidden="true">
                    <img
                      v-if="tryOnImageDisplayUrl"
                      :src="tryOnImageDisplayUrl"
                      :alt="`${profile.name} AI 시착용 사진 미리보기`"
                    />
                    <span v-else>{{ profileInitial }}</span>
                  </div>
                  <div class="my-tryon-photo__body">
                    <strong>AI 시착용 기본 사진</strong>
                    <p>온보딩에서 등록한 시착용 사진입니다. JPG, PNG, WebP 이미지를 5MB 이하로 업로드할 수 있습니다.</p>
                    <p v-if="selectedTryOnImageName" class="my-tryon-photo__file">
                      {{ selectedTryOnImageName }}
                    </p>
                    <div class="my-tryon-photo__actions">
                      <button type="button" @click="openTryOnImagePicker">사진 선택</button>
                      <button v-if="tryOnImageDisplayUrl" type="button" @click="removeTryOnImage">
                        사진 삭제
                      </button>
                    </div>
                  </div>
                  <input
                    ref="tryOnImageInput"
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    class="my-tryon-photo__input"
                    aria-label="AI 시착용 사진 선택"
                    @change="handleTryOnImageChange"
                  />
                </div>

                <div class="my-profile-form__grid">
                  <label>
                    <span>이름</span>
                    <input :value="profile.name" type="text" disabled />
                  </label>
                  <label>
                    <span>이메일</span>
                    <input :value="profile.email" type="email" disabled />
                  </label>
                  <label>
                    <span>닉네임</span>
                    <input v-model.trim="profileForm.nickname" type="text" maxlength="20" autocomplete="nickname" />
                  </label>
                  <label>
                    <span>전화번호</span>
                    <input v-model.trim="profileForm.phoneNumber" type="tel" inputmode="numeric" autocomplete="tel" />
                  </label>
                  <label>
                    <span>우편번호</span>
                    <input v-model.trim="profileForm.postalCode" type="text" inputmode="numeric" />
                  </label>
                  <label>
                    <span>성별</span>
                    <select v-model="profileForm.gender">
                      <option value="FEMALE">여성</option>
                      <option value="MALE">남성</option>
                    </select>
                  </label>
                  <label class="my-profile-form__wide">
                    <span>주소</span>
                    <input v-model.trim="profileForm.address" type="text" autocomplete="street-address" />
                  </label>
                  <label class="my-profile-form__wide">
                    <span>상세 주소</span>
                    <input v-model.trim="profileForm.detailAddress" type="text" />
                  </label>
                  <div class="my-profile-form__readonly">
                    <span>인증 상태</span>
                    <strong>{{ MY_BUSINESS_STATUS_LABELS[profile.businessVerificationStatus] }}</strong>
                  </div>
                </div>

                <section class="my-interest-editor" aria-labelledby="my-interest-editor-title">
                  <div class="my-interest-editor__header">
                    <div>
                      <h3 id="my-interest-editor-title">관심 정보</h3>
                      <p>맞춤 상품과 라이브 추천에 사용하는 브랜드와 카테고리입니다.</p>
                    </div>
                    <span v-if="isInterestLoading">불러오는 중</span>
                    <span v-else>
                      {{ selectedInterestBrandIds.length + selectedInterestCategoryIds.length }}개 선택
                    </span>
                  </div>

                  <p v-if="interestLoadMessage" class="my-interest-editor__message">
                    {{ interestLoadMessage }}
                  </p>

                  <div class="my-interest-editor__group">
                    <label class="my-interest-editor__search">
                      <span>관심 브랜드</span>
                      <input
                        v-model.trim="interestBrandSearchQuery"
                        type="search"
                        placeholder="브랜드명을 검색해 주세요."
                        :disabled="isInterestLoading"
                      />
                    </label>

                    <div v-if="filteredInterestBrands.length" class="my-interest-editor__chips">
                      <button
                        v-for="brand in filteredInterestBrands"
                        :key="brand.id"
                        type="button"
                        :class="{ 'my-interest-editor__chip--selected': isInterestBrandSelected(brand.id) }"
                        :aria-pressed="isInterestBrandSelected(brand.id)"
                        :disabled="isInterestLoading"
                        @click="toggleInterestBrand(brand.id)"
                      >
                        {{ brand.nameEn ? `${brand.name} (${brand.nameEn})` : brand.name }}
                      </button>
                    </div>
                    <p v-else class="my-interest-editor__empty">검색 결과가 없습니다.</p>
                  </div>

                  <div class="my-interest-editor__group">
                    <div class="my-interest-editor__label">관심 카테고리</div>
                    <div class="my-interest-editor__categories">
                      <label
                        v-for="category in visibleInterestCategories"
                        :key="category.id"
                        class="my-interest-editor__category"
                        :class="{
                          'my-interest-editor__category--selected': selectedInterestCategoryIds.includes(category.id),
                        }"
                      >
                        <input
                          v-model="selectedInterestCategoryIds"
                          type="checkbox"
                          :value="category.id"
                          :disabled="isInterestLoading"
                          @change="handleInterestCategoryChange"
                        />
                        <span>{{ category.name }}</span>
                      </label>
                    </div>
                  </div>
                </section>
              </form>
            </template>

            <template v-else-if="selectedSection === 'products'">
              <div class="my-card__title">
                <h2>판매 상품 관리</h2>
              </div>
              <div class="my-product-tabs" role="tablist" aria-label="판매 상품 상태 필터">
                <button
                  v-for="filter in productFilterOptions"
                  :key="filter.id"
                  type="button"
                  role="tab"
                  :aria-selected="selectedProductFilter === filter.id"
                  :class="{ 'my-product-tabs__item--active': selectedProductFilter === filter.id }"
                  @click="selectProductFilter(filter.id)"
                >
                  {{ filter.label }}
                  <span>{{ getProductFilterCount(filter.id) }}</span>
                </button>
              </div>
              <div v-if="filteredProducts.length" class="my-product-grid">
                <article v-for="item in filteredProducts" :key="item.id" class="my-product-card">
                  <button
                    type="button"
                    class="my-product-card__main"
                    @click="goToProductDetail(item.product.id)"
                  >
                    <img :src="item.product.imageUrl" :alt="item.product.imageAlt" />
                    <span>{{ MY_PRODUCT_STATUS_LABELS[item.status] }}</span>
                    <strong>{{ item.product.name }}</strong>
                    <p>{{ item.product.price.toLocaleString('ko-KR') }}P</p>
                  </button>
                </article>
              </div>
              <p v-else class="my-product-empty">해당 상태의 판매 상품이 없습니다.</p>
            </template>

            <template v-else-if="selectedSection === 'orders'">
              <div class="my-card__title">
                <h2>구매·낙찰 내역</h2>
              </div>
              <div class="my-order-tabs" role="tablist" aria-label="구매 내역 상태 필터">
                <button
                  v-for="filter in orderFilterOptions"
                  :key="filter.id"
                  type="button"
                  role="tab"
                  :aria-selected="selectedOrderFilter === filter.id"
                  :class="{ 'my-order-tabs__item--active': selectedOrderFilter === filter.id }"
                  @click="selectOrderFilter(filter.id)"
                >
                  {{ filter.label }}
                  <span>{{ getOrderFilterCount(filter.id) }}</span>
                </button>
              </div>
              <div v-if="filteredOrders.length" class="my-order-grid">
                <article
                  v-for="order in filteredOrders"
                  :key="order.id"
                  class="my-order-card"
                >
                  <button
                    type="button"
                    class="my-order-card__main"
                    @click="goToOrderDetail(order.id)"
                  >
                    <img :src="order.productThumbnailUrl" :alt="order.productName" />
                    <div class="my-order-card__body">
                      <div class="my-order-card__top">
                        <span>{{ getOrderTypeLabel(order.type) }}</span>
                        <strong>{{ MY_ORDER_STATUS_LABELS[order.status] }}</strong>
                      </div>
                      <h3>{{ order.productName }}</h3>
                      <p>{{ order.sellerNickname }}</p>
                      <dl>
                        <div>
                          <dt>결제 금액</dt>
                          <dd>{{ order.paidAmount.toLocaleString('ko-KR') }}P</dd>
                        </div>
                        <div>
                          <dt>구매 일시</dt>
                          <dd>{{ formatOrderDate(order.createdAt) }}</dd>
                        </div>
                      </dl>
                    </div>
                  </button>
                </article>
              </div>
              <p v-if="!filteredOrders.length" class="my-order-empty">
                해당 상태의 구매 내역이 없습니다.
              </p>
            </template>

            <template v-else-if="selectedSection === 'sales'">
              <div class="my-card__title">
                <h2>판매·정산 내역</h2>
              </div>
              <div class="my-order-tabs" role="tablist" aria-label="판매 내역 상태 필터">
                <button
                  v-for="filter in saleFilterOptions"
                  :key="filter.id"
                  type="button"
                  role="tab"
                  :aria-selected="selectedSaleFilter === filter.id"
                  :class="{ 'my-order-tabs__item--active': selectedSaleFilter === filter.id }"
                  @click="selectSaleFilter(filter.id)"
                >
                  {{ filter.label }}
                  <span>{{ getSaleFilterCount(filter.id) }}</span>
                </button>
              </div>
              <div v-if="filteredSales.length" class="my-order-grid">
                <article v-for="sale in filteredSales" :key="sale.id" class="my-order-card">
                  <button
                    type="button"
                    class="my-order-card__main"
                    @click="goToSaleDetail(sale.id)"
                  >
                    <img :src="sale.productThumbnailUrl" :alt="sale.productName" />
                    <div class="my-order-card__body">
                      <div class="my-order-card__top">
                        <span>{{ MY_ORDER_STATUS_LABELS[sale.status] }}</span>
                        <strong>{{ MY_SETTLEMENT_STATUS_LABELS[sale.settlementStatus] }}</strong>
                      </div>
                      <h3>{{ sale.productName }}</h3>
                      <p>{{ sale.buyerNickname }}</p>
                      <dl>
                        <div>
                          <dt>판매 금액</dt>
                          <dd>{{ sale.paidAmount.toLocaleString('ko-KR') }}P</dd>
                        </div>
                        <div>
                          <dt>판매 일시</dt>
                          <dd>{{ formatOrderDate(sale.createdAt) }}</dd>
                        </div>
                      </dl>
                    </div>
                  </button>
                </article>
              </div>
              <p v-if="!filteredSales.length" class="my-order-empty">
                해당 상태의 판매 내역이 없습니다.
              </p>
            </template>

            <template v-else-if="selectedSection === 'lives'">
              <div class="my-card__title">
                <h2>라이브 관리</h2>
              </div>
              <div class="my-order-tabs" role="tablist" aria-label="라이브 상태 필터">
                <button
                  v-for="filter in liveFilterOptions"
                  :key="filter.id"
                  type="button"
                  role="tab"
                  :aria-selected="selectedLiveFilter === filter.id"
                  :class="{ 'my-order-tabs__item--active': selectedLiveFilter === filter.id }"
                  @click="selectLiveFilter(filter.id)"
                >
                  {{ filter.label }}
                  <span>{{ getLiveFilterCount(filter.id) }}</span>
                </button>
              </div>
              <div v-if="filteredLives.length" class="my-order-grid">
                <article v-for="live in filteredLives" :key="live.id" class="my-order-card">
                  <button
                    type="button"
                    class="my-order-card__main"
                    @click="goToLiveDetail(live.id, live.status)"
                  >
                    <img :src="live.thumbnailUrl" :alt="live.title" />
                    <div class="my-order-card__body">
                      <div class="my-order-card__top">
                        <span>{{ MY_LIVE_STATUS_LABELS[live.status] }}</span>
                        <strong>상품 {{ live.productCount }}개</strong>
                      </div>
                      <h3>{{ live.title }}</h3>
                      <p>시청 {{ live.viewerCount.toLocaleString('ko-KR') }}</p>
                      <dl>
                        <div>
                          <dt>방송 일시</dt>
                          <dd>{{ formatOrderDate(live.broadcastAt) }}</dd>
                        </div>
                        <div>
                          <dt>관리 이동</dt>
                          <dd>{{ live.status === 'LIVE' ? '송출 화면' : '상세 화면' }}</dd>
                        </div>
                      </dl>
                    </div>
                  </button>
                </article>
              </div>
              <p v-if="!filteredLives.length" class="my-order-empty">
                해당 상태의 라이브가 없습니다.
              </p>
            </template>

            <template v-else-if="selectedSection === 'wishlist'">
              <div class="my-card__title">
                <h2>찜한 상품</h2>
              </div>
              <p v-if="wishActionMessage" class="my-wish-message" role="status">
                {{ wishActionMessage }}
              </p>
              <div v-if="viewData.wishes.length" class="my-product-grid">
                <article
                  v-for="wish in viewData.wishes"
                  :key="wish.product.id"
                  class="my-product-card my-wish-card"
                >
                  <button
                    type="button"
                    class="my-product-card__main"
                    @click="goToProductDetail(wish.product.id)"
                  >
                    <img :src="wish.product.imageUrl" :alt="wish.product.imageAlt" />
                    <span>찜</span>
                    <strong>{{ wish.product.name }}</strong>
                    <p>{{ wish.product.price.toLocaleString('ko-KR') }}P</p>
                  </button>
                  <div class="my-wish-card__meta">
                    <span>{{ wish.product.brand }}</span>
                    <span>{{ formatOrderDate(wish.wishedAt) }}</span>
                  </div>
                  <button
                    type="button"
                    class="my-wish-card__remove"
                    :disabled="wishRemoveProductId === wish.product.id"
                    @click="removeWishItem(wish.product.id)"
                  >
                    {{ wishRemoveProductId === wish.product.id ? '해제 중' : '찜 해제' }}
                  </button>
                </article>
              </div>
              <p v-else class="my-product-empty">찜한 상품이 없습니다.</p>
            </template>

            <template v-else-if="selectedSection === 'social'">
              <div class="my-card__title">
                <h2>팔로워·팔로잉</h2>
              </div>
              <div class="my-order-tabs" role="tablist" aria-label="팔로워 팔로잉 탭">
                <button
                  v-for="tab in socialTabOptions"
                  :key="tab.id"
                  type="button"
                  role="tab"
                  :aria-selected="selectedSocialTab === tab.id"
                  :class="{ 'my-order-tabs__item--active': selectedSocialTab === tab.id }"
                  @click="selectSocialTab(tab.id)"
                >
                  {{ tab.label }}
                  <span>{{ getSocialTabCount(tab.id) }}</span>
                </button>
              </div>
              <div v-if="visibleSocialUsers.length" class="my-social-grid">
                <article v-for="user in visibleSocialUsers" :key="user.id" class="my-social-card">
                  <div class="my-social-card__avatar" aria-hidden="true">
                    <img v-if="user.profileImageUrl" :src="user.profileImageUrl" :alt="user.nickname" />
                    <span v-else>{{ user.nickname.slice(0, 1) }}</span>
                  </div>
                  <div class="my-social-card__body">
                    <strong>{{ user.nickname }}</strong>
                    <p>{{ user.introduction }}</p>
                    <dl>
                      <div>
                        <dt>팔로워</dt>
                        <dd>{{ user.followerCount.toLocaleString('ko-KR') }}</dd>
                      </div>
                      <div>
                        <dt>팔로잉</dt>
                        <dd>{{ user.followingCount.toLocaleString('ko-KR') }}</dd>
                      </div>
                    </dl>
                    <span>{{ formatOrderDate(user.followedAt) }}</span>
                  </div>
                  <button type="button" disabled>
                    {{ selectedSocialTab === 'followers' && !user.isFollowing ? '팔로우' : '프로필 보기' }}
                  </button>
                </article>
              </div>
              <p v-else class="my-product-empty">표시할 사용자가 없습니다.</p>
            </template>

            <template v-else-if="selectedSection === 'business'">
              <div class="my-card__title">
                <h2>사업자 정보</h2>
                <button type="button" @click="goToBusinessVerification">
                  {{ businessActionLabel }}
                </button>
              </div>
              <section class="my-business-status" aria-label="사업자 인증 상태">
                <div>
                  <span>{{ profile.memberType === 'BUSINESS' ? '사업자 회원' : '일반 회원' }}</span>
                  <strong>{{ MY_BUSINESS_STATUS_LABELS[profile.businessVerificationStatus] }}</strong>
                  <p>{{ businessStatusDescription }}</p>
                </div>
                <button type="button" @click="goToBusinessVerification">
                  {{ businessActionLabel }}
                </button>
              </section>
              <dl class="my-business-grid">
                <div v-for="item in businessInfoCards" :key="item.label">
                  <dt>{{ item.label }}</dt>
                  <dd>{{ item.value }}</dd>
                </div>
              </dl>
              <div class="my-business-guide">
                <strong>사업자 정보 관리</strong>
                <p>인증 정보 변경이 필요하면 사업자 정보를 다시 제출해 검토를 요청할 수 있습니다.</p>
              </div>
            </template>
          </section>
        </main>
      </template>
    </section>
  </DefaultLayout>
</template>

<style scoped lang="scss">
.my-shell {
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr);
  gap: 0;
  min-height: 720px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
  overflow: hidden;
}

.my-sidebar {
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--color-border);
  background: var(--color-surface);
}

.my-sidebar__profile {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  min-height: 76px;
  padding: var(--space-4);
  border-bottom: 1px solid var(--color-border);
}

.my-sidebar__avatar {
  display: grid;
  flex: 0 0 auto;
  place-items: center;
  width: 38px;
  height: 38px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface-secondary);
  color: var(--color-text-primary);
  font-size: 15px;
  font-weight: var(--font-weight-extrabold);
  overflow: hidden;
}

.my-sidebar__avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.my-sidebar__profile strong,
.my-row strong,
.my-text-row strong,
.my-empty strong {
  display: block;
  color: var(--color-text-primary);
  font-size: 14px;
  font-weight: var(--font-weight-bold);
  line-height: 21px;
}

.my-sidebar__profile span {
  display: block;
  color: var(--color-text-secondary);
  font-size: 11px;
  line-height: 17px;
}

.my-sidebar__nav {
  display: grid;
  gap: 4px;
  padding: 12px 8px;
}

.my-sidebar__nav button,
.my-sidebar__footer button {
  display: flex;
  align-items: center;
  width: 100%;
  min-height: var(--button-height-small);
  padding: 0 var(--space-3);
  border: 0;
  border-radius: var(--radius-control);
  background: transparent;
  color: var(--color-text-secondary);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-semibold);
  line-height: 22px;
  text-align: left;
}

.my-sidebar__nav button:hover,
.my-sidebar__nav-item--active {
  background: var(--color-primary-soft) !important;
  color: var(--color-primary) !important;
}

.my-sidebar__footer {
  margin-top: auto;
  padding: 12px;
  border-top: 1px solid var(--color-border);
}

.my-content {
  min-width: 0;
  background: var(--color-page);
}

.my-content__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 96px;
  padding: 28px 32px 18px;
}

.my-content__header h1 {
  color: var(--color-text-primary);
  font-size: 28px;
  font-weight: var(--font-weight-extrabold);
  line-height: 36px;
}

.my-content__header p,
.my-row p,
.my-text-row p,
.my-empty p {
  margin-top: 2px;
  color: var(--color-text-secondary);
  font-size: 12px;
  line-height: 18px;
}

.my-content__actions {
  display: flex;
  gap: var(--space-2);
}

.my-content__actions button,
.my-card__title button,
.my-state button {
  min-height: var(--button-height-small);
  padding: 0 var(--space-4);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-bold);
  transition:
    border-color 160ms ease,
    background-color 160ms ease,
    color 160ms ease,
    box-shadow 160ms ease;
}

.my-content__actions button:first-child,
.my-card__title button:first-of-type {
  border-color: var(--color-primary);
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

.my-content__actions button:hover,
.my-card__title button:hover,
.my-state button:hover {
  background: var(--color-surface-secondary);
}

.my-content__actions button:first-child:hover,
.my-card__title button:first-of-type:hover {
  background: var(--color-primary-hover);
}

.my-content__actions button:focus-visible,
.my-card__title button:focus-visible,
.my-state button:focus-visible,
.my-profile-hero__edit:focus-visible,
.my-profile-hero__stats button:focus-visible,
.my-dashboard__card:focus-visible,
.my-todo-row:focus-visible,
.my-product-tabs button:focus-visible,
.my-order-tabs button:focus-visible,
.my-product-card__main:focus-visible,
.my-order-card__main:focus-visible,
.my-wish-card__remove:focus-visible,
.my-business-status button:focus-visible,
.my-profile-photo__actions button:focus-visible,
.my-tryon-photo__actions button:focus-visible,
.my-interest-editor__chips button:focus-visible,
.my-point-panel__actions button:focus-visible {
  outline: 3px solid var(--color-primary-soft);
  outline-offset: 2px;
}

.my-profile-hero {
  display: grid;
  grid-template-columns: 112px minmax(0, 1fr) auto;
  align-items: start;
  gap: 24px;
  min-height: 180px;
  margin: 32px 32px 24px;
  padding: 32px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
  box-shadow: 0 1px 3px rgb(23 26 31 / 10%);
}

.my-profile-hero__avatar {
  display: grid;
  place-items: center;
  width: 88px;
  height: 88px;
  border-radius: 50%;
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-size: 32px;
  font-weight: var(--font-weight-extrabold);
  overflow: hidden;
}

.my-profile-hero__avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.my-profile-hero__body {
  min-width: 0;
}

.my-profile-hero__title {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}

.my-profile-hero__title h2 {
  color: var(--color-text-primary);
  font-size: 28px;
  font-weight: var(--font-weight-extrabold);
  line-height: 36px;
}

.my-profile-hero__title span {
  min-height: 28px;
  padding: 5px 12px;
  border-radius: var(--radius-badge);
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-size: 12px;
  font-weight: var(--font-weight-bold);
}

.my-profile-hero__body > p {
  margin-top: 4px;
  color: var(--color-text-secondary);
  font-size: 14px;
  line-height: 22px;
}

.my-profile-hero__stats {
  display: flex;
  flex-wrap: wrap;
  gap: 34px;
  margin-top: 22px;
}

.my-profile-hero__stats button {
  display: grid;
  gap: 4px;
  min-width: 64px;
  padding: 0;
  border: 0;
  background: transparent;
  text-align: left;
}

.my-profile-hero__stats strong {
  color: var(--color-text-primary);
  font-size: 24px;
  font-variant-numeric: tabular-nums;
  font-weight: var(--font-weight-extrabold);
  line-height: 30px;
}

.my-profile-hero__stats span {
  color: var(--color-text-secondary);
  font-size: 12px;
  font-weight: var(--font-weight-semibold);
}

.my-profile-hero__edit {
  min-height: var(--button-height-small);
  padding: 0 var(--space-4);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-bold);
}

.my-dashboard {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  padding: 0 32px 16px;
}

.my-dashboard--home {
  grid-template-columns: repeat(4, minmax(0, 1fr));
  padding-bottom: 24px;
}

.my-dashboard__card,
.my-card {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
  box-shadow: 0 1px 3px rgb(23 26 31 / 10%);
}

.my-dashboard__card {
  display: grid;
  gap: 8px;
  min-height: 128px;
  padding: 20px;
  border-radius: var(--radius-card);
  text-align: left;
  transition:
    border-color 160ms ease,
    box-shadow 160ms ease,
    transform 160ms ease;
}

.my-dashboard__card:hover {
  border-color: var(--color-border-strong);
  box-shadow: 0 6px 18px rgb(23 26 31 / 10%);
  transform: translateY(-1px);
}

.my-dashboard--home .my-dashboard__card {
  align-content: center;
  min-height: 128px;
  padding: 22px;
}

.my-dashboard__card span {
  color: var(--color-text-secondary);
  font-size: 12px;
  font-weight: var(--font-weight-semibold);
  line-height: 18px;
}

.my-dashboard__card strong {
  color: var(--color-text-primary);
  font-size: 24px;
  font-variant-numeric: tabular-nums;
  font-weight: var(--font-weight-extrabold);
  line-height: 32px;
}

.my-dashboard__card small {
  color: var(--color-text-muted);
  font-size: 12px;
  font-weight: var(--font-weight-medium);
  line-height: 18px;
}

.my-point-panel {
  gap: 20px;
}

.my-point-panel .my-card__title button {
  min-height: auto;
  padding: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  color: var(--color-text-primary);
}

.my-point-panel__grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.my-point-panel__grid article {
  display: grid;
  gap: 8px;
  min-height: 112px;
  padding: 20px;
  border-radius: var(--radius-control);
  background: var(--color-surface-secondary);
}

.my-point-panel__grid span {
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: var(--font-weight-semibold);
}

.my-point-panel__grid strong {
  color: var(--color-text-primary);
  font-size: 22px;
  font-variant-numeric: tabular-nums;
  font-weight: var(--font-weight-extrabold);
}

.my-point-panel__grid p {
  color: var(--color-text-muted);
  font-size: 12px;
  font-weight: var(--font-weight-medium);
  line-height: 18px;
}

.my-point-panel__actions {
  display: flex;
  gap: var(--space-3);
}

.my-point-panel__actions button {
  min-height: var(--button-height-small);
  padding: 0 var(--space-4);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-bold);
  transition:
    border-color 160ms ease,
    background-color 160ms ease,
    color 160ms ease;
}

.my-point-panel__actions button:first-child {
  border-color: var(--color-primary);
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

.my-point-panel__actions button:hover {
  background: var(--color-surface-secondary);
}

.my-point-panel__actions button:first-child:hover {
  background: var(--color-primary-hover);
}

.my-dashboard-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(280px, 0.55fr);
  gap: 16px;
  padding: 0 32px 16px;
}

.my-dashboard-grid .my-card {
  margin: 0;
}

.my-card {
  display: grid;
  gap: 16px;
  margin: 0 32px 32px;
  padding: 24px;
}

.my-card--split {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.my-card--revenue {
  align-content: start;
}

.my-card--revenue .my-card__title > strong {
  color: var(--color-text-primary);
  font-size: 20px;
  font-variant-numeric: tabular-nums;
  font-weight: var(--font-weight-extrabold);
}

.my-revenue-chart {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  align-items: end;
  gap: 12px;
  min-height: 216px;
  padding-top: 8px;
}

.my-revenue-chart__item {
  display: grid;
  grid-template-rows: 20px 128px 18px 16px;
  gap: 6px;
  align-items: end;
  min-width: 0;
  text-align: center;
}

.my-revenue-chart__item span,
.my-revenue-chart__item small {
  overflow: hidden;
  color: var(--color-text-muted);
  font-size: 11px;
  font-weight: var(--font-weight-medium);
  line-height: 16px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.my-revenue-chart__item div {
  display: flex;
  align-items: end;
  justify-content: center;
  height: 128px;
  border-radius: var(--radius-control);
  background: var(--color-surface-secondary);
  overflow: hidden;
}

.my-revenue-chart__item i {
  display: block;
  width: 100%;
  min-height: 10px;
  border-radius: var(--radius-control) var(--radius-control) 3px 3px;
  background: var(--color-primary);
}

.my-revenue-chart__item b {
  color: var(--color-text-primary);
  font-size: 12px;
  font-weight: var(--font-weight-bold);
  line-height: 18px;
}

.my-card--todo {
  align-content: start;
}

.my-todo-row {
  display: grid;
  align-items: center;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  min-height: 48px;
  padding: 0;
  border: 0;
  border-bottom: 1px solid var(--color-border);
  background: transparent;
  color: var(--color-text-primary);
  text-align: left;
}

.my-todo-row:last-child {
  border-bottom: 0;
}

.my-todo-row span {
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: var(--font-weight-semibold);
}

.my-todo-row strong {
  color: var(--color-text-primary);
  font-size: 20px;
  font-variant-numeric: tabular-nums;
  font-weight: var(--font-weight-extrabold);
}

.my-status-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.my-status-grid div {
  display: grid;
  gap: 6px;
  min-height: 86px;
  padding: 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface-secondary);
}

.my-status-grid span {
  color: var(--color-text-secondary);
  font-size: 12px;
  font-weight: var(--font-weight-semibold);
}

.my-status-grid strong {
  color: var(--color-text-primary);
  font-size: 24px;
  font-variant-numeric: tabular-nums;
  font-weight: var(--font-weight-extrabold);
}

.my-card h2,
.my-card__title h2 {
  color: var(--color-text-primary);
  font-size: 16px;
  font-weight: var(--font-weight-extrabold);
  line-height: 24px;
}

.my-card__title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.my-row,
.my-text-row {
  display: grid;
  align-items: center;
  grid-template-columns: 84px minmax(0, 1fr) auto;
  gap: 16px;
  padding: 14px 0;
  border-top: 1px solid var(--color-border);
}

.my-text-row {
  grid-template-columns: minmax(0, 1fr) auto;
}

.my-product-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  padding-bottom: var(--space-1);
}

.my-product-tabs button,
.my-order-tabs button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  min-height: var(--button-height-small);
  padding: 0 var(--space-4);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-bold);
}

.my-product-tabs button:hover,
.my-product-tabs__item--active,
.my-order-tabs button:hover,
.my-order-tabs__item--active {
  border-color: var(--color-primary) !important;
  background: var(--color-primary-soft) !important;
  color: var(--color-primary) !important;
}

.my-product-tabs button span,
.my-order-tabs button span {
  color: inherit;
  font-size: 12px;
  line-height: 18px;
}

.my-order-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  padding-bottom: var(--space-1);
}

.my-product-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-4);
}

.my-product-card {
  display: grid;
  min-width: 0;
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
  box-shadow: 0 1px 3px rgb(23 26 31 / 8%);
}

.my-product-card__main {
  display: grid;
  width: 100%;
  min-width: 0;
  padding: 0;
  border: 0;
  background: transparent;
  color: inherit;
  text-align: left;
}

.my-product-card__main:hover strong {
  color: var(--color-primary);
}

.my-product-card__main img {
  display: block;
  width: 100%;
  aspect-ratio: 1 / 1;
  object-fit: cover;
}

.my-product-card__main span,
.my-product-card__main strong,
.my-product-card__main p {
  margin-right: var(--space-4);
  margin-left: var(--space-4);
}

.my-product-card__main span {
  justify-self: start;
  min-height: 24px;
  padding: 2px 10px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-badge);
  margin-top: var(--space-4);
  background: var(--color-surface-secondary);
  color: var(--color-text-secondary);
  font-size: 12px;
  font-weight: var(--font-weight-bold);
  line-height: 18px;
}

.my-product-card__main strong {
  overflow: hidden;
  margin-top: var(--space-2);
  color: var(--color-text-primary);
  font-size: 14px;
  font-weight: var(--font-weight-extrabold);
  line-height: 20px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.my-product-card__main p {
  margin-top: var(--space-2);
  color: var(--color-text-primary);
  font-size: 15px;
  font-weight: var(--font-weight-extrabold);
  line-height: 22px;
}

.my-product-empty {
  padding: var(--space-8);
  border: 1px dashed var(--color-border-strong);
  border-radius: var(--radius-control);
  background: var(--color-surface-secondary);
  color: var(--color-text-secondary);
  font-size: 14px;
  line-height: 22px;
  text-align: center;
}

.my-wish-card {
  align-content: start;
}

.my-wish-card__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  min-width: 0;
  padding: var(--space-3) var(--space-4) 0;
  color: var(--color-text-secondary);
  font-size: 12px;
  line-height: 18px;
}

.my-wish-card__meta span {
  overflow: hidden;
  min-width: 0;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.my-wish-card__remove {
  min-height: 36px;
  padding: 0 var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  margin: var(--space-3) var(--space-4) var(--space-4);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: var(--font-weight-bold);
  line-height: 20px;
  cursor: pointer;
}

.my-wish-card__remove:hover:not(:disabled) {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.my-wish-card__remove:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.my-wish-message {
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface-secondary);
  color: var(--color-text-secondary);
  font-size: 13px;
  line-height: 20px;
}

.my-social-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-4);
}

.my-social-card {
  display: grid;
  grid-template-columns: 56px minmax(0, 1fr);
  gap: var(--space-4);
  min-width: 0;
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
  box-shadow: 0 1px 3px rgb(23 26 31 / 8%);
}

.my-social-card__avatar {
  display: grid;
  place-items: center;
  width: 56px;
  height: 56px;
  overflow: hidden;
  border-radius: 50%;
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-size: 20px;
  font-weight: var(--font-weight-extrabold);
}

.my-social-card__avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.my-social-card__body {
  display: grid;
  gap: var(--space-2);
  min-width: 0;
}

.my-social-card__body strong {
  overflow: hidden;
  color: var(--color-text-primary);
  font-size: 15px;
  font-weight: var(--font-weight-extrabold);
  line-height: 22px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.my-social-card__body p {
  display: -webkit-box;
  overflow: hidden;
  color: var(--color-text-secondary);
  font-size: 13px;
  line-height: 20px;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.my-social-card__body dl {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
}

.my-social-card__body dl div {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
}

.my-social-card__body dt,
.my-social-card__body > span {
  color: var(--color-text-secondary);
  font-size: 12px;
  line-height: 18px;
}

.my-social-card__body dd {
  color: var(--color-text-primary);
  font-size: 12px;
  font-weight: var(--font-weight-bold);
  line-height: 18px;
}

.my-social-card > button {
  min-height: 36px;
  padding: 0 var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface-secondary);
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: var(--font-weight-bold);
  grid-column: 2;
  justify-self: start;
}

.my-business-status {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-5);
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface-secondary);
}

.my-business-status div {
  display: grid;
  gap: var(--space-2);
  min-width: 0;
}

.my-business-status span {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  justify-self: start;
  min-height: 24px;
  padding: 2px 10px;
  border-radius: var(--radius-badge);
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-size: 12px;
  font-weight: var(--font-weight-bold);
  line-height: 18px;
}

.my-business-status strong {
  color: var(--color-text-primary);
  font-size: 22px;
  font-weight: var(--font-weight-extrabold);
  line-height: 32px;
}

.my-business-status p,
.my-business-guide p {
  color: var(--color-text-secondary);
  font-size: 14px;
  line-height: 22px;
}

.my-business-status button {
  flex: 0 0 auto;
  min-height: 40px;
  padding: 0 var(--space-4);
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-control);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-size: 14px;
  font-weight: var(--font-weight-bold);
  line-height: 22px;
  cursor: pointer;
}

.my-business-status button:hover {
  background: var(--color-primary-hover);
}

.my-business-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-3);
}

.my-business-grid div {
  display: grid;
  gap: var(--space-1);
  min-width: 0;
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
}

.my-business-grid dt {
  color: var(--color-text-secondary);
  font-size: 12px;
  line-height: 18px;
}

.my-business-grid dd {
  overflow: hidden;
  color: var(--color-text-primary);
  font-size: 15px;
  font-weight: var(--font-weight-bold);
  line-height: 22px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.my-business-guide {
  display: grid;
  gap: var(--space-2);
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface-secondary);
}

.my-business-guide strong {
  color: var(--color-text-primary);
  font-size: 15px;
  font-weight: var(--font-weight-extrabold);
  line-height: 22px;
}

.my-order-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-4);
}

.my-order-card {
  display: block;
  min-width: 0;
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
  box-shadow: 0 1px 3px rgb(23 26 31 / 8%);
}

.my-order-card__main {
  display: grid;
  width: 100%;
  min-height: 100%;
  padding: 0;
  border: 0;
  background: transparent;
  color: inherit;
  cursor: pointer;
  grid-template-columns: 124px minmax(0, 1fr);
  text-align: left;
}

.my-order-card__main:hover h3 {
  color: var(--color-primary);
}

.my-order-card__main img {
  width: 124px;
  height: 100%;
  min-height: 168px;
  object-fit: cover;
}

.my-order-card__body {
  display: grid;
  align-content: start;
  gap: var(--space-3);
  min-width: 0;
  padding: var(--space-4);
}

.my-order-card__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.my-order-card__top span,
.my-order-card__top strong {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 24px;
  padding: 2px 10px;
  border-radius: var(--radius-badge);
  font-size: 12px;
  font-weight: var(--font-weight-bold);
  line-height: 18px;
}

.my-order-card__top span {
  background: var(--color-primary-soft);
  color: var(--color-primary);
}

.my-order-card__top strong {
  border: 1px solid var(--color-border);
  background: var(--color-surface-secondary);
  color: var(--color-text-secondary);
}

.my-order-card h3 {
  overflow: hidden;
  color: var(--color-text-primary);
  font-size: 15px;
  font-weight: var(--font-weight-extrabold);
  line-height: 22px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.my-order-card p {
  color: var(--color-text-secondary);
  font-size: 13px;
  line-height: 20px;
}

.my-order-card dl {
  display: grid;
  gap: var(--space-2);
}

.my-order-card dl div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}

.my-order-card dt {
  color: var(--color-text-secondary);
  font-size: 12px;
  line-height: 18px;
}

.my-order-card dd {
  overflow: hidden;
  color: var(--color-text-primary);
  font-size: 13px;
  font-weight: var(--font-weight-bold);
  line-height: 20px;
  text-align: right;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.my-order-empty {
  padding: var(--space-8);
  border: 1px dashed var(--color-border-strong);
  border-radius: var(--radius-control);
  background: var(--color-surface-secondary);
  color: var(--color-text-secondary);
  font-size: 14px;
  line-height: 22px;
  text-align: center;
}

.my-row img {
  width: 84px;
  height: 84px;
  border: 1px solid var(--color-border);
  object-fit: cover;
}

.my-row > span,
.my-text-row > span {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 26px;
  padding: 0 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-badge);
  background: var(--color-surface-secondary);
  color: var(--color-text-primary);
  font-size: 12px;
  font-weight: var(--font-weight-bold);
}

.my-profile-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.my-profile-grid div {
  padding: 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface-secondary);
}

.my-profile-grid dt {
  color: var(--color-text-secondary);
  font-size: 12px;
  line-height: 18px;
}

.my-profile-grid dd {
  margin-top: 6px;
  color: var(--color-text-primary);
  font-size: 14px;
  font-weight: var(--font-weight-bold);
  line-height: 22px;
}

.my-profile-form {
  display: grid;
  gap: 18px;
}

.my-profile-form__message {
  padding: 12px 14px;
  border-radius: var(--radius-control);
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-size: 13px;
  font-weight: var(--font-weight-semibold);
  line-height: 20px;
}

.my-profile-form__message--error {
  background: var(--color-error-soft);
  color: var(--color-error);
}

.my-profile-photo {
  position: relative;
  display: grid;
  grid-template-columns: 96px minmax(0, 1fr);
  gap: var(--space-4);
  align-items: center;
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface-secondary);
}

.my-profile-photo__preview {
  display: grid;
  place-items: center;
  width: 88px;
  height: 88px;
  border: 1px solid var(--color-border);
  border-radius: 50%;
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-size: 30px;
  font-weight: var(--font-weight-extrabold);
  overflow: hidden;
}

.my-profile-photo__preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.my-profile-photo__body {
  min-width: 0;
}

.my-profile-photo strong {
  display: block;
  color: var(--color-text-primary);
  font-size: 15px;
  font-weight: var(--font-weight-extrabold);
  line-height: 24px;
}

.my-profile-photo p {
  margin-top: var(--space-1);
  color: var(--color-text-secondary);
  font-size: 13px;
  line-height: 20px;
}

.my-profile-photo__file {
  color: var(--color-primary) !important;
  font-weight: var(--font-weight-semibold);
}

.my-profile-photo__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: var(--space-3);
}

.my-profile-photo__actions button {
  min-height: var(--button-height-small);
  padding: 0 var(--space-4);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-bold);
}

.my-profile-photo__actions button:first-child {
  border-color: var(--color-primary);
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

.my-profile-photo__actions button:hover {
  background: var(--color-surface);
}

.my-profile-photo__actions button:first-child:hover {
  background: var(--color-primary-hover);
}

.my-profile-photo__input {
  display: none;
}

.my-tryon-photo {
  position: relative;
  display: grid;
  grid-template-columns: minmax(160px, 180px) minmax(0, 1fr);
  gap: var(--space-5);
  align-items: start;
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface-secondary);
}

.my-tryon-photo__preview {
  display: grid;
  place-items: center;
  width: 100%;
  max-width: 180px;
  height: 220px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-size: 42px;
  font-weight: var(--font-weight-extrabold);
  overflow: hidden;
}

.my-tryon-photo__preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.my-tryon-photo__body {
  min-width: 0;
  padding-top: 2px;
}

.my-tryon-photo strong {
  display: block;
  color: var(--color-text-primary);
  font-size: 15px;
  font-weight: var(--font-weight-extrabold);
  line-height: 24px;
}

.my-tryon-photo p {
  margin-top: var(--space-1);
  color: var(--color-text-secondary);
  font-size: 13px;
  line-height: 20px;
}

.my-tryon-photo__file {
  color: var(--color-primary) !important;
  font-weight: var(--font-weight-semibold);
}

.my-tryon-photo__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: var(--space-3);
}

.my-tryon-photo__actions button {
  min-height: var(--button-height-small);
  padding: 0 var(--space-4);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-bold);
}

.my-tryon-photo__actions button:first-child {
  border-color: var(--color-primary);
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

.my-tryon-photo__actions button:hover {
  background: var(--color-surface);
}

.my-tryon-photo__actions button:first-child:hover {
  background: var(--color-primary-hover);
}

.my-tryon-photo__input {
  display: none;
}

.my-profile-form__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.my-profile-form__grid label,
.my-profile-form__readonly {
  display: grid;
  gap: 8px;
  min-width: 0;
}

.my-profile-form__grid label span,
.my-profile-form__readonly span {
  color: var(--color-text-secondary);
  font-size: 12px;
  font-weight: var(--font-weight-semibold);
  line-height: 18px;
}

.my-profile-form__grid input,
.my-profile-form__grid select {
  width: 100%;
  min-height: var(--button-height-standard);
  padding: 0 14px;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-size: 14px;
  font-weight: var(--font-weight-semibold);
}

.my-profile-form__grid input:disabled {
  background: var(--color-surface-secondary);
  color: var(--color-text-muted);
}

.my-profile-form__grid input:focus,
.my-profile-form__grid select:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
  outline: none;
}

.my-profile-form__wide,
.my-profile-form__readonly {
  grid-column: 1 / -1;
}

.my-profile-form__readonly {
  padding: 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface-secondary);
}

.my-profile-form__readonly strong {
  color: var(--color-text-primary);
  font-size: 14px;
  font-weight: var(--font-weight-bold);
}

.my-interest-editor {
  display: grid;
  gap: var(--space-5);
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface-secondary);
}

.my-interest-editor__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
}

.my-interest-editor__header h3 {
  color: var(--color-text-primary);
  font-size: 16px;
  font-weight: var(--font-weight-extrabold);
  line-height: 24px;
}

.my-interest-editor__header p {
  margin-top: var(--space-1);
  color: var(--color-text-secondary);
  font-size: 13px;
  line-height: 20px;
}

.my-interest-editor__header > span {
  flex: 0 0 auto;
  min-height: 28px;
  padding: 4px 10px;
  border-radius: var(--radius-badge);
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-size: 12px;
  font-weight: var(--font-weight-bold);
  line-height: 20px;
}

.my-interest-editor__message,
.my-interest-editor__empty {
  color: var(--color-text-secondary);
  font-size: 13px;
  line-height: 20px;
}

.my-interest-editor__group,
.my-interest-editor__search {
  display: grid;
  gap: var(--space-3);
}

.my-interest-editor__search span,
.my-interest-editor__label {
  color: var(--color-text-secondary);
  font-size: 12px;
  font-weight: var(--font-weight-semibold);
  line-height: 18px;
}

.my-interest-editor__search input {
  width: 100%;
  min-height: var(--button-height-standard);
  padding: 0 14px;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-size: 14px;
}

.my-interest-editor__search input:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
  outline: none;
}

.my-interest-editor__chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.my-interest-editor__chips button {
  min-height: var(--button-height-small);
  padding: 0 var(--space-4);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-bold);
}

.my-interest-editor__chips button:hover,
.my-interest-editor__chip--selected {
  border-color: var(--color-primary) !important;
  background: var(--color-primary-soft) !important;
  color: var(--color-primary) !important;
}

.my-interest-editor__categories {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-2);
}

.my-interest-editor__category {
  display: flex;
  align-items: center;
  min-height: var(--button-height-standard);
  padding: 0 var(--space-4);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  cursor: pointer;
  font-size: var(--font-size-button-small);
  font-weight: var(--font-weight-bold);
}

.my-interest-editor__category input {
  width: 16px;
  height: 16px;
  margin: 0 var(--space-2) 0 0;
  accent-color: var(--color-primary);
}

.my-interest-editor__category:hover,
.my-interest-editor__category--selected {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
  color: var(--color-primary);
}

.my-card__title button:disabled {
  cursor: wait;
  opacity: 0.65;
}

.my-empty,
.my-state {
  display: grid;
  justify-items: center;
  gap: 12px;
  padding: 48px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  text-align: center;
}

.my-state {
  grid-column: 1 / -1;
}

@media (max-width: 980px) {
  .my-shell {
    grid-template-columns: 1fr;
  }

  .my-sidebar {
    border-right: 0;
    border-bottom: 1px solid var(--color-border);
  }

  .my-sidebar__nav {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .my-card--split,
  .my-dashboard,
  .my-dashboard-grid,
  .my-dashboard--home,
  .my-business-grid,
  .my-point-panel__grid,
  .my-profile-form__grid,
  .my-profile-grid {
    grid-template-columns: 1fr;
  }

  .my-profile-hero {
    grid-template-columns: 88px minmax(0, 1fr);
  }

  .my-profile-hero__edit {
    grid-column: 2;
    justify-self: start;
  }

  .my-product-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .my-social-grid {
    grid-template-columns: 1fr;
  }

  .my-order-grid {
    grid-template-columns: 1fr;
  }

  .my-interest-editor__categories {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .my-dashboard,
  .my-dashboard-grid {
    padding-right: 16px;
    padding-left: 16px;
  }

  .my-card {
    margin-right: 16px;
    margin-left: 16px;
    padding: 18px;
  }

  .my-profile-hero {
    grid-template-columns: 1fr;
    margin: 16px;
    padding: 22px;
  }

  .my-profile-hero__edit {
    grid-column: auto;
  }

  .my-profile-hero__stats {
    gap: 18px;
  }

  .my-product-grid {
    grid-template-columns: 1fr;
  }

  .my-social-card {
    grid-template-columns: 48px minmax(0, 1fr);
  }

  .my-social-card__avatar {
    width: 48px;
    height: 48px;
  }

  .my-business-status {
    flex-direction: column;
  }

  .my-order-card__main {
    grid-template-columns: 96px minmax(0, 1fr);
  }

  .my-order-card__main img {
    width: 96px;
    min-height: 154px;
  }

  .my-order-card__top {
    align-items: flex-start;
    flex-direction: column;
  }

  .my-interest-editor__header {
    flex-direction: column;
  }

  .my-interest-editor__categories {
    grid-template-columns: 1fr;
  }

  .my-profile-photo {
    grid-template-columns: 1fr;
    justify-items: start;
  }

  .my-tryon-photo {
    grid-template-columns: 1fr;
  }

  .my-tryon-photo__preview {
    width: 100%;
    max-width: 220px;
    height: 260px;
  }

  .my-point-panel__actions {
    flex-direction: column;
  }

  .my-revenue-chart {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    row-gap: 18px;
  }

  .my-status-grid {
    grid-template-columns: 1fr;
  }

  .my-content__header {
    align-items: stretch;
    flex-direction: column;
  }

  .my-content__actions {
    flex-direction: column;
  }

  .my-row {
    grid-template-columns: 64px minmax(0, 1fr);
  }

  .my-row img {
    width: 64px;
    height: 64px;
  }

  .my-row > span {
    grid-column: 1 / -1;
    justify-self: start;
  }
}
</style>
