// AI 시착 생성은 비동기 job이라 즉시 완료되지 않는다 — BE가 job을 접수하면 PENDING으로
// 시작해서, 조회 시점에 AI 쪽 상태를 다시 확인해 SUCCESS/FAILED로 바뀐다
// (docs/requests/BE/040-tryon-job-contract.md).
export type TryOnGenerationStatus = 'PENDING' | 'PROCESSING' | 'SUCCESS' | 'FAILED'

// AI 시착 결과(TRYON-005). BE 응답 `TryOnResultResponse` =
// { id, productId, status, imageUrl, fitTitle, fitDescription, createdAt }.
export interface TryOnResult {
  id: number
  productId: number
  // mock 데이터 호환을 위해 선택 필드로 둔다 — 값이 없으면 이미 완료된(mock) 결과로 간주.
  status?: TryOnGenerationStatus
  // PENDING/PROCESSING이면 아직 없다.
  imageUrl: string | null
  // 오프셋 없는 KST 벽시계 문자열(016 규약). Z/toISOString 왕복 금지.
  createdAt: string
  // ⚠️ BE 확인 필요: 결과 응답에 카테고리가 아직 없다(현재 mock 전용).
  // 저장 결과를 상의/하의 등으로 나눠 보기 위해 필요 → docs/requests/BE/020.
  category: string | null
  // "한 줄 핏 예상" — 회원 신체·상품 실측이 부족하면 null.
  fitTitle?: string | null
  fitDescription?: string | null
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
