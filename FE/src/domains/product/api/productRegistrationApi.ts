import type {
  ProductRegistrationDraft,
  ProductRegistrationSubmitResult,
} from '@/domains/product/types/productRegistration.types'
import { submitProduct, type CategoryDto } from '@/domains/product/api/productApi'

export const submitProductRegistrationDraft = async (
  draft: ProductRegistrationDraft,
  options: {
    categories?: CategoryDto[]
  } = {},
): Promise<ProductRegistrationSubmitResult> => {
  if (!draft.name.trim()) {
    throw new Error('상품명이 없습니다.')
  }

  return submitProduct(draft, options)
}
