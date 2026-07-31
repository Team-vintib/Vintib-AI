# 006 Product API 요청

## 1. 요청 개요

- 요청 파트: FE
- 대상 파트: BE
- 요청 목적: 상품 목록/상세/등록 연동 상태와 남은 상품 API 보강 요청을 정리한다.
- 우선순위: P0
- 시연 필수 여부: 상품 목록/상세/등록 기본 흐름은 필수. AI 분석/가격 추천은 시연 범위에 따라 보류 가능.

## 2. 현재 연동 상태

- 연동 완료 API
  - `GET /api/brands`
  - `GET /api/categories`
  - `GET /api/products`
  - `GET /api/products/{id}`
  - `POST /api/products`
  - `PATCH /api/products/{id}/status`
  - `POST /api/products/{id}/auction-schedule`
  - `POST /api/products/{id}/images/upload-url`
  - `POST /api/products/{id}/images`
  - `POST /api/users/{userId}/wishes`
  - `DELETE /api/users/{userId}/wishes/{productId}`
- FE 구현 완료 범위
  - 상품 목록/상세 화면
  - 상품 등록 기본 플로우
  - presigned URL 기반 이미지 업로드/등록 플로우
  - 상품 상세 찜 추가/해제
- 현재 임시 처리 또는 Mock 사용 여부
  - 목록 query 필터 일부는 FE에서 보내지만 BE 미구현이면 결과에 반영되지 않는다.
  - 상품 상세의 가격 분포, 유사 상품, AI 품질 분석/가격 추천은 화면 내 mock 또는 임시 데이터 성격이 남아 있다.

## 3. 추가 구현 요청

### 3.1 상품 목록 필터 구현/문서화

- Method / Endpoint: `GET /api/products`
- 요청 목적: FE 상품 목록 필터 UI가 실제 조회 결과에 반영되도록 한다.
- FE 사용처: `ProductListView.vue`
- 요청 데이터
  - Query
    - `keyword`: string | null
    - `categoryIds`: string | null, comma-separated ids
    - `conditionGrades`: string | null, comma-separated grades
    - `saleType`: `DIRECT` | `AUCTION` | null
    - `minPrice`: number | null
    - `maxPrice`: number | null
    - `sort`: string | null
    - `page`: number
    - `size`: number
- 응답 데이터
  - 기존 PageResponse<Product> 유지
- 응답 예시

```json
{
  "success": true,
  "data": {
    "content": [
      {
        "id": 1,
        "sellerId": 10,
        "categoryId": 2,
        "categoryName": "자켓",
        "brandId": 1,
        "brandName": "Levi's",
        "title": "빈티지 자켓",
        "conditionGrade": "A",
        "saleType": "DIRECT_SALE",
        "saleStatus": "ON_SALE",
        "price": 59000,
        "primaryImageUrl": null,
        "isWished": false,
        "createdAt": "2026-07-31T12:00:00"
      }
    ],
    "page": 0,
    "size": 20,
    "totalElements": 1,
    "totalPages": 1,
    "hasNext": false
  },
  "error": null
}
```

### 3.2 상품 상세 응답 보강

- Method / Endpoint: `GET /api/products/{id}`
- 요청 목적: 상세 화면에서 판매자 요약, 연결 라이브, 상세 치수, 유사 상품을 실제 데이터로 표시한다.
- FE 사용처: `ProductDetailView.vue`
- 요청 데이터
  - Path: `id`
- 응답 데이터
  - 기존 상세 필드 유지
  - 추가 후보: `seller`, `relatedLive`, `measurements`, `similarProducts`, `priceDistribution`
- 응답 예시

```json
{
  "success": true,
  "data": {
    "id": 1,
    "sellerNickname": "vintagelover",
    "images": [],
    "measurements": {
      "chest": 52,
      "length": 68
    },
    "relatedLive": null,
    "similarProducts": []
  },
  "error": null
}
```

### 3.3 AI 품질 분석/가격 추천

- Method / Endpoint: BE 확정 필요
- 요청 목적: 상품 등록 중 사진 품질 분석과 추천 가격을 실제 AI/BE 결과로 대체한다.
- FE 사용처: `ProductRegistrationPage.vue`
- 요청 데이터: 상품 사진, 카테고리, 브랜드, 상태, 치수, 판매 방식 후보
- 응답 데이터: 품질 분석 결과, 보완 요청 항목, 추천 가격 구간
- 응답 예시: BE/AI 계약 확정 전이라 없음

## 4. 기존 API 변경 요청

- 기존 요청·응답에서 변경할 내용
  - `GET /api/products` query 필터 반영
  - `GET /api/products/{id}` 상세 응답 보강
- 추가할 필드
  - 이미지 role 정책 필요 시 `images[].role`: `FRONT` | `BACK` | `ADDITIONAL`
  - 상세 치수 `measurements`
  - 판매자 요약 `seller`
  - 연결 라이브 `relatedLive`
- 변경 영향 범위
  - 상품 목록 필터/정렬
  - 상품 상세 정보 섹션
  - 상품 등록 AI 검증 단계

## 5. 보류 또는 시연 제외 범위

- 현재 구현하지 않아도 되는 기능
  - AI 품질 분석/가격 추천
  - 상품 수정/삭제 화면 연결
  - 이미지 role 기반 고급 검증
- 추후 구현 예정 기능
  - 상품 관리/수정 화면
  - 유사 상품 추천 고도화
  - 판매자별 상품 목록

## 6. 협의 필요 사항

- FE·BE 간 결정이 필요한 내용
  - 목록 query 필터 이름과 enum 이름
  - `saleType` enum을 `DIRECT`, `DIRECT_SALE`, `AUCTION` 중 무엇으로 통일할지
  - 비회원 목록/상세의 `isWished` 값 정책
  - 이미지 role 저장 여부
  - AI 품질 분석 endpoint 위치
- 아직 확정되지 않은 응답 구조나 정책
  - 가격 분포/유사 상품 응답 구조
  - 상세 치수 필드명
  - 상품 상태 enum 전체 목록

## 7. 추가 요청 없음

- 이미 정상 연동된 API
  - 상품 등록 기본 흐름
  - 이미지 업로드/등록
  - 상품 상세 찜 토글
- 기존 규격을 유지하면 되는 기능
  - 브랜드/카테고리 목록 조회
  - 상품 생성 기본 요청
