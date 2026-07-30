# API 명세서

## 미분류

| 이름 | Method | Endpoint | 인증 필요 여부 | 관련 기능 ID | 구현 완료 여부 |
| :--- | :--- | :--- | :---: | :--- | :---: |
| 공통 응답 구조 |  |  |  |  | ✓ |
| 헬스체크 | GET | `/health` |  |  | ✓ |

## 인증(Auth)

| 이름 | Method | Endpoint                      | 인증 필요 여부 | 관련 기능 ID | 구현 완료 여부 |
| :--- | :--- |:------------------------------| :---: | :--- | :---: |
| 이메일 중복 확인 | POST | `/auth/email/check-duplicate` |  | AUTH-001 | ✓ |
| 이메일 인증코드 발송 | POST | `/auth/email/send-code`       |  | AUTH-001 | ✓ |
| 이메일 인증코드 확인 | POST | `/auth/email/verify-code`     |  | AUTH-001 | ✓ |
| 이메일 회원가입 | POST | `/auth/signup`                |  | AUTH-001 | ✓ |
| 로그인 | POST | `/auth/signin`                |  | AUTH-002 | ✓ |
| 토큰 재발급 | POST | `/auth/reissue`               |  | AUTH-002 | ✓ |
| 로그아웃 | POST | `/auth/logout`                | ✓ | AUTH-002 | ✓ |

## 회원 (Users)

| 이름 | Method | Endpoint | 인증 필요 여부 | 관련 기능 ID | 구현 완료 여부 |
| :--- | :--- | :--- | :---: | :--- | :---: |
| 내 정보 조회 | GET | `/users/me` |  | MY-001 |  |
| 회원 상세 조회 | GET | `/users/{id}` |  |  |  |
| 회원 정보 등록, 수정 | PATCH | `/users/{id}` |  | ONBOARD-001, MY-001 |  |
| 관심 정보 조회 | GET | `/users/{id}/interests` |  | ONBOARD-002 |  |
| 관심 정보 등록, 수정 | PUT | `/users/{id}/interests` |  | ONBOARD-002 |  |

## 사업자 (Businesses)

| 이름 | Method | Endpoint | 인증 필요 여부 | 관련 기능 ID | 구현 완료 여부 |
| :--- | :--- | :--- | :---: | :--- | :---: |
| 사업자 인증 상태 조회 | GET | `/users/{id}/business` |  | MY-008 |  |
| 사업자 정보 등록 | POST | `/users/{id}/business` |  | BIZ-001 |  |
| 사업자 정보 수정 | PATCH | `/users/{id}/business` |  | MY-008 |  |
| 세금계산서 발행 요청 | POST | `/orders/{id}/invoices` |  | BIZ-002 |  |
| 세금계산서 조회 | GET | `/orders/{id}/invoices` |  | BIZ-002 |  |

## 검색 / 추천 (Discovery)

| 이름 | Method | Endpoint | 인증 필요 여부 | 관련 기능 ID | 구현 완료 여부 |
| :--- | :--- | :--- | :---: | :--- | :---: |
| 통합 검색 (상품, 라이브, 회원) | GET | `/search` |  | SEARCH-001, SEARCH-002 |  |
| 개인화 추천 조회 | GET | `/users/{id}/picks` |  | REC-001 |  |

## 팔로우 / 찜 (Socials)

| 이름 | Method | Endpoint | 인증 필요 여부 | 관련 기능 ID | 구현 완료 여부 |
| :--- | :--- | :--- | :---: | :--- | :---: |
| 팔로워 목록 조회 | GET | `/users/{id}/followers` |  | MY-006 |  |
| 팔로잉 목록 조회 | GET | `/users/{id}/followings` |  | MY-006 |  |
| 팔로우 | POST | `/users/{id}/followers` |  | FOLLOW-001 |  |
| 팔로우 해제 | DELETE | `/users/{id}/followers` |  | FOLLOW-001 |  |
| 찜 목록 조회 | GET | `/users/{userId}/wishes` | ✓ | MY-006., MY-009 |  |
| 상품 찜 | POST | `/users/{userId}/wishes` | ✓ | MY-009 |  |
| 상품 찜 해제 | DELETE | `/users/{userId}/wishes/{id}` | ✓ | MY-009 |  |

## 알림 (Notifications)

| 이름 | Method | Endpoint | 인증 필요 여부 | 관련 기능 ID | 구현 완료 여부 |
| :--- | :--- | :--- | :---: | :--- | :---: |
| 알림 목록 조회 | GET | `/users/{id}/alerts` | ✓ | NOTI-001~005 | ✓ |
| 알림 전체 읽음 처리 | PATCH | `/users/{userId}/alerts/read-all` | ✓ | NOTI-001 | ✓ |
| 알림 읽음 처리 | PATCH | `/users/{userId}/alerts/{id}` | ✓ | NOTI-001 | ✓ |

## 상품 (Products)

| 이름 | Method | Endpoint | 인증 필요 여부 | 관련 기능 ID | 구현 완료 여부 |
| :--- | :--- | :--- | :---: | :--- | :---: |
| 상품 목록 조회 | GET | `/products` |  | PROD-008, SEARCH-002 | ✓ |
| 상품 기본 정보 저장 | POST | `/products` | ✓ | PROD-001 | ✓ |
| 상품 이미지 등록 | POST | `/products/{id}/images` | ✓ | PROD-001 | ✓ |
| 상품 이미지 업로드 URL 발급 | POST | `/products/{id}/images/upload-url` | ✓ | PROD-001 | ✓ |
| 경매 상품 등록 및 경매 전환 | PATCH | `/products/{id}/auction-schedule` | ✓ | PROD-003, PROD-004 | ✓ |
| 판매 가격 설정 및 상시 판매 등록 | PATCH | `/products/{id}/status` | ✓ | PROD-002, PROD-004, PROD-005, AUCT-014 | ✓ |
| 상품 이미지 삭제 | DELETE | `/products/{id}/images/{imgId}` | ✓ | PROD-001 | ✓ |
| 상품 이미지 수정 | PATCH | `/products/{id}/images/{imageId}` | ✓ | PROD-001 | ✓ |
| 상품 상세 조회 | GET | `/products/{id}` |  | PROD-006 | ✓ |
| 카테고리 전체 목록 조회 | GET | `/categories` |  | PROD-001 | ✓ |
| 브랜드 전체 목록 조회 | GET | `/brands` |  | PROD-001 | ✓ |
| 상품 정보 수정 | PATCH | `/products/{id}` | ✓ | PROD-007 | ✓ |
| 상품 삭제 | DELETE | `/products/{id}` | ✓ | PROD-007 | ✓ |

## 라이브 / 채팅 (Lives)

| 이름 | Method | Endpoint | 인증 필요 여부 | 관련 기능 ID | 구현 완료 여부 |
| :--- | :--- | :--- | :---: | :--- | :---: |
| 라이브 목록 조회 | GET | `/lives` |  | MY-005 |  |
| 라이브 예약 개설 | POST | `/lives/schedule` | ✓ | LIVE-001 | ✓ |
| 라이브 즉시 개설 | POST | `/lives` | ✓ | LIVE-002 | ✓ |
| 라이브 상세 조회 | GET | `/lives/{id}` |  | LIVE-005 |  |
| 라이브 정보 수정 | PATCH | `/lives/{id}` |  | LIVE-001 |  |
| 라이브 상품 목록 조회 | GET | `/lives/{id}/products` |  | LIVE-003 | ✓ |
| 라이브 상품 등록 | POST | `/lives/{id}/products` | ✓ | LIVE-003, LIVE-006 | ✓ |
| 라이브 상품 해제 | DELETE | `/lives/{liveId}/products/{id}` | ✓ | LIVE-003 | ✓ |
| 채팅 메시지 목록 조회 | GET | `/lives/{id}/messages` |  | CHAT-001 |  |
| 채팅 메시지 전송 | POST | `/lives/{id}/messages` |  | CHAT-001, CHAT-002, CHAT-003 |  |
| 채팅 메시지 숨김, 차단 처리 | PATCH | `/lives/{liveId}/messages/{id}` |  | CHAT-004 |  |
| STT 변환 텍스트 조회 | GET | `/lives/{id}/transcripts` |  | LIVE-007 |  |

## 경매 / 입찰 (Auctions)

| 이름 | Method | Endpoint | 인증 필요 여부 | 관련 기능 ID | 구현 완료 여부 |
| :--- | :--- | :--- | :---: | :--- | :---: |
| 경매 조건 설정 | POST | `/lives/{liveId}/auctions` | ✓ | AUCT-001 | ✓ |
| 경매 조건 조회 | GET | `/products/{id}/auction` |  | AUCT-001 |  |
| 경매 시작 | POST | `/lives/{id}/auctions` |  | AUCT-002 |  |
| 경매 상세 조회 | GET | `/auctions/{id}` |  | AUCT-011 |  |
| 입찰 내역 조회 | GET | `/auctions/{id}/bids` |  | AUCT-003~006 |  |
| 입찰 | POST | `/auctions/{id}/bids` |  | AUCT-003~010 |  |
| 낙찰 결과 조회 | GET | `/auctions/{id}/winner` |  | AUCT-012, AUCT-013 |  |

## 포인트 / 계좌 / 출금 (Wallet)

| 이름 | Method | Endpoint | 인증 필요 여부 | 관련 기능 ID | 구현 완료 여부 |
| :--- | :--- | :--- | :---: | :--- | :---: |
| 잔액 조회 | GET | `/users/{id}/points` |  | POINT-002 |  |
| 사용 내역 조회 | GET | `/users/{id}/points/logs` |  | POINT-002 |  |
| 포인트 충전 | POST | `/users/{id}/points/charges` |  | POINT-001 |  |
| 출금 신청 | POST | `/users/{id}/withdrawals` |  | POINT-004 |  |
| 출금 내역 조회 | GET | `/users/{id}/withdrawals` |  | POINT-004, MY-007 |  |

## 주문 / 배송 / 환불 (Orders)

| 이름 | Method | Endpoint | 인증 필요 여부 | 관련 기능 ID | 구현 완료 여부 |
| :--- | :--- | :--- | :---: | :--- | :---: |
| 주문 목록 조회 | GET | `/users/{id}/orders` |  | MY-003, MY-004 |  |
| 상시 판매 주문 생성 | POST | `/orders` |  | SALE-001, SALE-002 |  |
| 주문 상세 조회 | GET | `/orders/{id}` |  | MY-003 |  |
| 주문 배송지 조회 | GET | `/orders/{id}/address` |  | ORDER-001 |  |
| 주문 배송지 등록, 수정 | PATCH | `/orders/{id}/address` |  | ORDER-001 |  |
| 구매 확정 처리 | POST | `/orders/{id}/confirmation` |  | ORDER-002, ORDER-003 |  |
| 송장 정보 조회 | GET | `/orders/{id}/shipment` |  | SHIP-002 |  |
| 송장 정보 등록 | POST | `/orders/{id}/shipment` |  | SHIP-001 |  |
| 환불 요청 목록 조회 | GET | `/orders/{id}/refunds` |  | REFUND-001 |  |
| 환불 요청 등록 | POST | `/orders/{id}/refunds` |  | REFUND-001 |  |
| 환불 승인, 거절 처리 | PATCH | `/refunds/{id}` |  | REFUND-002 |  |

## AI 가상 시착 (TryOns)

| 이름 | Method | Endpoint | 인증 필요 여부 | 관련 기능 ID | 구현 완료 여부 |
| :--- | :--- | :--- | :---: | :--- | :---: |
| 시착 프로필 조회 | GET | `/users/{userId}/tryon` |  | TRYON-001, TRYON-002 |  |
| 시착 프로필 등록, 수정 | PUT | `/users/{id}/tryon` |  | TRYON-001, TRYON-002 |  |
| 시착 프로필 삭제 | DELETE | `/users/{id}/tryon` |  | TRYON-001 |  |
| 가상 시착 생성 | POST | `/users/{id}/tryons` |  | TRYON-003, TRYON-004 |  |
| 시착 결과 목록 조회 | GET | `/users/{userId}/tryons` | ✓ | TRYON-005 | ✓ |
| 시착 결과 상세 조회 | GET | `/users/{userId}/tryons/{id}` | ✓ | TRYON-005 | ✓ |
| 시착 결과 삭제 | DELETE | `/users/{userId}/tryons/{id}` | ✓ | TRYON-005 | ✓ |

## 홈 (Home)

| 이름 | Method | Endpoint | 인증 필요 여부 | 관련 기능 ID | 구현 완료 여부 |
| :--- | :--- | :--- | :---: | :--- | :---: |
| 홈 콘텐츠 조회 | GET | `/home` |  | HOME-001 | ✓ |
| 팔로잉 콘텐츠 조회 | GET | `/home/following` | ✓ | HOME-002 | ✓ |