import denimJacketImage from '@/assets/images/products/product-denim-jacket.webp'
import leatherBagImage from '@/assets/images/products/product-leather-bag.webp'
import sneakersImage from '@/assets/images/products/product-sneakers.webp'
import trenchCoatImage from '@/assets/images/products/product-trench-coat.webp'

import type {
  LiveCreateMethodOption,
  LiveCreateProduct,
  LiveCreateStep,
} from '@/domains/live/types/liveCreate.types'

export const LIVE_CREATE_METHOD_OPTIONS: LiveCreateMethodOption[] = [
  {
    id: 'IMMEDIATE',
    title: '즉시 시작',
    description: '장비 테스트를 마치면 별도 예약 없이 바로 라이브를 시작합니다.',
  },
  {
    id: 'SCHEDULED',
    title: '예약 시작',
    description: '방송 날짜와 시간을 정해 라이브를 미리 예약합니다.',
  },
]

export const LIVE_CREATE_BASE_STEPS: LiveCreateStep[] = [
  {
    id: 'method',
    label: '라이브 유형',
    description: '즉시 시작 또는 예약 시작을 선택합니다.',
  },
  {
    id: 'info',
    label: '방송 정보',
    description: '시청자에게 보일 방송 정보를 입력합니다.',
  },
  {
    id: 'products',
    label: '판매 상품',
    description: '라이브에서 소개할 상품을 선택합니다.',
  },
]

export const LIVE_CREATE_SCHEDULE_STEP: LiveCreateStep = {
  id: 'schedule',
  label: '일정 설정',
  description: '예약 방송 날짜와 시작 시간을 입력합니다.',
}

export const LIVE_CREATE_DEVICE_STEP: LiveCreateStep = {
  id: 'device',
  label: '장비 확인',
  description: '카메라와 마이크 테스트 상태를 확인합니다.',
}

export const LIVE_CREATE_COMPLETE_STEP: LiveCreateStep = {
  id: 'complete',
  label: '완료',
  description: '라이브 개설 결과를 확인합니다.',
}

export const LIVE_CREATE_MOCK_PRODUCTS: LiveCreateProduct[] = [
  {
    id: 101,
    name: '90s 오버핏 데님 재킷',
    brand: "Levi's",
    category: '아우터',
    condition: '사용감 적음',
    price: 89000,
    thumbnailUrl: denimJacketImage,
  },
  {
    id: 102,
    name: '버버리 체크 트렌치 코트',
    brand: 'Burberry',
    category: '아우터',
    condition: '생활 사용감',
    price: 248000,
    thumbnailUrl: trenchCoatImage,
  },
  {
    id: 103,
    name: '프라다 빈티지 레더 백',
    brand: 'Prada',
    category: '가방',
    condition: '모서리 스크래치',
    price: 320000,
    thumbnailUrl: leatherBagImage,
  },
  {
    id: 104,
    name: '아디다스 삼바 스니커즈',
    brand: 'Adidas',
    category: '신발',
    condition: '밑창 사용감',
    price: 76000,
    thumbnailUrl: sneakersImage,
  },
]

export const LIVE_CREATE_VALIDATION_MESSAGES = {
  modeRequired: '방송 방식을 선택해 주세요.',
  titleRequired: '방송 제목을 입력해 주세요.',
  descriptionRequired: '한 줄 소개를 입력해 주세요.',
  mainBrandRequired: '대표 브랜드를 입력해 주세요.',
  productRequired: '라이브에 연결할 상품을 1개 이상 선택해 주세요.',
  scheduledDateRequired: '방송 날짜를 선택해 주세요.',
  scheduledTimeRequired: '시작 시간을 선택해 주세요.',
  scheduledDateTimePast: '예약 시간은 현재 시간 이후로 설정해 주세요.',
  deviceTestRequired: '방송 시작 전 카메라와 마이크 테스트를 완료해 주세요.',
} as const
