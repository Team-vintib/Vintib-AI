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

| 기능 | Method | 후보 endpoint |
| --- | --- | --- |
| 내 정보 조회 | GET | `/api/me` |
| 온보딩 저장 | PATCH | `/api/me/onboarding` |
| 내 정보 수정 | PATCH | `/api/me` |
| 주소 조회/저장 | GET/POST | `/api/addresses` |
| 사업자 인증 제출/조회 | POST/GET | `/api/business-verifications` |

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
