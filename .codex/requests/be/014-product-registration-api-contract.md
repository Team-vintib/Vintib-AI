# 상품 등록 API 계약 보완 요청

- **요청자 파트**: FE
- **대상 파트**: BE
- **관련 티켓**: `S15P11A108-409`, `S15P11A108-411`, `S15P11A108-414`

## 배경/이유

FE 상품 등록 화면은 사진 등록, 기본 정보, 사이즈/소재, 상태/하자, AI 품질 검증, 가격, 검토, 완료까지
7단계 플로우로 구현되어 있다. 현재 Swagger의 상품 API는 기본 상품 생성, 이미지 등록, 상시 판매 가격
설정 중심이라 FE 등록 플로우 전체를 실제 API에 연결하기에는 계약이 부족하다.

확인한 Swagger URL:

- `https://i15a108.p.ssafy.io/swagger-ui/index.html`

## 현재 Swagger 기준 구현된 Product API

현재 product 관련으로 확인한 주요 endpoint는 다음과 같다.

| Method | Endpoint | 현재 용도 |
| --- | --- | --- |
| `GET` | `/api/products` | 공개 상품 목록 조회 |
| `POST` | `/api/products` | DRAFT 상품 기본 정보 생성 |
| `GET` | `/api/products/{id}` | 상품 상세 조회 |
| `PATCH` | `/api/products/{id}` | 상품 정보 수정 |
| `DELETE` | `/api/products/{id}` | 상품 삭제 |
| `PATCH` | `/api/products/{id}/status` | DRAFT 상품을 상시 판매로 전환하고 가격 설정 |
| `POST` | `/api/products/{id}/images/upload-url` | 상품 이미지 presigned upload URL 발급 |
| `POST` | `/api/products/{id}/images` | 업로드 완료 이미지 상품에 등록 |
| `PATCH` | `/api/products/{id}/images/{imageId}` | 이미지 순서/대표 여부 수정 |
| `DELETE` | `/api/products/{id}/images/{imageId}` | 상품 이미지 삭제 |
| `GET` | `/api/categories` | 카테고리 목록 조회 |
| `GET` | `/api/brands` | 브랜드 목록 조회 |

현재 `POST /api/products` 요청 필드는 아래 수준으로 확인된다.

```json
{
  "title": "빈티지 리바이스 데님 자켓",
  "description": "1990년대 리바이스 데님 자켓, 상태 양호",
  "categoryId": 1,
  "brandId": 1,
  "conditionGrade": "A",
  "sizeLabel": "M"
}
```

현재 `PATCH /api/products/{id}/status` 요청 필드는 상시 판매 가격만 받는다.

```json
{
  "price": 50000
}
```

## FE 상품 등록 플로우와 현재 API 차이

### 사진 등록

- FE는 `Front View` 1장, `Back View` 1장을 필수로 받고 추가 사진은 제한 없이 받는다.
- 현재 BE 이미지 등록은 상품당 최대 10장으로 문서화되어 있다.
- 현재 이미지 API에는 이미지 역할(`FRONT`, `BACK`, `ADDITIONAL`)이 없다.
- 대표 이미지는 `isPrimary`로 처리 가능하지만, Front/Back 필수 검증을 BE에서도 할지 정책 확인이 필요하다.

### 기본 정보

- FE는 `상품명`, `브랜드`, `색상`, `카테고리`, `상품 설명`, `구매 시기`, `구매 국가`를 입력한다.
- 현재 BE는 `brandId`, `categoryId`를 받는다.
- FE는 현재 브랜드를 문자열로 입력하고 카테고리는 FE 화면용 id(`outer`, `top`, `bottom` 등)를 사용한다.
- 현재 BE 요청에는 `color`, `purchasedAt`, `purchasedCountry`가 없다.

### 사이즈/소재/실측

- FE는 `size`, `material`, `measurements` JSON을 가진다.
- 현재 BE 요청에는 `sizeLabel`만 있고 `material`, `measurements`가 없다.
- FE 실측 정책:
  - 아우터/상의: `shoulder`, `length`, `chest`, `sleeve`
  - 하의: `waist`, `hip`, `totalLength`, `thigh`, `hem`
  - 원피스: `shoulder`, `length`, `chest`, `waist`, `sleeveLength`, `hem`
  - 신발: `size`
  - 액세서리/기타: 실측 없음
- 실측 값은 cm 기준 단면 길이이며 JSON 객체로 전송할 계획이다.

### 상태/하자 및 AI 품질 검증

- FE는 판매자 직접 입력으로 `conditionGrade`, `hasDefect`, `sellerDefectDescription`을 받는다.
- 현재 BE 요청에는 `conditionGrade`만 있고 하자 여부/하자 설명 저장 필드가 없다.
- FE는 등록 사진 중 AI 품질 검증 사진을 선택하고, 사진별 후보 마스킹/카드 선택 결과를 저장해야 한다.
- 현재 상품 등록/상세 API에는 AI 품질 검증 생성, 결과 저장, 상세 조회 계약이 없다.

### 판매 방식/가격

- FE 판매 방식은 `상시 판매` 또는 `경매`이다.
- 상시 판매는 `price`, 경매는 `startPrice`를 입력한다.
- 현재 BE는 `PATCH /api/products/{id}/status`로 상시 판매 가격 설정만 제공한다.
- 경매는 `/api/lives/{liveId}/auctions`에서 라이브에 연결된 상품에 조건을 설정하는 구조로 보인다.
- FE 상품 등록 화면에서는 경매 선택 시 경매 라이브 선택이 선택값이다. 경매 라이브 미선택 상태로 상품을 경매 예정 상태로 둘 수 있는지 정책 확인이 필요하다.

### AI 가격 추천

- FE는 가격 단계에서 AI 가격 추천 카드와 가격 분포 그래프를 표시한다.
- 필요한 데이터:
  - 가격 구간별 상품 수
  - `S급`, `A급`, `B급`, `C급` 추천 가격
  - 조회 중/실패/데이터 없음/성공 상태
- 현재 Swagger에는 AI 가격 추천 endpoint가 없다.

## 요청 내용

### 1. 상품 등록 요청/응답 계약 확장

FE 등록 플로우를 실제 저장하려면 아래 필드 저장 계약이 필요하다.

```json
{
  "title": "90s 오버핏 데님 재킷",
  "brandId": 1,
  "brandName": "Levi's",
  "categoryId": 1,
  "categoryCode": "outer",
  "color": "indigo",
  "description": "상품 설명",
  "purchasedAt": "1990년대",
  "purchasedCountry": "미국",
  "sizeLabel": "M",
  "material": "면 100%",
  "measurements": {
    "shoulder": 45,
    "length": 68,
    "chest": 54,
    "sleeve": 61
  },
  "conditionGrade": "A",
  "hasDefect": true,
  "sellerDefectDescription": "왼쪽 소매 끝단 마모"
}
```

확정 필요:

- 브랜드를 `brandId`만 받을지, 신규/기타 브랜드 문자열 등록도 허용할지
- 카테고리를 `categoryId`만 받을지, FE 코드값과 매핑할 별도 필드를 둘지
- 색상 enum/문자열 정책
- 구매 시기/구매 국가 저장 여부와 필드명
- 소재/실측 JSON 저장 여부와 필드명
- 하자 여부/하자 설명 저장 여부와 필드명

### 2. 이미지 역할 및 개수 정책 확정

FE 요구사항은 Front View/Back View 필수, 추가 사진 제한 없음이다. 현재 BE는 상품당 최대 10장으로 보인다.

요청:

- 이미지 등록/수정 응답 또는 요청에 `role` 추가 검토
  - 후보: `FRONT`, `BACK`, `ADDITIONAL`
- BE 이미지 최대 개수를 FE 요구사항과 맞출지 확정
- Front View/Back View 최소 1장 검증을 BE에서도 할지 확정
- 대표 이미지는 현재 `isPrimary` 유지 가능

이미지 등록 후보:

```json
{
  "key": "product-images/1/abc123.jpg",
  "sortOrder": 0,
  "isPrimary": true,
  "role": "FRONT"
}
```

### 3. 상시 판매/경매 등록 흐름 확정

현재 상시 판매는 `PATCH /api/products/{id}/status`로 연결 가능해 보인다. 경매 상품은 추가 계약이 필요하다.

요청:

- 상시 판매 전환 endpoint는 현재대로 사용할 수 있는지 확인
- 경매 선택 시 상품 상태를 `AUCTION_SCHEDULED`로 만들 endpoint 필요 여부 확인
- 경매 라이브를 선택하지 않은 상품도 경매 예정 상품으로 등록 가능한지 확인
- 경매 라이브 선택 시 필요한 처리 순서 확정
  - 상품 생성
  - 이미지 등록
  - 라이브 상품 연결
  - 경매 조건 설정

경매 등록 후보:

```http
PATCH /api/products/{id}/auction
```

```json
{
  "startPrice": 30000,
  "liveId": 101
}
```

또는 기존 `/api/lives/{liveId}/products`, `/api/lives/{liveId}/auctions` 조합을 사용할 경우 FE에서 따라야 할 정확한 순서와 필수값을 문서화해주길 요청한다.

### 4. AI 품질 검증 저장/조회 계약 요청

FE는 AI 품질 검증 결과를 상품 상세의 AI 분석 결과로 노출해야 한다.

요청 endpoint 후보:

```http
POST /api/products/{id}/quality-inspections
PATCH /api/products/{id}/quality-inspections/{inspectionId}/confirm
GET /api/products/{id}/quality-inspections
```

저장 데이터 후보:

```json
{
  "photoId": 10,
  "status": "CONFIRMED",
  "findings": [
    {
      "labelNumber": 1,
      "description": "소매 끝단 마모 의심",
      "box": {
        "x": 12.5,
        "y": 42.1,
        "width": 18.0,
        "height": 10.4
      },
      "isActualDefect": true
    }
  ],
  "maskedImageUrl": "https://..."
}
```

확정 필요:

- AI 호출 주체가 FE인지 BE인지
- AI 분석 중/실패/결과 없음/완료 상태 enum
- bounding box 좌표 단위: `%` 또는 pixel
- 사용자가 실제 하자 여부를 수정한 결과 저장 방식
- 상품 상세 조회에 AI 분석 결과를 포함할지, 별도 endpoint로 조회할지

### 5. AI 가격 추천 API 요청

가격 단계에서 사용할 추천 데이터 조회 endpoint가 필요하다.

요청 endpoint 후보:

```http
POST /api/products/price-recommendations
```

요청 후보:

```json
{
  "title": "90s 오버핏 데님 재킷",
  "brandId": 1,
  "categoryId": 1,
  "conditionGrade": "A",
  "sizeLabel": "M",
  "color": "indigo"
}
```

응답 후보:

```json
{
  "buckets": [
    {
      "label": "5~7만",
      "minPrice": 50000,
      "maxPrice": 70000,
      "productCount": 24
    }
  ],
  "recommendedPrices": [
    {
      "grade": "S",
      "price": 108000
    },
    {
      "grade": "A",
      "price": 92000
    }
  ]
}
```

## FE 처리 계획

- BE 계약 확정 전까지 `FE/src/domains/product/api/productRegistrationApi.ts`의 mock adapter를 사용한다.
- 실제 API가 확정되면 `submitProductRegistrationDraft()` 내부에서 다음 순서로 연결한다.
  1. 상품 기본 정보 생성
  2. 이미지 upload URL 발급 및 업로드
  3. 이미지 등록/대표 이미지 설정
  4. 상시 판매 또는 경매 상태 설정
  5. AI 품질 검증 결과 저장
- 가격 추천 API가 확정되면 가격 단계의 mock 그래프 데이터를 API 응답으로 교체한다.

## FE 관련 파일

- `FE/src/domains/product/pages/ProductRegistrationPage.vue`
- `FE/src/domains/product/api/productRegistrationApi.ts`
- `FE/src/domains/product/types/productRegistration.types.ts`
- `FE/src/domains/product/constants/productRegistrationOptions.ts`
- `FE/docs/frontend/screens/PROD-001/requirements.md`
- `.codex/plans/fe/SY009-product-registration.md`
