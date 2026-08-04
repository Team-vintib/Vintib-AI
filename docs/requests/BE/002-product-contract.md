# 002 Product API 요청

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
  - 목록 필터(카테고리/상태등급/판매방식/가격범위/정렬)는 구현 완료 — 아래 3.1 참고. `keyword`
    (검색어)만 아직 미구현이다(SEARCH-002 스코프, PROD-008과 별도).
  - 상세 응답 보강(판매자 통계/찜/연결 라이브/카테고리·브랜드명)은 구현 완료 — 아래 3.2 참고.
  - 상품 상세의 가격 분포, 유사 상품, AI 품질 분석/가격 추천은 화면 내 mock 또는 임시 데이터 성격이 남아 있다.

## 3. 추가 구현 요청

### 3.1 상품 목록 필터 구현/문서화 — 구현 완료, 계약은 다르게 확정됨

요청 그대로의 파라미터명으로 구현했다. `keyword`(검색어)만 통합 검색(005) 범위로 미룬 상태다.
확정 계약은 `docs/requests/FE/016-product-list-detail-contract.md` 참고.

### 3.2 상품 상세 응답 보강 — 구현 완료, 계약은 다르게 확정됨

`categoryName`/`brandName`/`isWished`/`sellerFollowerCount`/`sellerProductCount`/`linkedLive`를
추가했다. `seller` 중첩 객체 대신 최상위 평탄 필드로 냈고, 요청한 `relatedLive`는 `linkedLive`로
이름이 다르다. `similarProducts`/`priceDistribution`/이미지 `role`은 이번 범위 밖. 확정 계약은
`docs/requests/FE/016-product-list-detail-contract.md` 참고.

### 3.3 AI 품질 분석/가격 추천

- Method / Endpoint: BE 확정 필요
- 요청 목적: 상품 등록 중 사진 품질 분석과 추천 가격을 실제 AI/BE 결과로 대체한다.
- FE 사용처: `ProductRegistrationPage.vue`
- 요청 데이터: 상품 사진, 카테고리, 브랜드, 상태, 치수, 판매 방식 후보
- 응답 데이터: 품질 분석 결과, 보완 요청 항목, 추천 가격 구간
- 응답 예시: BE/AI 계약 확정 전이라 없음

## 4. 기존 API 변경 요청

- 기존 요청·응답에서 변경할 내용
  - `GET /api/products` query 필터 반영 — `keyword` 제외 완료(3.1 참고)
  - `GET /api/products/{id}` 상세 응답 보강 — `similarProducts`/`priceDistribution` 제외 완료(3.2 참고)
- 추가할 필드
  - 이미지 role 정책 필요 시 `images[].role`: `FRONT` | `BACK` | `ADDITIONAL` — 아직 미반영
- 변경 영향 범위
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

- FE·BE 간 결정이 필요한 내용 — 목록 필터 파라미터명·`saleType` enum(3.1), 비회원 `isWished`
  정책(3.2, `false`로 확정)은 해소됨
  - 이미지 role 저장 여부
  - AI 품질 분석 endpoint 위치
- 아직 확정되지 않은 응답 구조나 정책
  - 가격 분포/유사 상품 응답 구조
  - 상품 상태 enum 전체 목록

## 7. 추가 요청 없음

- 이미 정상 연동된 API
  - 상품 등록 기본 흐름
  - 이미지 업로드/등록
  - 상품 상세 찜 토글
- 기존 규격을 유지하면 되는 기능
  - 브랜드/카테고리 목록 조회
  - 상품 생성 기본 요청
