# Product list primary image response

## 요청 파트 / 대상 파트

- 요청 파트: FE
- 대상 파트: BE

## 배경/이유

상품 목록 화면과 라이브 생성 상품 선택 화면에서 등록 시 업로드한 대표 사진을 바로 표시해야 합니다. 현재 `GET /api/products`의 `ProductResponse`에는 이미지 URL 필드가 없어서 FE가 각 상품의 상세 API를 추가 호출해 이미지를 보강하고 있습니다.

## 요청 내용

- `GET /api/products` 목록 응답의 각 상품에 대표 이미지 URL을 포함해 주세요.
- FE는 우선 `primaryImageUrl` 필드명을 기준으로 읽고 있습니다.
- 대표 이미지가 없으면 `null` 또는 빈 문자열이어도 됩니다.
- 기존 상세 응답의 `images[].isPrimary`, `images[].sortOrder` 기준과 동일하게 대표 이미지를 결정해 주세요.

## 관련 FE 처리

- 현재 임시 처리:
  - `FE/src/domains/product/api/productApi.ts`에서 목록 이미지가 비어 있으면 `GET /products/{id}`를 추가 호출합니다.
  - `FE/src/domains/live/api/liveCreateApi.ts`에서도 라이브 연결 상품 썸네일 보강을 위해 같은 상세 조회를 사용합니다.
- BE 목록 응답에 `primaryImageUrl`이 포함되면 위 추가 호출은 제거할 수 있습니다.
