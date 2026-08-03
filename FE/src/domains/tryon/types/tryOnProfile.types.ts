export type TryOnProfileAvailability = 'READY' | 'NEEDS_MEASUREMENTS' | 'MISSING_PHOTO'

export type TryOnBodyFieldId = 'heightCm' | 'weightKg' | 'chest' | 'waist' | 'hip'

export interface TryOnProfile {
  id: number | null
  bodyPhotoUrl: string | null
  heightCm: number | null
  weightKg: number | null
  chest: number | null
  waist: number | null
  hip: number | null
  updatedAt: string | null
}

export interface SaveTryOnProfileRequest {
  bodyPhoto?: File
  removeBodyPhoto?: boolean
  heightCm?: string
  weightKg?: string
  chest?: string
  waist?: string
  hip?: string
}

export interface TryOnBodyFieldOption {
  id: TryOnBodyFieldId
  label: string
  unit?: string
  placeholder: string
}
