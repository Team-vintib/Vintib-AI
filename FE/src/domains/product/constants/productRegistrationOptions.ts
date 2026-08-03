import type {
  ProductRegistrationOption,
  ProductRegistrationStep,
} from '@/domains/product/types/productRegistration.types'

export interface ProductRegistrationMeasurementField {
  id: string
  label: string
}

export const PRODUCT_REGISTRATION_STEPS: ProductRegistrationStep[] = [
  {
    id: 'photos',
    label: '기본 정보',
  },
  {
    id: 'condition',
    label: '상태/하자',
  },
  {
    id: 'pricing',
    label: '가격',
  },
  {
    id: 'complete',
    label: '완료',
  },
]

export const PRODUCT_REGISTRATION_CATEGORY_OPTIONS: ProductRegistrationOption[] = [
  { id: 'outer', label: '아우터' },
  { id: 'top', label: '상의' },
  { id: 'bottom', label: '하의' },
  { id: 'dress', label: '원피스' },
  { id: 'shoes', label: '신발' },
  { id: 'accessory', label: '액세서리' },
  { id: 'etc', label: '기타' },
]

export const PRODUCT_REGISTRATION_CONDITION_OPTIONS: ProductRegistrationOption[] = [
  { id: 'S', label: 'S급' },
  { id: 'A', label: 'A급' },
  { id: 'B', label: 'B급' },
  { id: 'C', label: 'C급' },
]

export const PRODUCT_REGISTRATION_SALE_TYPE_OPTIONS: ProductRegistrationOption[] = [
  { id: 'DIRECT', label: '상시 판매' },
  { id: 'AUCTION', label: '경매' },
]

export const PRODUCT_REGISTRATION_COLOR_OPTIONS: ProductRegistrationOption[] = [
  { id: 'indigo', label: '인디고' },
  { id: 'black', label: '블랙' },
  { id: 'white', label: '화이트' },
  { id: 'ivory', label: '아이보리' },
  { id: 'beige', label: '베이지' },
  { id: 'camel', label: '카멜' },
  { id: 'gray', label: '그레이' },
  { id: 'brown', label: '브라운' },
  { id: 'navy', label: '네이비' },
  { id: 'blue', label: '블루' },
  { id: 'sky-blue', label: '스카이블루' },
  { id: 'green', label: '그린' },
  { id: 'khaki', label: '카키' },
  { id: 'red', label: '레드' },
  { id: 'pink', label: '핑크' },
  { id: 'yellow', label: '옐로우' },
  { id: 'orange', label: '오렌지' },
  { id: 'purple', label: '퍼플' },
  { id: 'silver', label: '실버' },
  { id: 'gold', label: '골드' },
  { id: 'multi', label: '멀티컬러' },
  { id: 'etc', label: '기타' },
]

export const PRODUCT_REGISTRATION_SIZE_OPTIONS: ProductRegistrationOption[] = [
  { id: 'XS', label: 'XS' },
  { id: 'S', label: 'S' },
  { id: 'M', label: 'M' },
  { id: 'L', label: 'L' },
  { id: 'XL', label: 'XL' },
  { id: 'FREE', label: 'Free' },
]

export const PRODUCT_REGISTRATION_MEASUREMENT_FIELDS_BY_CATEGORY: Record<
  string,
  ProductRegistrationMeasurementField[]
> = {
  outer: [
    { id: 'shoulder', label: '어깨' },
    { id: 'length', label: '총장' },
    { id: 'chest', label: '가슴' },
    { id: 'sleeve', label: '소매' },
  ],
  top: [
    { id: 'shoulder', label: '어깨' },
    { id: 'length', label: '총장' },
    { id: 'chest', label: '가슴' },
    { id: 'sleeve', label: '소매' },
  ],
  bottom: [
    { id: 'waist', label: '허리' },
    { id: 'hip', label: '엉덩이' },
    { id: 'totalLength', label: '총길이' },
    { id: 'thigh', label: '허벅지' },
    { id: 'hem', label: '밑단' },
  ],
  dress: [
    { id: 'shoulder', label: '어깨' },
    { id: 'length', label: '총장' },
    { id: 'chest', label: '가슴' },
    { id: 'waist', label: '허리' },
    { id: 'sleeveLength', label: '소매길이' },
    { id: 'hem', label: '밑단' },
  ],
  shoes: [{ id: 'size', label: '사이즈' }],
  accessory: [],
  etc: [],
}

export const PRODUCT_REGISTRATION_VALIDATION_MESSAGES = {
  frontPhotoRequired: 'Front View 사진을 업로드해 주세요.',
  backPhotoRequired: 'Back View 사진을 업로드해 주세요.',
  representativePhotoRequired: '대표 이미지를 선택해 주세요.',
  imageTypeInvalid: '이미지 파일만 업로드할 수 있습니다.',
  imageSizeInvalid: '이미지는 10MB 이하로 업로드해 주세요.',
  nameRequired: '상품명을 입력해 주세요.',
  brandRequired: '브랜드를 입력해 주세요.',
  colorRequired: '색상을 입력해 주세요.',
  customColorRequired: '기타 색상을 입력해 주세요.',
  categoryRequired: '카테고리를 선택해 주세요.',
  sizeRequired: '사이즈를 선택해 주세요.',
  measurementRequired: '실측 정보를 입력해 주세요.',
  measurementInvalid: '실측은 0보다 큰 숫자로 입력해 주세요.',
  conditionRequired: '상품 상태를 선택해 주세요.',
  defectRequired: '하자 여부를 선택해 주세요.',
  sellerDefectDescriptionRequired: '판매자가 확인한 하자 설명을 입력해 주세요.',
  aiPhotoRequired: 'AI 품질 검증에 사용할 Front View와 Back View 사진을 선택해 주세요.',
  aiPhotoConfirmationRequired: '품질 검증 사진별 확인을 완료해 주세요.',
  aiModelGenderRequired: 'AI 모델을 선택해 주세요.',
  saleTypeRequired: '판매 방식을 선택해 주세요.',
  directSalePriceRequired: '판매가를 입력해 주세요.',
  auctionStartPriceRequired: '시작가를 입력해 주세요.',
  priceInvalid: '가격은 0보다 큰 숫자로 입력해 주세요.',
} as const
