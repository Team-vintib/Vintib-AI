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
  - AI 품질 분석은 구현 완료(등록 시점 확정 데이터 기준) — 아래 3.3 참고. 가격 분포·유사 상품·
    AI 가격 추천은 여전히 mock/임시 데이터 성격이 남아 있다.

## 3. 추가 구현 요청

### 3.1 상품 목록 필터 구현/문서화 — 구현 완료, 계약은 다르게 확정됨

요청 그대로의 파라미터명으로 구현했다. `keyword`(검색어)만 통합 검색(005) 범위로 미룬 상태다.
확정 계약은 `docs/requests/FE/016-product-list-detail-contract.md` 참고.

### 3.2 상품 상세 응답 보강 — 구현 완료, 계약은 다르게 확정됨

`categoryName`/`brandName`/`isWished`/`sellerFollowerCount`/`sellerProductCount`/`linkedLive`를
추가했다. `seller` 중첩 객체 대신 최상위 평탄 필드로 냈고, 요청한 `relatedLive`는 `linkedLive`로
이름이 다르다. `similarProducts`/`priceDistribution`은 이번 범위 밖. 이미지 `role`은 이후
`SY043`으로 반영 완료(아래 4번 참고).

### 3.3 AI 품질 분석 — 구현 완료(`SY043`), AI 가격 추천은 여전히 미착수

품질 분석은 "등록 시점에 사용자가 인정/확정한 하자"만 저장하는 범위로 구현했다 —
`POST /products`의 `aiQualityFindings`를 저장했다가 `GET /products/{id}`의
`aiQualityAnalysis.images[].findings`로 그대로 돌려준다. AI가 실시간으로 분석 중인 상태
(`ANALYZING`/`FAILED`)는 BE가 관측할 수 없어 상태값은 `NOT_REQUESTED`/`NO_FINDINGS`/
`COMPLETED` 3종만 낸다. 상세는 `docs/plans/BE/SY043-product-image-role-quality-findings.md`
참고.

가격 추천(추천 판매가/경매 시작가)은 이 문서 범위 밖으로 남는다 — 별도 스레드
(`docs/requests/BE/043-registration-price-chart-source.md`,
`044-pricing-estimate-trigger.md`)에서 다룬다.

## 4. 기존 API 변경 요청

- 기존 요청·응답에서 변경할 내용
  - `GET /api/products` query 필터 반영 — `keyword` 제외 완료(3.1 참고)
  - `GET /api/products/{id}` 상세 응답 보강 — `similarProducts`/`priceDistribution` 제외 완료(3.2 참고)
- 추가한 필드
  - `images[].role`: `FRONT` | `BACK` | `ADDITIONAL` — `SY043`으로 반영 완료. `POST /products/{id}/images`
    요청에도 `role`이 필수로 추가됐다.
- 변경 영향 범위
  - 상품 등록 AI 검증 단계

## 5. 보류 또는 시연 제외 범위

- 현재 구현하지 않아도 되는 기능
  - AI 가격 추천
  - 상품 수정/삭제 화면 연결
- 추후 구현 예정 기능
  - 상품 관리/수정 화면
  - 유사 상품 추천 고도화

> **2026-08-07 정리**: "판매자별 상품 목록"은 `GET /api/products?sellerId=...`로 이미 구현
> 완료됐다(PROD-008, 공개 프로필에서 사용). 항목에서 뺐다.
>
> **2026-08-08 정리**: 이미지 `role`, AI 품질 분석(3.3)은 `SY043`으로 반영 완료돼 위 항목에서
> 뺐다. 관련 요청 문서 `019-product-quality-multi-image.md`/`041-quality-inspection-integration.md`/
> `042-product-registration-ai-pipeline.md`도 같은 작업으로 해소돼 삭제했다.

## 6. 협의 필요 사항

- FE·BE 간 결정이 필요한 내용 — 목록 필터 파라미터명·`saleType` enum(3.1), 비회원 `isWished`
  정책(3.2, `false`로 확정), 이미지 role 저장 여부(3.3, `SY043`으로 저장 확정)는 해소됨
  - AI 가격 추천 endpoint 위치
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