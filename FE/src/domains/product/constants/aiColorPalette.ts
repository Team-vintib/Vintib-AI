import { PRODUCT_REGISTRATION_COLOR_OPTIONS } from '@/domains/product/constants/productRegistrationOptions'

// AI 색상 분류기(`worker/models/product_classifier/color.py`)의 팔레트(13색 + MIXED)는
// 등록 폼의 14개 색상 옵션과 1:1로 정확히 매핑된다(값을 소문자로 낮추기만 하면 id가 같다) —
// 실제로 요청 응답이 오면(docs/requests/AI/006-registration-category-color-autofill.md) 이
// 매핑을 그대로 쓰면 된다. 팔레트가 바뀌면(색이 추가/삭제되면) 이 상수도 함께 갱신해야 한다.
export const AI_COLOR_PALETTE_KEYS = [
  'BLACK',
  'WHITE',
  'GRAY',
  'RED',
  'ORANGE',
  'PINK',
  'YELLOW',
  'BROWN',
  'GREEN',
  'BLUE',
  'PURPLE',
  'BEIGE',
  'NAVY',
  'MIXED',
] as const

export type AiColorPaletteKey = (typeof AI_COLOR_PALETTE_KEYS)[number]

const REGISTRATION_COLOR_OPTION_IDS = new Set(
  PRODUCT_REGISTRATION_COLOR_OPTIONS.map((option) => option.id),
)

// AI가 준 팔레트 코드(예: "BLACK")를 등록 폼 색상 옵션 id(예: "black")로 변환한다.
// 매핑되는 옵션이 없으면(팔레트가 늘어났는데 이 상수가 안 따라간 경우) null을 반환한다.
export const mapAiColorKeyToOptionId = (colorKey: string): string | null => {
  const optionId = colorKey.toLowerCase()

  return REGISTRATION_COLOR_OPTION_IDS.has(optionId) ? optionId : null
}
