// AI 시착 결과(TRYON-005). BE 응답 `TryOnResultResponse` = { id, productId, imageUrl, createdAt }.
export interface TryOnResult {
  id: number
  productId: number
  imageUrl: string
  // 오프셋 없는 KST 벽시계 문자열(016 규약). Z/toISOString 왕복 금지.
  createdAt: string
  // ⚠️ BE 확인 필요: 결과 응답에 카테고리가 아직 없다(현재 mock 전용).
  // 저장 결과를 상의/하의 등으로 나눠 보기 위해 필요 → docs/requests/BE/020.
  category: string | null
}

// 결과 갤러리 카테고리 탭(상품 대분류 수준).
export const TRYON_RESULT_CATEGORIES = [
  '상의',
  '하의',
  '아우터',
  '원피스',
  '신발',
  '가방',
  '액세서리',
] as const

export type TryOnResultCategory = (typeof TRYON_RESULT_CATEGORIES)[number]
