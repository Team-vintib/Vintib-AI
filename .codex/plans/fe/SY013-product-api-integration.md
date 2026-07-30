# 상품 API 연동 계획

## 배경/목표

상품 관련 화면은 목록, 상세, 등록 플로우까지 UI가 구현되어 있으나 현재 대부분 목업 데이터와 목업 adapter를 사용한다. BE에는 상품 기본 생성, 목록, 상세, 이미지 presigned 업로드/등록/수정/삭제, 상시 판매 상태 전환, 찜 API가 구현되어 있으므로 우선 붙일 수 있는 API를 실제 연동하고, 화면이 요구하지만 BE 계약이 부족한 항목은 `.codex/requests/be/006-product-contract.md`에 요청으로 남긴다.

이번 작업은 구현 전에 계약과 순서를 정리하는 문서 작업이다. 사용자가 승인하면 이 계획 기준으로 FE 구현을 시작한다.

## 현재 FE 구현 상태

| 화면/기능 | 현재 상태 | 주요 파일 |
| --- | --- | --- |
| 상품 목록 | `PRODUCT_LIST_MOCK_DATA` 기반 필터/정렬/페이지 UI. 서버 API 미연동 | `FE/src/domains/product/pages/ProductListView.vue`, `FE/src/domains/product/constants/productListMockData.ts` |
| 상품 카드 찜 | 로컬 `Set`으로 토글만 처리. 서버 찜 API 미연동 | `FE/src/domains/product/pages/ProductListView.vue`, `FE/src/domains/product/components/ProductCard.vue` |
| 상품 상세 | `getProductDetailViewData()`가 목업 상세를 반환. 서버 상세 API 미연동 | `FE/src/domains/product/pages/ProductDetailView.vue`, `FE/src/domains/product/api/productDetailApi.ts` |
| 상세 찜/장바구니/구매/판매자 이동 | 화면 상태 메시지 또는 로컬 토글. 실제 API/라우팅 미연동 | `FE/src/domains/product/pages/ProductDetailView.vue`, `FE/src/domains/product/components/ProductPurchaseSummary.vue` |
| 가격 분포/유사 상품 | 목업 상세 데이터 기반 | `FE/src/domains/product/components/ProductPriceDistribution.vue` |
| 판매자 라이브 패널 | 목업 `linkedLive` 기반 | `FE/src/domains/product/components/ProductSellerLivePanel.vue` |
| AI 품질 분석 | 목업 시나리오 기반 | `FE/src/domains/product/components/AiQualityAnalysisPanel.vue` |
| 상품 등록 | 다단계 UI와 검증은 구현됨. 제출은 `submitProductRegistrationDraft()` 목업 | `FE/src/domains/product/pages/ProductRegistrationPage.vue`, `FE/src/domains/product/api/productRegistrationApi.ts` |
| 등록 이미지 | 브라우저 preview만 사용. presigned 업로드 미연동 | `FE/src/domains/product/components/ProductPhotoUploader.vue` |
| 브랜드/카테고리 옵션 | FE 상수 기반 | `FE/src/domains/product/constants/productRegistrationOptions.ts` |

## 현재 BE에서 우선 연동 가능한 API

| 기능 | Method | Endpoint | FE 적용 |
| --- | --- | --- | --- |
| 브랜드 목록 | `GET` | `/api/brands` | 등록 화면 브랜드 옵션으로 전환 |
| 카테고리 목록 | `GET` | `/api/categories` | 등록/목록 필터 카테고리 옵션으로 전환 |
| 상품 목록 | `GET` | `/api/products` | 목록 화면 데이터 소스로 전환. 단 대표 이미지/브랜드명/찜 여부 부족 |
| 상품 상세 | `GET` | `/api/products/{id}` | 상세 기본 정보와 이미지 갤러리 연동. 단 판매자 통계/가격분포/AI/라이브 부족 |
| 상품 생성 | `POST` | `/api/products` | 등록 기본 정보 저장 |
| 이미지 업로드 URL 발급 | `POST` | `/api/products/{id}/images/upload-url` | 이미지별 presigned URL 발급 |
| S3 업로드 | `PUT` | 발급된 `uploadUrl` | 파일 직접 업로드 |
| 이미지 등록 | `POST` | `/api/products/{id}/images` | 업로드 완료 이미지 DB 등록 |
| 상시 판매 전환 | `PATCH` | `/api/products/{id}/status` | 직접 판매 가격 설정 및 공개 |
| 상품 찜 | `POST` | `/api/users/{userId}/wishes` | 목록/상세 찜 추가 |
| 상품 찜 해제 | `DELETE` | `/api/users/{userId}/wishes/{productId}` | 목록/상세 찜 해제 |
| 찜 목록 | `GET` | `/api/users/{userId}/wishes` | 초기 찜 상태 보정 후보 |

## FE 구현 계획

1. 상품 API adapter와 DTO 타입 정리
   - `domains/product/api/`에 목록/상세/등록/찜/마스터 데이터 API 함수를 분리한다.
   - BE의 `ApiResponse<T>`, `PageResponse<T>`를 unwrap하는 패턴은 홈/라이브 API의 기존 방식과 맞춘다.
   - BE DTO와 화면 ViewData 사이에는 mapping 함수를 둔다. 화면 타입을 BE 응답 타입에 직접 종속시키지 않는다.

2. 상품 목록 API 연동
   - `GET /products`를 호출해 목록 데이터를 가져온다.
   - 현재 UI의 필터/정렬/페이지 상태를 query param으로 보낼 준비를 한다.
   - BE가 아직 최신순 고정이면 FE 정렬 select는 유지하되 실제 적용 가능한 범위를 문서/상태로 제한한다.
   - 대표 이미지가 없는 응답은 임시 fallback 이미지를 사용한다.
   - 네트워크 실패/빈 목록/loading 상태를 목록 화면에 추가한다.

3. 상품 상세 API 연동
   - `GET /products/{id}` 응답을 `ProductDetailViewData`로 매핑한다.
   - BE에서 제공되는 기본 필드와 images는 실제 응답을 사용한다.
   - 판매자 통계, 연결 라이브, 유사 상품 가격 분포, AI 품질 분석은 BE 계약이 생기기 전까지 기존 목업 또는 빈 상태로 fallback한다.
   - 404는 기존 `not-found`, 그 외 실패는 `error` 상태로 연결한다.

4. 찜 API 연동
   - 로그인 상태에서 목록/상세 찜 토글 시 `POST /users/{userId}/wishes`, `DELETE /users/{userId}/wishes/{productId}`를 호출한다.
   - 비로그인 사용자는 로그인 이동 또는 안내 상태로 처리한다.
   - BE 응답에 `isLiked`가 없으면 초기 찜 여부는 `GET /users/{userId}/wishes` 결과로 보정하거나 false로 시작한다.

5. 상품 등록 API 연동
   - 제출 시 `POST /products`로 DRAFT 상품을 먼저 생성한다.
   - 각 이미지에 대해 `POST /products/{id}/images/upload-url` -> presigned `PUT` -> `POST /products/{id}/images` 순서로 업로드한다.
   - 직접 판매 선택 시 `PATCH /products/{id}/status`로 가격을 설정하고 공개한다.
   - 경매 선택은 BE 상태 전환/라이브 경매 계약이 확인되기 전까지 요청 문서 기준으로 보류하거나 등록 완료 후 DRAFT 상태 유지 정책을 명시한다.

6. 마스터 데이터 연동
   - 브랜드/카테고리 옵션은 API에서 불러오되 실패 시 기존 상수 fallback을 유지한다.
   - FE의 카테고리 코드와 BE categoryId 매핑이 필요한 경우 mapping 테이블을 별도 상수로 둔다.

7. 검증
   - `npm run type-check`
   - `npm run build`
   - 로컬 FE/BE 실행 후 상품 목록, 상세, 등록 직접 판매 플로우를 브라우저에서 확인한다.

## BE 요청으로 남긴 항목

상세 내용은 `.codex/requests/be/006-product-contract.md`에 정리한다.

- 상품 목록 필터/정렬/검색 query param 계약
- 상품 목록 카드용 대표 이미지, 브랜드명, 카테고리명, 찜 여부 응답 필드
- 상품 상세 화면용 판매자 통계, 연결 라이브, 유사 상품/가격분포, AI 품질 분석 응답
- 상품 등록 확장 필드: 색상, 소재, 구매 시기/국가, 실측, 하자 설명
- 이미지 역할(`FRONT`, `BACK`, `ADDITIONAL`) 저장 여부
- 경매 상품 등록/상태 전환/라이브 연결 흐름
- 가격 추천 API와 AI 품질 검사 API
- 비회원 상품 목록 조회 허용 여부와 인증 정책

