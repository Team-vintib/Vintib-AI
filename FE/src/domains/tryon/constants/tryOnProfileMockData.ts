import type { TryOnBodyFieldOption, TryOnProfile } from '@/domains/tryon/types/tryOnProfile.types'

export const TRYON_BODY_FIELD_OPTIONS: TryOnBodyFieldOption[] = [
  { id: 'heightCm', label: '키', unit: 'cm', placeholder: '예: 170' },
  { id: 'weightKg', label: '몸무게', unit: 'kg', placeholder: '예: 60' },
  { id: 'chest', label: '가슴', placeholder: '선택 입력' },
  { id: 'waist', label: '허리', placeholder: '선택 입력' },
  { id: 'hip', label: '엉덩이', placeholder: '선택 입력' },
]

export const EMPTY_TRYON_PROFILE: TryOnProfile = {
  id: null,
  bodyPhotoUrl: null,
  heightCm: null,
  weightKg: null,
  chest: null,
  waist: null,
  hip: null,
  updatedAt: null,
}

export const TRYON_PROFILE_STATUS_LABELS = {
  READY: '사용 가능',
  NEEDS_MEASUREMENTS: '정보 보강 권장',
  MISSING_PHOTO: '사용 불가',
} as const
