# SY038 상품 도메인 보강 (대표 이미지 · 유사 상품 · AI 착용컷 필드)

기능번호는 서로 다르지만(PROD-008/PROD-006/PROD-001) 전부 상품 등록/조회 응답을 다루는 작은 보강이라
한 브랜치·한 PR로 묶어 처리한다.

## 1. 상품 목록 대표 이미지 (PROD-008)

### 배경/목표

`docs/requests/BE/009-product-list-primary-image.md`. `GET /api/products` 목록 응답에 대표 이미지 URL이
없어 FE가 상품마다 상세 API를 추가 호출하고 있다. 목록 응답에 대표 이미지 URL을 포함해 이 왕복을 없앤다.

### 작업 내용

- `ProductResponse`에 `primaryImageUrl: String` 필드를 추가한다.
- `ProductImageRepository.findByProduct_IdInAndPrimaryTrue`(이미 홈 도메인 팔로잉 피드에서 쓰는 배치
  조회 메서드)를 재사용해, 목록 조회 후 상품 ID들을 모아 대표 이미지를 한 번에 조회한다(N+1 방지).
- 대표 이미지가 없는 상품은 `null`로 내려간다.
- `ProductResponse`를 함께 쓰는 `getProductList`(`GET /api/products`)와 `getMyProducts`(`GET
  /api/users/{userId}/products`) 양쪽에 동일하게 적용한다 — 같은 응답 타입이라 한쪽만 채우면 일관성이
  깨진다.
- presigned URL 발급은 상세 조회와 동일한 방식(`ProductImageService`)을 따른다.

### 구현 목록

- [x] `ProductResponse`에 `primaryImageUrl` 필드 추가
- [x] `ProductService.getProductList`/`getMyProducts`에서 대표 이미지 배치 조회 후 매핑
- [x] 관련 테스트 추가(대표 이미지 있음/없음 케이스)
- [x] Swagger `@Schema` 갱신

## 2. 상품 상세 유사 상품 목록 (PROD-006)

### 배경/목표

`docs/requests/BE/011-product-similar-price-distribution.md`. 상품 상세의 "유사 상품 가격대 그래프"가
실데이터 없이 빈 배열로 렌더된다. 유사 상품 목록(`id`/`title`/`price`)을 상세 응답에 채운다.

### 작업 내용

- "유사" 판정 기준(사용자 확정): **같은 `categoryId`인 상품을 필터링**하고, 그중 **같은 `brandId`인
  상품을 우선 노출**한다.
- `GET /api/products/{id}` 응답(`ProductDetailResponse`)에 `similarProducts: List<SimilarProductResponse>`
  필드를 추가한다(요청 문서가 제시한 별도 엔드포인트 대신 상세 응답에 포함 — 상세 조회 1회로 그래프까지
  그릴 수 있어 왕복이 적다).
- 정렬: 같은 브랜드(브랜드 일치)를 앞에, 그 다음 최신 등록순.
- 제외 대상: 현재 상품 자신, `DRAFT` 상태 상품(비공개).
- 개수 상한: 20개(그래프용으로 충분한 표본 — 문서에서 "수 개~수십 개"로 BE 판단에 위임).
- `SimilarProductResponse(id, title, price)` — 요청 문서가 명시한 최소 3개 필드만 담는다.

### 구현 목록

- [x] `SimilarProductResponse` DTO 추가(`id`/`title`/`price`)
- [x] `ProductRepository`에 유사 상품 조회 쿼리 추가(같은 카테고리, 현재 상품 제외, DRAFT 제외, 브랜드
      일치 우선 정렬, limit 20)
- [x] `ProductDetailResponse`에 `similarProducts` 필드 추가, `ProductService.getProductDetail`에서 조립
- [x] 관련 테스트 추가(같은 브랜드 우선 정렬, 카테고리 다른 상품 제외, DRAFT 제외 케이스)
- [x] Swagger `@Schema` 갱신

### 확인이 필요한 미결정 사항

- 개수 상한 20을 그대로 써도 되는지(그래프 표본 수가 부족/과다하면 조정)

## 3. 상품 등록 AI 착용컷 설정 필드 (PROD-001)

### 배경/목표

`docs/requests/BE/012-product-ai-tryon-registration-fields.md`. 상품 등록 시 마네킹 사진 기반 AI
착용컷 사용 여부와 모델 성별을 저장할 필드가 없다. `ProductCreateRequest`/`Product`/응답 DTO에 필드를
추가한다.

### 작업 내용

- `aiModelEnabled: boolean` — AI 착용컷(마네킹 사진 기반 합성) 사용 여부. 기본값 `false`.
- `aiModelGender: MALE | FEMALE` — 마네킹 사진 속 모델이 어떤 성별로 보이게 할지. **`aiModelEnabled=true`일
  때 필수(null 불가)**, `false`면 `null`. 이 값은 프로필 표시용이 아니라 "합성 시 어떤 성별 모델 사진을
  쓸지"를 판매자가 정하는 값이다.
- 검증: `aiModelEnabled=true`인데 `aiModelGender`가 없으면 400. 요청 DTO 레벨 커스텀 검증(예:
  `@AssertTrue`) 또는 서비스 레벨 검증으로 처리한다.
- DB: `product.ai_model_enabled boolean not null default false`, `product.ai_model_gender varchar(10)
  null`, 체크 제약 `ai_model_enabled = false OR ai_model_gender IS NOT NULL`로 애플리케이션 검증을
  DB 레벨에서도 보강한다.
- `ProductDetailResponse`에도 두 필드를 추가해 상품 상세에서 설정값을 확인할 수 있게 한다. 목록
  (`ProductResponse`)에는 추가하지 않는다(요청 문서 범위 밖, FE 사용처 없음).
- `ProductUpdateRequest`/수정 API는 이번 범위에 포함하지 않는다(요청 문서가 등록만 다룸).

### 구현 목록

- [x] `Product` 엔티티에 `aiModelEnabled`/`aiModelGender` 컬럼 추가 + 체크 제약
- [x] `AiModelGender` enum 추가(`MALE`, `FEMALE`)
- [x] `ProductCreateRequest`에 필드 추가 + `enabled=true`면 `gender` 필수 검증
- [x] `ProductService.createProduct`에서 필드 저장
- [x] `ProductDetailResponse`에 필드 추가
- [x] 관련 테스트 추가(`enabled=true`+`gender` 없음 → 400, `enabled=false`+`gender` 있음 케이스 등)
- [x] Swagger `@Schema` 갱신
