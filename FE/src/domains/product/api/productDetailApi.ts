import { PRODUCT_DETAIL_MOCK_DATA } from '@/domains/product/constants/productDetailMockData'
import type { ProductDetailViewData } from '@/domains/product/types/productDetail.types'

export const getProductDetailViewData = async (
  productId: number,
): Promise<ProductDetailViewData> => {
  // 최신 Swagger의 GET /api/products/{id}는 기본 정보만 반환합니다.
  // 이미지·연결 라이브·찜·AI 품질 분석 계약이 합쳐지면 이 함수 안에서 응답을 ViewData로 매핑합니다.
  return {
    ...PRODUCT_DETAIL_MOCK_DATA,
    id: productId,
  }
}
