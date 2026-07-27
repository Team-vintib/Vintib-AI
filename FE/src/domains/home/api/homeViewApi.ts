import { homeMockData } from '@/domains/home/constants/homeMockData'
import type { HomeViewData } from '@/domains/home/types/homeView.types'

export const getHomeViewData = async (): Promise<HomeViewData> => {
  // 실제 HOME API 계약이 확정되면 이 함수 내부를 HTTP 호출과 adapter로 교체합니다.
  return homeMockData
}
