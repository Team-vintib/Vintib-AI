export type ProductSaleType = 'DIRECT' | 'AUCTION'

export type ProductSortOption = 'LATEST' | 'PRICE_ASC' | 'PRICE_DESC'

export type ProductConditionGrade = 'S' | 'A' | 'B' | 'C'

export interface ProductListItem {
  id: number
  brand: string
  name: string
  price: number
  conditionGrade: ProductConditionGrade
  saleType: ProductSaleType
  imageUrl: string
  imageAlt: string
  isLiked: boolean
}

export interface ProductFilterOption {
  id: string
  label: string
}

export interface ProductSaleTypeTab {
  id: 'ALL' | ProductSaleType
  label: string
}

export interface ProductSortItem {
  id: ProductSortOption
  label: string
}
