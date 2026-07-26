# API 목록

Swagger 제공 전까지는 임시 후보를 사용합니다. 실제 구현 시 Swagger/BE 계약을 1순위로 갱신해야 합니다.

## 인증

| 기능                 | Method | endpoint                      | 요청                                             | 응답                                         | 상태          |
| -------------------- | ------ | ----------------------------- | ------------------------------------------------ | -------------------------------------------- | ------------- |
| 이메일 인증코드 발송 | POST   | `/api/auth/email/send-code`   | `email`                                          | `null`                                       | AUTH-001 연동 |
| 이메일 인증코드 확인 | POST   | `/api/auth/email/verify-code` | `email`, `code`                                  | `verificationToken`                          | AUTH-001 연동 |
| 이메일 회원가입      | POST   | `/api/auth/signup`            | `name`, `email`, `password`, `verificationToken` | `id`, `email`, `name`, `onboardingCompleted` | AUTH-001 연동 |
| 이메일 로그인        | POST   | `/api/auth/login`             | `email`, `password`, `rememberMe`                | `accessToken`, `refreshToken`, `user`        | 후보          |
| 토큰 갱신            | POST   | `/api/auth/refresh`           | `refreshToken`                                   | `accessToken`                                | 후보          |
| 로그아웃             | POST   | `/api/auth/logout`            | 없음 또는 `refreshToken`                         | 성공 여부                                    | 후보          |
| 싸피어스 callback    | POST   | `/api/auth/ssafy/callback`    | `authorizationCode`, `redirectUri`               | `linked`, `nextStep`, `user`                 | 후보          |

### 이메일 회원가입

AUTH-001에서 실제 연동한 계약입니다. 공통 응답은 `ApiResponse<T>` envelope를 사용합니다.

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
- 로컬 Docker 환경에서 이메일 발송 500이 발생하면 BE 컨테이너에 `MAIL_*` 환경변수가 주입되는지 확인해야 합니다.

## 온보딩/내 정보

| 기능                    | Method   | endpoint                      | 상태                        |
| ----------------------- | -------- | ----------------------------- | --------------------------- |
| 내 정보 조회            | GET      | `/api/me`                     | 후보                        |
| 기본 정보 저장          | PATCH    | `/api/me/onboarding`          | S15P11A108-241 FE 선행 계약 |
| 관심 정보 저장·건너뛰기 | PUT      | `/api/me/interests`           | S15P11A108-250 FE 선행 계약 |
| 내 정보 수정            | PATCH    | `/api/me`                     | 후보                        |
| 주소 조회/저장          | GET/POST | `/api/addresses`              | 후보                        |
| 사업자 인증 제출/조회   | POST/GET | `/api/business-verifications` | 후보                        |

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
