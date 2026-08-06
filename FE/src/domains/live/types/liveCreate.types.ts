export type LiveCreateMode = 'IMMEDIATE' | 'SCHEDULED'

export type LiveCreateStepId = 'method' | 'info' | 'products' | 'schedule' | 'device' | 'complete'

export type LiveDeviceTestStatus = 'idle' | 'testing' | 'success' | 'failed'

export interface LiveCreateStep {
  id: LiveCreateStepId
  label: string
  description: string
}

export interface LiveCreateMethodOption {
  id: LiveCreateMode
  title: string
  description: string
}

export interface LiveCreateProduct {
  id: number
  name: string
  brand: string
  category: string
  condition: string
  price: number
  isAuctionScheduled: boolean
  thumbnailUrl: string
}

export interface LiveDeviceState {
  camera: LiveDeviceTestStatus
  microphone: LiveDeviceTestStatus
}

export interface LiveCreateFormState {
  mode: LiveCreateMode | ''
  title: string
  description: string
  mainBrand: string
  productKeyword: string
  selectedProductIds: number[]
  scheduledDate: string
  scheduledTime: string
}
