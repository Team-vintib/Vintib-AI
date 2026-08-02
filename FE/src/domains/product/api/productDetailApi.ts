import { getProductDetail } from '@/domains/product/api/productApi'

import type {
  ProductDetailMockScenario,
  ProductDetailViewData,
} from '@/domains/product/types/productDetail.types'

export class ProductDetailNotFoundError extends Error {
  constructor() {
    super('상품을 찾을 수 없습니다.')
    this.name = 'ProductDetailNotFoundError'
  }
}

export const getProductDetailViewData = async (
  productId: number,
  _scenario: ProductDetailMockScenario = 'default',
): Promise<ProductDetailViewData> => getProductDetail(productId)
