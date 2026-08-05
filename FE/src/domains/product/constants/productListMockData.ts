import denimJacketImage from '@/assets/images/products/product-denim-jacket.webp'
import knitImage from '@/assets/images/products/product-knit.webp'
import leatherBagImage from '@/assets/images/products/product-leather-bag.webp'
import sneakersImage from '@/assets/images/products/product-sneakers.webp'
import trenchCoatImage from '@/assets/images/products/product-trench-coat.webp'
import watchImage from '@/assets/images/products/product-watch.webp'

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

// PROD-008 껍데기 화면 확인용 임시 데이터입니다. 실제 API 연동 후 제거합니다.
export const PRODUCT_LIST_MOCK_DATA: ProductListItem[] = [
  {
    id: 1,
    brand: "Levi's",
    name: "Levi's 빈티지 데님 재킷",
    price: 45000,
    conditionGrade: 'S',
    saleType: 'DIRECT',
    categoryId: 1,
    categoryName: '아우터',
    imageUrl: denimJacketImage,
    imageAlt: '푸른색 빈티지 데님 재킷',
    isLiked: false,
  },
  {
    id: 2,
    brand: 'Ralph Lauren',
    name: 'Polo Ralph Lauren 빈티지 니트',
    price: 38000,
    conditionGrade: 'A',
    saleType: 'DIRECT',
    categoryId: 2,
    categoryName: '상의',
    imageUrl: knitImage,
    imageAlt: '아이보리색 빈티지 니트',
    isLiked: true,
  },
  {
    id: 3,
    brand: 'Burberry',
    name: 'Burberry 빈티지 트렌치코트',
    price: 450000,
    conditionGrade: 'A',
    saleType: 'AUCTION',
    categoryId: 1,
    categoryName: '아우터',
    imageUrl: trenchCoatImage,
    imageAlt: '베이지색 빈티지 트렌치코트',
    isLiked: false,
  },
  {
    id: 4,
    brand: 'Omega',
    name: 'Omega Seamaster 빈티지 시계',
    price: 320000,
    conditionGrade: 'B',
    saleType: 'DIRECT',
    categoryId: 6,
    categoryName: '액세서리',
    imageUrl: watchImage,
    imageAlt: '가죽 스트랩 빈티지 손목시계',
    isLiked: false,
  },
  {
    id: 5,
    brand: 'Gucci',
    name: 'Gucci 클래식 레더 토트백',
    price: 280000,
    conditionGrade: 'A',
    saleType: 'AUCTION',
    categoryId: 6,
    categoryName: '액세서리',
    imageUrl: leatherBagImage,
    imageAlt: '브라운색 클래식 레더 토트백',
    isLiked: true,
  },
  {
    id: 6,
    brand: 'New Balance',
    name: 'New Balance 990 빈티지 스니커즈',
    price: 87000,
    conditionGrade: 'B',
    saleType: 'DIRECT',
    categoryId: 5,
    categoryName: '신발',
    imageUrl: sneakersImage,
    imageAlt: '회색 빈티지 러닝 스니커즈',
    isLiked: false,
  },
]
