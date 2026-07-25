# API 후보 목록

Swagger 제공 전까지 사용하는 임시 후보입니다. 실제 구현 시 Swagger 계약을 1순위로 갱신해야 합니다.

## 인증

| 기능 | Method | 후보 endpoint | 요청 | 응답 |
| --- | --- | --- | --- | --- |
| 이메일 회원가입 | POST | `/api/auth/signup` | `name`, `email`, `password`, `agreements` | `user`, `nextStep` |
| 이메일 로그인 | POST | `/api/auth/login` | `email`, `password`, `rememberMe` | `accessToken`, `refreshToken`, `user` |
| 토큰 갱신 | POST | `/api/auth/refresh` | `refreshToken` | `accessToken` |
| 로그아웃 | POST | `/api/auth/logout` | 없음 또는 `refreshToken` | 성공 여부 |
| 싸피어스 callback | POST | `/api/auth/ssafy/callback` | `authorizationCode`, `redirectUri` | `linked`, `nextStep`, `user` |

## 온보딩/내 정보

| 기능 | Method | endpoint | 상태 |
| --- | --- | --- | --- |
| 내 정보 조회 | GET | `/api/me` | 후보 |
| 기본 정보 저장 | PATCH | `/api/me/onboarding` | S15P11A108-241 FE 선행 계약 |
| 내 정보 수정 | PATCH | `/api/me` | 후보 |
| 주소 조회/저장 | GET/POST | `/api/addresses` | 후보 |
| 사업자 인증 제출/조회 | POST/GET | `/api/business-verifications` | 후보 |

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

## 이후 화면 후보

| 영역 | 후보 endpoint |
| --- | --- |
| 상품 | `/api/products`, `/api/products/{id}` |
| 찜 | `/api/products/{id}/wish` |
| 라이브 | `/api/lives`, `/api/lives/{id}` |
| 경매 | `/api/auctions`, `/api/auctions/{id}` |
| 주문 | `/api/orders`, `/api/orders/{id}` |
| 배송 | `/api/shipments` |
| 환불 | `/api/refunds` |
| 포인트 | `/api/points`, `/api/points/transactions`, `/api/points/withdrawals` |
| 알림 | `/api/notifications` |
| 팔로우 | `/api/users/{id}/follow` |

## 공통 오류 코드

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
