import type {
  ProductRegistrationDraft,
  ProductRegistrationSubmitResult,
} from '@/domains/product/types/productRegistration.types'

const waitForMockResponse = () =>
  new Promise<void>((resolve) => {
    window.setTimeout(resolve, 360)
  })

export const submitProductRegistrationDraft = async (
  draft: ProductRegistrationDraft,
): Promise<ProductRegistrationSubmitResult> => {
  await waitForMockResponse()

  if (!draft.name.trim()) {
    throw new Error('상품 등록 mock 요청에 상품명이 없습니다.')
  }

  return {
    productId: `preview-${Date.now()}`,
    submittedAt: new Date().toISOString(),
  }
}
