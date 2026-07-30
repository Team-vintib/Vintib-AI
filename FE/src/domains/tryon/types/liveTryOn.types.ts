export const LIVE_TRY_ON_MOCK_SCENARIOS = ['ready', 'empty', 'error'] as const

export type LiveTryOnMockScenario = (typeof LIVE_TRY_ON_MOCK_SCENARIOS)[number]

export type LiveTryOnPanelState =
  | 'EMPTY'
  | 'READY'
  | 'GENERATING'
  | 'RESULT'
  | 'ERROR'

export interface LiveTryOnMockResult {
  imageUrl: string
  fitTitle: string
  fitDescription: string
}
