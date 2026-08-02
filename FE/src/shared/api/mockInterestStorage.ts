const STORAGE_KEY = 'vidtib:mock-interests'
const FALLBACK_USER_KEY = 'current'

export interface InterestBrand {
  id: number
  name: string
  nameEn: string | null
}

export interface InterestCategory {
  id: number
  parentId: number | null
  name: string
  depth: number
}

export interface UserInterests {
  brands: InterestBrand[]
  categories: InterestCategory[]
}

type UserInterestIdMap = Record<string, { brandIds: number[]; categoryIds: number[] }>

export const MOCK_INTEREST_BRANDS: InterestBrand[] = [
  { id: 1, name: '리바이스', nameEn: "Levi's" },
  { id: 2, name: '나이키', nameEn: 'Nike' },
  { id: 3, name: '폴로 랄프 로렌', nameEn: 'Polo Ralph Lauren' },
  { id: 4, name: '칼하트', nameEn: 'Carhartt' },
  { id: 5, name: '아디다스', nameEn: 'Adidas' },
  { id: 6, name: '유니클로', nameEn: 'Uniqlo' },
]

export const MOCK_INTEREST_CATEGORIES: InterestCategory[] = [
  { id: 1, parentId: null, name: '아우터', depth: 1 },
  { id: 2, parentId: null, name: '상의', depth: 1 },
  { id: 3, parentId: null, name: '하의', depth: 1 },
  { id: 4, parentId: null, name: '원피스', depth: 1 },
  { id: 5, parentId: null, name: '신발', depth: 1 },
  { id: 6, parentId: null, name: '액세서리', depth: 1 },
]

const getUserKey = (userId?: number | null) => (userId ? String(userId) : FALLBACK_USER_KEY)

const readInterestIdMap = (): UserInterestIdMap => {
  try {
    const storedValue = window.localStorage.getItem(STORAGE_KEY)

    if (!storedValue) {
      return {}
    }

    return JSON.parse(storedValue) as UserInterestIdMap
  } catch {
    return {}
  }
}

const writeInterestIdMap = (interestIdMap: UserInterestIdMap) => {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(interestIdMap))
}

const getSelectedIds = (userId?: number | null) => {
  const interestIdMap = readInterestIdMap()

  return {
    ...interestIdMap[FALLBACK_USER_KEY],
    ...interestIdMap[getUserKey(userId)],
    brandIds:
      interestIdMap[getUserKey(userId)]?.brandIds ??
      interestIdMap[FALLBACK_USER_KEY]?.brandIds ??
      [],
    categoryIds:
      interestIdMap[getUserKey(userId)]?.categoryIds ??
      interestIdMap[FALLBACK_USER_KEY]?.categoryIds ??
      [],
  }
}

export const getMockInterestOptions = () => ({
  brands: MOCK_INTEREST_BRANDS,
  categories: MOCK_INTEREST_CATEGORIES,
})

export const readMockUserInterests = (userId?: number | null): UserInterests => {
  const selectedIds = getSelectedIds(userId)

  return {
    brands: MOCK_INTEREST_BRANDS.filter((brand) => selectedIds.brandIds.includes(brand.id)),
    categories: MOCK_INTEREST_CATEGORIES.filter((category) =>
      selectedIds.categoryIds.includes(category.id),
    ),
  }
}

export const saveMockUserInterests = (
  userId: number | null | undefined,
  brandIds: number[],
  categoryIds: number[],
): UserInterests => {
  const interestIdMap = readInterestIdMap()

  interestIdMap[getUserKey(userId)] = {
    brandIds: Array.from(new Set(brandIds)),
    categoryIds: Array.from(new Set(categoryIds)),
  }
  writeInterestIdMap(interestIdMap)

  return readMockUserInterests(userId)
}
