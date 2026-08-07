// AI 품질 검수(`worker/models/sam3/prompts.py`의 SECTION_LABELS_KO)와 정확히 같은 한글
// 라벨이다 — 새 라벨을 만들지 않고 AI 쪽 표기를 그대로 옮긴다. 부위가 늘어나면(예: 원피스
// 지원 추가) 이 상수도 함께 갱신해야 한다.
export const AI_SECTION_LABELS: Record<string, string> = {
  SHOULDER_LEFT: '왼쪽 어깨',
  COLLAR: '목깃',
  SHOULDER_RIGHT: '오른쪽 어깨',
  SLEEVE_LEFT: '왼쪽 소매',
  CHEST_CENTER: '가슴 중앙',
  SLEEVE_RIGHT: '오른쪽 소매',
  HEM_LEFT: '왼쪽 밑단',
  HEM_CENTER: '밑단 중앙',
  HEM_RIGHT: '오른쪽 밑단',
  WAIST_LEFT: '왼쪽 허리',
  WAIST_CENTER: '허리 중앙',
  WAIST_RIGHT: '오른쪽 허리',
  THIGH_LEFT: '왼쪽 허벅지',
  CROTCH: '사타구니',
  THIGH_RIGHT: '오른쪽 허벅지',
  SHIN_CENTER: '정강이 중앙',
}

// 매핑되는 라벨이 없으면(신규 부위 추가 등 이 상수가 안 따라간 경우) 원본 코드를 그대로 보여준다.
export const mapAiSectionToLabel = (section: string): string => AI_SECTION_LABELS[section] ?? section
