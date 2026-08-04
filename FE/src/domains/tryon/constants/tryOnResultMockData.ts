import type { TryOnResult } from '@/domains/tryon/types/tryOnResult.types'

// ⚠️ Mock 전용 · BE/AI 확인 필요
// AI 시착 결과 저장(POST /users/{id}/tryons) + AI 합성이 미구현이라 실데이터가 아직 없다.
// 결과 조회/삭제 API(GET·DELETE)는 구현돼 있으므로, VITE_TRYON_API_ENABLED가 켜지면 실 API를 쓴다.
// 로컬 확인용으로만 아래 mock을 사용하고, 실데이터가 쌓이면 이 파일은 제거한다.

// 합성 결과 이미지 대체용 placeholder(사람 실루엣 + 라벨).
const placeholder = (bg: string, label: string) =>
  `data:image/svg+xml;utf8,${encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" width="360" height="480"><rect width="360" height="480" fill="${bg}"/><circle cx="180" cy="150" r="54" fill="#ffffff" opacity="0.55"/><rect x="112" y="214" width="136" height="210" rx="40" fill="#ffffff" opacity="0.55"/><text x="180" y="454" font-size="22" text-anchor="middle" fill="#3f3a34">${label}</text></svg>`,
  )}`

export const TRYON_RESULT_MOCK_DATA: TryOnResult[] = [
  { id: 101, productId: 1, imageUrl: placeholder('#d8cbb8', '데님 자켓 시착'), createdAt: '2026-08-03T14:20:00', category: '아우터' },
  { id: 102, productId: 2, imageUrl: placeholder('#c9d3c0', '니트 상의 시착'), createdAt: '2026-08-02T18:05:00', category: '상의' },
  { id: 103, productId: 3, imageUrl: placeholder('#cdbfd0', '슬랙스 시착'), createdAt: '2026-08-02T11:40:00', category: '하의' },
  { id: 104, productId: 4, imageUrl: placeholder('#bcccd6', '원피스 시착'), createdAt: '2026-08-01T09:15:00', category: '원피스' },
  { id: 105, productId: 5, imageUrl: placeholder('#d6c6bc', '셔츠 시착'), createdAt: '2026-07-31T20:30:00', category: '상의' },
  { id: 106, productId: 6, imageUrl: placeholder('#c7cdb9', '스니커즈 시착'), createdAt: '2026-07-30T16:50:00', category: '신발' },
]

// 입어보기(mock) 결과 이미지 — 실제 합성 전까지 선택 상품 이미지를 결과 대체로 쓴다.
export const buildMockTryOnResultImage = (label: string) => placeholder('#d3c7b6', label)
