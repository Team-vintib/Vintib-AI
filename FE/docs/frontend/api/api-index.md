# API 목록

Swagger 제공 전까지는 임시 후보를 사용합니다. 실제 구현 시 Swagger/BE 계약을 1순위로 갱신해야 합니다.

## 인증

| 기능                 | Method | endpoint                      | 요청                                             | 응답                                              | 상태          |
| -------------------- | ------ | ----------------------------- | ------------------------------------------------ | ------------------------------------------------- | ------------- |
| 이메일 중복 확인     | POST   | `/api/auth/email/check-duplicate` | `email`                                       | `null`                                            | AUTH-001 연동 |
| 이메일 인증코드 발송 | POST   | `/api/auth/email/send-code`   | `email`                                          | `null`                                            | AUTH-001 연동 |
| 이메일 인증코드 확인 | POST   | `/api/auth/email/verify-code` | `email`, `code`                                  | `verificationToken`                               | AUTH-001 연동 |
| 이메일 회원가입      | POST   | `/api/auth/signup`            | `name`, `email`, `password`, `verificationToken` | `id`, `email`, `name`, `onboardingCompleted`      | AUTH-001 연동 |
| 이메일 로그인        | POST   | `/api/auth/login`             | `email`, `password`, `rememberMe`                | `accessToken`, `refreshToken`, `user`, `nextStep` | AUTH-002 연동 |
| 토큰 갱신            | POST   | `/api/auth/refresh`           | `refreshToken`                                   | `accessToken`                                     | 후보          |
| 로그아웃             | POST   | `/api/auth/logout`            | 없음 또는 `refreshToken`                         | 성공 여부                                         | 후보          |
| 싸피어스 callback    | POST   | `/api/auth/ssafy/callback`    | `authorizationCode`, `redirectUri`               | `linked`, `nextStep`, `user`                      | 후보          |

### 이메일 로그인

AUTH-002에서 FE가 연동한 후보 계약입니다. 공통 응답은 `ApiResponse<T>` envelope를 사용합니다.

```http
POST /api/auth/login
Content-Type: application/json
```

```json
{
  "email": "user@example.com",
  "password": "password123",
  "rememberMe": true
}
```

성공 응답 후보:

```json
{
  "success": true,
  "data": {
    "accessToken": "access-token",
    "refreshToken": "refresh-token",
    "user": {
      "id": 1,
      "email": "user@example.com",
      "name": "홍길동",
      "onboardingCompleted": false
    },
    "nextStep": "ONBOARD_PROFILE"
  },
  "error": null
}
```

- `accessToken`은 필수로 처리한다.
- `refreshToken`, `user`, `nextStep`은 서버 구현 차이에 대비해 optional로 처리한다.
- 로그인 성공 후 `redirect` query가 내부 경로이면 우선 이동한다.
- `nextStep` 또는 `user.onboardingCompleted` 기준으로 홈 또는 온보딩 기본정보 화면으로 이동한다.
- 로그인 실패 코드는 Swagger 확정 전까지 `C001`, 네트워크/타임아웃, 그 외 인증 실패로만 구분한다.

### 이메일 회원가입

AUTH-001에서 실제 연동한 계약입니다. 공통 응답은 `ApiResponse<T>` envelope를 사용합니다.

```http
POST /api/auth/email/check-duplicate
Content-Type: application/json
```

```json
{
  "email": "user@example.com"
}
```

성공하면 같은 이메일로 인증코드 발송 버튼과 인증코드 입력창을 활성화합니다.

```http
POST /api/auth/email/send-code
Content-Type: application/json
```

```json
{
  "email": "user@example.com"
}
```

```http
POST /api/auth/email/verify-code
Content-Type: application/json
```

```json
{
  "email": "user@example.com",
  "code": "123456"
}
```

성공 응답의 `data.verificationToken`을 회원가입 요청에 사용합니다.

```http
POST /api/auth/signup
Content-Type: application/json
```

```json
{
  "name": "홍길동",
  "email": "user@example.com",
  "password": "password123",
  "verificationToken": "verified-token"
}
```

- `U003`: 중복 이메일
- `U005`: 인증코드 불일치 또는 만료
- `U006`: 이메일 인증 필요
- `U007`: 인증 시도 횟수 초과
- `U008`: 인증코드 요청 횟수 초과
- `C001`: 입력값 검증 실패
- 이메일 입력값이 바뀌면 중복 확인, 인증코드 발송, 인증 완료, `verificationToken` 상태를 모두 초기화합니다.
- 로컬 Docker 환경에서 이메일 발송 500이 발생하면 BE 컨테이너에 `MAIL_*` 환경변수가 주입되는지 확인해야 합니다.

## 온보딩/내 정보

| 기능                    | Method   | endpoint                      | 상태                        |
| ----------------------- | -------- | ----------------------------- | --------------------------- |
| 내 정보 조회            | GET      | `/api/me`                     | 후보                        |
| 기본 정보 저장          | PATCH    | `/api/me/onboarding`          | S15P11A108-241 FE 선행 계약 |
| 관심 정보 저장·건너뛰기 | PUT      | `/api/me/interests`           | S15P11A108-250 FE 선행 계약 |
| AI 시착 정보 저장       | PUT      | `/api/me/tryon`               | S15P11A108-254 FE 선행 계약 |
| 회원 유형·온보딩 완료   | POST     | `/api/me/onboarding/complete` | S15P11A108-261 FE 선행 계약 |
| 내 정보 수정            | PATCH    | `/api/me`                     | 후보                        |
| 주소 조회/저장          | GET/POST | `/api/addresses`              | 후보                        |
| 사업자 인증 제출/조회   | POST/GET | `/api/business-verifications` | S15P11A108-400 FE 계약 제안 |

### 기본 정보 저장

BE 구현 전 FE가 선행 정의한 임시 계약입니다. BE Swagger가 제공되면 실제 계약을 기준으로
타입과 오류 처리를 갱신합니다.

```http
PATCH /api/me/onboarding
Authorization: Bearer {accessToken}
Content-Type: application/json
```

```json
{
  "nickname": "빈티지러버",
  "gender": "FEMALE",
  "phoneNumber": "010-1234-5678",
  "postalCode": "06236",
  "address": "서울 강남구 테헤란로 212",
  "detailAddress": "3층"
}
```

- `gender`: `MALE | FEMALE`
- `postalCode`: 주소 검색을 사용하면 우편번호, 주소를 직접 입력하면 `null`
- 나머지 필드는 필수

성공 응답:

```json
{
  "success": true,
  "data": null,
  "error": null
}
```

검증 실패는 `400 / C001`과 `error.errors`를 사용한다. 필드명은 `nickname`,
`gender`, `phoneNumber`, `postalCode`, `address`, `detailAddress` 중 하나로 전달한다.

### 관심 정보 저장·건너뛰기

BE 구현 전 FE가 선행 정의한 임시 계약입니다. 인증 토큰에서 현재 회원을 식별하며,
선택 저장과 건너뛰기는 같은 멱등 PUT endpoint를 사용합니다.

```http
PUT /api/me/interests
Authorization: Bearer {accessToken}
Content-Type: application/json
```

선택 저장:

```json
{
  "brandIds": ["brand-a", "brand-c"],
  "categoryIds": ["outer", "top"]
}
```

건너뛰기:

```json
{
  "brandIds": [],
  "categoryIds": []
}
```

성공 응답:

```json
{
  "success": true,
  "data": null,
  "error": null
}
```

- `brandIds`, `categoryIds`는 중복 없는 문자열 배열입니다.
- 빈 배열은 해당 관심 정보가 없는 상태로 저장하며 기존 선택값도 비웁니다.
- 현재 문자열 ID는 FE 화면의 임시 식별자입니다. 브랜드·카테고리 마스터 조회 API와
  서버 ID 타입이 확정되면 실제 ID로 교체해야 합니다.
- HTTP 성공이어도 `success: false`이면 저장 실패로 처리합니다.
- 검증 실패는 `error.message`를 화면 공통 오류로 표시합니다.

### AI 시착 정보 저장

BE 구현 전 FE가 선행 정의한 임시 계약입니다. 전신 사진과 신체 정보는 모두 선택 사항이며,
값이 있는 항목만 multipart form-data에 포함합니다.

```http
PUT /api/me/tryon
Authorization: Bearer {accessToken}
Content-Type: multipart/form-data
```

| multipart 필드 | 타입           | 필수 | 설명                         |
| -------------- | -------------- | ---- | ---------------------------- |
| `bodyPhoto`    | image file     | 선택 | AI 시착용 정면 전신 사진     |
| `heightCm`     | integer string | 선택 | 키(cm)                       |
| `weightKg`     | integer string | 선택 | 몸무게(kg)                   |
| `chest`        | integer string | 선택 | 가슴 치수, 단위 미확정       |
| `waist`        | integer string | 선택 | 허리 치수, 단위 미확정       |
| `hip`          | integer string | 선택 | 엉덩이 치수, 단위 미확정     |

- 숫자 필드는 현재 FE에서 빈 값 또는 0보다 큰 정수만 허용합니다.
- 건너뛰기는 이 API를 호출하지 않고 다음 온보딩 화면으로 이동합니다.
- 사진과 숫자가 모두 비어 있는 `다음 단계`도 저장할 값이 없으므로 API를 호출하지 않습니다.
- 사진이나 숫자가 하나라도 있으면 API 저장 성공 후에만 다음 화면으로 이동합니다.
- 브라우저가 multipart boundary를 생성하도록 FE는 `Content-Type` 값을 직접 고정하지 않습니다.
- 검증 실패의 `error.errors[].field`는 위 multipart 필드명을 사용한다고 임시 정의합니다.
- BE Swagger가 제공되면 endpoint, 필드명, 파일 제한, 단위와 숫자 범위를 갱신해야 합니다.

### 회원 유형 저장·온보딩 완료

BE 구현 전 FE가 선행 정의한 임시 계약입니다. 회원 유형 저장과 최종 온보딩 완료를 하나의
요청으로 처리합니다.

```http
POST /api/me/onboarding/complete
Authorization: Bearer {accessToken}
Content-Type: application/json
```

```json
{
  "memberType": "GENERAL"
}
```

- `memberType`: `GENERAL | BUSINESS`
- 회원 유형 저장과 `onboardingCompleted = true` 변경은 하나의 트랜잭션으로 처리합니다.
- HTTP 성공이어도 `success: false`이면 완료 실패로 처리합니다.
- 성공한 `GENERAL` 회원은 HOME으로 이동합니다.
- 성공한 `BUSINESS` 회원은 BIZ-001 사업자 인증 화면으로 이동합니다.
- 실패 시 선택값을 유지하며 사용자가 다시 요청할 수 있습니다.
- BE Swagger가 제공되면 endpoint, enum과 중복 완료 정책을 실제 계약에 맞춥니다.

### 사업자 인증 제출

S15P11A108-400에서는 실제 API를 호출하지 않고 FE 더미 제출 상태만 구현했습니다.
아래 내용은 BE 검토를 위한 후보 계약이며 Swagger 확정 후 타입과 API 함수를 구현합니다.

```http
POST /api/business-verifications
Authorization: Bearer {accessToken}
Content-Type: multipart/form-data
```

| multipart 필드 | 타입 | 필수 | FE 임시 규칙 |
| --- | --- | --- | --- |
| `businessRegistrationNumber` | string | 예 | 하이픈 없는 숫자 10자리 |
| `businessName` | string | 예 | 공백 제외 값 필요 |
| `representativeName` | string | 예 | 공백 제외 값 필요 |
| `certificate` | image file | 예 | 한 개, `image/*` MIME 1차 확인 |

성공 응답 후보:

```json
{
  "success": true,
  "data": {
    "id": 1,
    "status": "PENDING",
    "submittedAt": "2026-07-27T17:00:00+09:00"
  },
  "error": null
}
```

- 브라우저가 multipart boundary를 생성하도록 FE는 `Content-Type` 값을 직접 고정하지
  않습니다.
- 사업자등록번호 체크섬, 이미지 확장자·MIME·용량·해상도와 중복 제출 정책은 미확정입니다.
- 실제 API 연동 전까지 제출 정보는 Pinia 메모리 상태로만 BIZ-001-2에 전달합니다.
- BIZ-001-2 상태 조회 endpoint와 승인·반려 상태 값도 BE 확인이 필요합니다.

## 이후 화면 후보

| 영역   | 후보 endpoint                                                        |
| ------ | -------------------------------------------------------------------- |
| 상품   | `/api/products`, `/api/products/{id}`                                |
| 찜     | `/api/products/{id}/wish`                                            |
| 라이브 | `/api/lives`, `/api/lives/{id}`                                      |
| 경매   | `/api/auctions`, `/api/auctions/{id}`                                |
| 주문   | `/api/orders`, `/api/orders/{id}`                                    |
| 배송   | `/api/shipments`                                                     |
| 환불   | `/api/refunds`                                                       |
| 포인트 | `/api/points`, `/api/points/transactions`, `/api/points/withdrawals` |
| 알림   | `/api/notifications`                                                 |
| 팔로우 | `/api/users/{id}/follow`                                             |

### 상품 목록 조회

PROD-008 껍데기 화면은 실제 API를 호출하지 않는다. 목록 연동 시
`GET /api/products`를 후보로 사용하되 아래 항목은 Swagger와 BE 계약에서 확정한다.

- pagination 방식과 응답 envelope
- 검색어, 카테고리, 상태 등급과 판매 방식 query 이름
- 최신순·가격 낮은순·가격 높은순 정렬 값
- 상시 판매와 경매 상품의 가격 필드 구분
- 찜 여부를 공개 목록 응답에 포함할지 여부

## 공통 오류 코드

- `C001`
- `U003`
- `U005`
- `U006`
- `U007`
- `U008`
- `AUTH_REQUIRED`
- `PERMISSION_DENIED`
- `VALIDATION_ERROR`
- `RESOURCE_NOT_FOUND`
- `REQUEST_ALREADY_PROCESSED`
- `PRODUCT_SOLD_OUT`
- `AUCTION_CLOSED`
- `POINT_INSUFFICIENT`
- `REALTIME_CONNECTION_FAILED`
- `INTERNAL_ERROR`

## 2026-07-28 통합 검색 API 후보

SEARCH-001/002 검색 결과 화면은 현재 mock data를 클라이언트에서 필터링합니다. 실제 API 연동 시
아래 항목은 BE Swagger/계약 확정 후 adapter로 교체해야 합니다.

### 통합 검색 조회

- 후보 endpoint: `GET /api/search` 또는 도메인별 검색 endpoint 조합
- 현재 FE query: `keyword`, `type`, `page`, `categories`, `conditions`, `saleTypes`, `minPrice`, `maxPrice`, `sort`
- `type` 후보값: `all`, `product`, `live`, `member`
- `page`: `product`, `live`, `member` 탭 페이지 번호. `all` 탭과 첫 페이지에서는 생략합니다.
- `categories`: 상품 카테고리 복수 선택
- `conditions`: 상품 상태 등급 복수 선택
- `saleTypes`: `DIRECT`, `AUCTION`
- `minPrice`, `maxPrice`: 숫자형 가격 범위
- `sort`: `LATEST`, `PRICE_ASC`, `PRICE_DESC`
- `status`: FE mock 상태 확인 전용 query이며 실제 API query가 아닙니다.

확정 필요 항목:

- 통합 검색 단일 endpoint 사용 여부와 path
- 상품/라이브/회원 결과를 한 응답에 포함할지, 탭별 endpoint로 나눌지
- 탭별 count와 pagination 응답 구조
- `all` 탭 preview 개수와 전체보기 진입 시 page 초기화 정책
- 상품 카드의 찜 여부와 판매 유형/가격 필드 구조
- 라이브 카드의 실시간 상태, 시청자 수, 썸네일 필드 구조
- 회원 카드의 팔로우 여부, 통계 필드, 프로필 상세 route
