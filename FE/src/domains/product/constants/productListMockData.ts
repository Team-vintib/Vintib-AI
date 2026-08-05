import type {
  ProductFilterOption,
  ProductListItem,
  ProductSaleTypeTab,
  ProductSortItem,
} from '../types/productList.types'

export const PRODUCT_CATEGORY_MOCK_DATA = [
  { id: 1, parentId: null, name: '아우터', depth: 2 },
  { id: 2, parentId: null, name: '상의', depth: 2 },
  { id: 3, parentId: null, name: '하의', depth: 2 },
  { id: 4, parentId: null, name: '원피스 및 점프슈트', depth: 2 },
  { id: 5, parentId: null, name: '신발', depth: 2 },
  { id: 6, parentId: null, name: '액세서리', depth: 2 },
]

export const PRODUCT_CONDITION_OPTIONS: ProductFilterOption[] = [
  { id: 'S', label: 'S급 (최상)' },
  { id: 'A', label: 'A급 (상)' },
  { id: 'B', label: 'B급 (중)' },
  { id: 'C', label: 'C급 (하)' },
]

export const PRODUCT_SALE_TYPE_TABS: ProductSaleTypeTab[] = [
  { id: 'ALL', label: '전체' },
  { id: 'DIRECT', label: '즉시 구매' },
  { id: 'AUCTION', label: '경매 예정' },
]

export const PRODUCT_SORT_OPTIONS: ProductSortItem[] = [
  { id: 'LATEST', label: '최신순' },
  { id: 'PRICE_ASC', label: '가격 낮은순' },
  { id: 'PRICE_DESC', label: '가격 높은순' },
]

// VITE_PRODUCT_API_ENABLED=false일 때만 쓰이는 mock 상품 목록입니다. 실제 API 연동 후 표본
// 데이터는 비워 뒀습니다 — 필요하면 다시 채워 넣으세요.
export const PRODUCT_LIST_MOCK_DATA: ProductListItem[] = []
