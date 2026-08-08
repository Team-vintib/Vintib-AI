# API 명세서

## 시스템 (System)

| 이름 | Method | Endpoint | 인증 필요 여부 | 관련 기능 ID | 구현 완료 여부 |
| :--- | :--- | :--- | :---: | :--- | :---: |
| 공통 응답 구조 |  |  |  |  | ✓ |
| 헬스체크 | GET | `/health` |  |  | ✓ |

## 인증(Auth)

| 이름 | Method | Endpoint | 인증 필요 여부 | 관련 기능 ID | 구현 완료 여부 |
| :--- | :--- | :--- | :---: | :--- | :---: |
| 이메일 중복 확인 | POST | `/auth/email/check-duplicate` |  | AUTH-001 | ✓ |
| 이메일 인증코드 발송 | POST | `/auth/email/send-code` |  | AUTH-001 | ✓ |
| 이메일 인증코드 확인 | POST | `/auth/email/verify-code` |  | AUTH-001 | ✓ |
| 이메일 회원가입 | POST | `/auth/signup` |  | AUTH-001 | ✓ |
| 로그인 | POST | `/auth/signin` |  | AUTH-002 | ✓ |
| 토큰 재발급 | POST | `/auth/reissue` |  | AUTH-002 | ✓ |
| 로그아웃 | POST | `/auth/logout` | ✓ | AUTH-002 | ✓ |
| 구글 로그인 | POST | `/auth/google` |  | AUTH-003 | ✓ |
| 구글 계정 연동 확인 | POST | `/auth/google/link` |  | AUTH-003 | ✓ |

## 회원 (Users)

| 이름 | Method | Endpoint | 인증 필요 여부 | 관련 기능 ID | 구현 완료 여부 |
| :--- | :--- | :--- | :---: | :--- | :---: |
| 내 정보 조회 | GET | `/users/{id}` | ✓ | MY-001 | ✓ |
| 회원 정보 등록, 수정 | PATCH | `/users/{id}` | ✓ | ONBOARD-001, MY-001 | ✓ |
| 관심 정보 조회 | GET | `/users/{id}/interests` | ✓ | ONBOARD-002 | ✓ |
| 관심 정보 등록, 수정 | PUT | `/users/{id}/interests` | ✓ | ONBOARD-002 | ✓ |
| 회원 유형 저장, 온보딩 완료 | PATCH | `/users/{id}/member-type` | ✓ | ONBOARD-004 | ✓ |
| 소개글 등록, 수정 | PATCH | `/users/{id}/bio` | ✓ | MY-001 | ✓ |
| 프로필 이미지 업로드 URL 발급 | POST | `/users/{id}/profile-image/upload-url` | ✓ | MY-001 | ✓ |
| 프로필 이미지 확정 | PUT | `/users/{id}/profile-image` | ✓ | MY-001 | ✓ |
| 프로필 이미지 삭제 | DELETE | `/users/{id}/profile-image` | ✓ | MY-001 | ✓ |
| 커버 이미지 업로드 URL 발급 | POST | `/users/{id}/cover-image/upload-url` | ✓ | MY-001 | ✓ |
| 커버 이미지 확정 | PUT | `/users/{id}/cover-image` | ✓ | MY-001 | ✓ |
| 커버 이미지 삭제 | DELETE | `/users/{id}/cover-image` | ✓ | MY-001 | ✓ |
| 마이페이지 요약 조회 | GET | `/users/{id}/mypage` | ✓ | MY-001~009 | ✓ |
| 공개 회원/판매자 프로필 조회 | GET | `/users/{id}/profile` |  | MY-010 | ✓ |

> 공개 프로필은 비회원도 조회 가능(`businessVerified` 포함). 소개글(`PATCH /users/{id}/bio`)은 부분 수정이 아니라 미입력 시 삭제된다.
>
> 프로필/커버 이미지는 presigned 2단계: `upload-url` 발급 → 클라이언트가 S3에 직접 PUT → `PUT .../profile-image`(또는 `cover-image`)에 `{key}` 전달해 확정. `DELETE`는 참조만 비우고 S3 객체는 남긴다.

## 사업자 (Businesses)

| 이름 | Method | Endpoint | 인증 필요 여부 | 관련 기능 ID | 구현 완료 여부 |
| :--- | :--- | :--- | :---: | :--- | :---: |
| 사업자등록증 이미지 업로드 URL 발급 | POST | `/users/{userId}/business/upload-url` | ✓ | BIZ-001 | ✓ |
| 사업자 인증 상태 조회 | GET | `/users/{id}/business` | ✓ | MY-008 | ✓ |
| 사업자 정보 등록 | POST | `/users/{id}/business` | ✓ | BIZ-001 | ✓ |
| 세금계산서 발행 요청 | POST | `/orders/{orderId}/invoices` | ✓ | BIZ-002 | ✓ |
| 세금계산서 조회 | GET | `/orders/{orderId}/invoices` | ✓ | BIZ-002 | ✓ |

> 사업자 정보 수정(PATCH)은 없다 — 등록(POST)이 재제출까지 겸한다(REJECTED 상태에서만 재제출 가능).

## 검색 / 추천 (Discovery)

| 이름 | Method | Endpoint | 인증 필요 여부 | 관련 기능 ID | 구현 완료 여부 |
| :--- | :--- | :--- | :---: | :--- | :---: |
| 통합 검색 (상품, 라이브, 회원) | GET | `/search` |  | SEARCH-001, SEARCH-002 | ✓ |

## 팔로우 / 찜 (Socials)

| 이름 | Method | Endpoint | 인증 필요 여부 | 관련 기능 ID | 구현 완료 여부 |
| :--- | :--- | :--- | :---: | :--- | :---: |
| 팔로워 목록 조회 | GET | `/users/{id}/followers` |  | MY-006 | ✓ |
| 팔로잉 목록 조회 | GET | `/users/{id}/followings` |  | MY-006 | ✓ |
| 팔로우 | POST | `/users/{id}/followers` | ✓ | FOLLOW-001 | ✓ |
| 팔로우 해제 | DELETE | `/users/{id}/followers` | ✓ | FOLLOW-001 | ✓ |
| 찜 목록 조회 | GET | `/users/{userId}/wishes` | ✓ | MY-006, MY-009 | ✓ |
| 상품 찜 | POST | `/users/{userId}/wishes` | ✓ | MY-009 | ✓ |
| 상품 찜 해제 | DELETE | `/users/{userId}/wishes/{id}` | ✓ | MY-009 | ✓ |

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
| 판매 상품 관리 목록 조회 | GET | `/users/{id}/products` | ✓ | MY-002 | ✓ |
| 상품 기본 정보 저장 | POST | `/products` | ✓ | PROD-001 | ✓ |
| 상품 이미지 업로드 URL 발급 | POST | `/products/{id}/images/upload-url` | ✓ | PROD-001 | ✓ |
| 상품 이미지 등록 | POST | `/products/{id}/images` | ✓ | PROD-001 | ✓ |
| 상품 이미지 수정 | PATCH | `/products/{id}/images/{imageId}` | ✓ | PROD-001 | ✓ |
| 상품 이미지 삭제 | DELETE | `/products/{id}/images/{imageId}` | ✓ | PROD-001 | ✓ |
| 경매 상품 등록 및 경매 전환 | PATCH | `/products/{id}/auction-schedule` | ✓ | PROD-003, PROD-004 | ✓ |
| 판매 가격 설정 및 상시 판매 등록 | PATCH | `/products/{id}/status` | ✓ | PROD-002, PROD-004, PROD-005 | ✓ |
| 상품 상세 조회 | GET | `/products/{id}` |  | PROD-006 | ✓ |
| 상품 정보 수정 | PATCH | `/products/{id}` | ✓ | PROD-007 | ✓ |
| 상품 삭제 | DELETE | `/products/{id}` | ✓ | PROD-007 | ✓ |
| AI 가격 추천 트리거 | POST | `/products/price-estimates` | ✓ | PROD-011, PROD-012 | ✓ |
| 카테고리 전체 목록 조회 | GET | `/categories` |  | PROD-001 | ✓ |
| 브랜드 전체 목록 조회 | GET | `/brands` |  | PROD-001 | ✓ |

> `GET /products`는 `sellerId`로 판매자별 필터링 가능(비회원 조회 가능). 필터: `categoryIds`, `conditionGrade`, `saleType`, `minPrice`/`maxPrice`, `sort`.
>
> 이미지 `role`(`FRONT`/`BACK`/`ADDITIONAL`, 등록 시 필수)은 상품당 `FRONT`·`BACK` 각 1장만 허용(중복 시 400). 전체 상한 10장.
>
> 상세 응답의 `aiQualityAnalysis`는 등록/수정 시 보낸 `aiQualityFindings`(사용자가 인정한 하자 — `photoRole`/`description`/`box`)를 사진별로 묶어 그대로 반환한다. `status`는 `NOT_REQUESTED`/`NO_FINDINGS`/`COMPLETED` 3종뿐(진행 중·실패는 BE가 관측 불가). `aiQualityFindings`는 `defects`처럼 null=미반영, 값 전달 시 전체 교체.
>
> `PATCH /products/{id}`의 `price`는 상시 판매(`ON_SALE`)에만 적용된다(경매 상품은 400 — 경매 시작가는 `/auction-schedule`에서 다룬다).
>
> `POST /products/price-estimates`는 AI 가격 추천 트리거. 상품 생성 전에도 호출 가능하며 `jobId`만 반환한다 — 결과는 FE가 `GET /ai/jobs/{jobId}`로 직접 폴링한다.

## 라이브 / 채팅 (Lives)

| 이름 | Method | Endpoint | 인증 필요 여부 | 관련 기능 ID | 구현 완료 여부 |
| :--- | :--- | :--- | :---: | :--- | :---: |
| 라이브 목록 조회 | GET | `/lives` |  | LIVE-005, MY-005 | ✓ |
| 라이브 예약 개설 | POST | `/lives/schedule` | ✓ | LIVE-001 | ✓ |
| 라이브 즉시 개설 | POST | `/lives` | ✓ | LIVE-002 | ✓ |
| 라이브 상세 조회 | GET | `/lives/{liveId}` |  | LIVE-005 | ✓ |
| 현재 소개 상품 변경 | PATCH | `/lives/{liveId}/current-product` | ✓ | LIVE-004 | ✓ |
| 라이브 상태 변경 (종료 등) | PATCH | `/lives/{liveId}/status` | ✓ | LIVE-002, LIVE-004 | ✓ |
| 라이브 상품 목록 조회 | GET | `/lives/{liveId}/products` |  | LIVE-003 | ✓ |
| 라이브 상품 등록 | POST | `/lives/{liveId}/products` | ✓ | LIVE-003, LIVE-006 | ✓ |
| 라이브 상품 해제 | DELETE | `/lives/{liveId}/products/{productId}` | ✓ | LIVE-003 | ✓ |
| 영상 접속 토큰 발급 | POST | `/lives/{liveId}/video-token` |  | LIVE-004 | ✓ |
| 채팅 메시지 목록 조회 | GET | `/lives/{liveId}/chat-messages` |  | CHAT-001 | ✓ |
| 방송 종료 요약 조회 | GET | `/lives/{liveId}/summary` | ✓ | LIVE-006 | ✓ |
| 방송별 유찰 상품 목록 조회 | GET | `/lives/{liveId}/unsold-products` | ✓ | LIVE-006 | ✓ |

> `GET /lives`는 `hostId`로 필터링 가능 — 본인이면 종료·취소 포함 전체, 아니면 예정·진행 중만.
>
> 채팅 전송은 REST가 아닌 **STOMP WebSocket**. 방송 종료는 `PATCH .../status` body `{ "status": "ENDED" }`(호스트만, 멱등 아님).
>
> `summary`/`unsold-products`는 **호스트 본인만** 조회(판매 실적이라 비공개). `summary.results`는 편성 상품 전체 기준 — 낙찰(`AUCTION`)과 방송 중 정찰가 즉시구매(`DIRECT_SALE`)를 함께 집계하며, 안 팔린 상품에도 편성 시점 `saleType`/`registeredPrice`가 채워진다.

## 경매 / 입찰 (Auctions)

| 이름 | Method | Endpoint | 인증 필요 여부 | 관련 기능 ID | 구현 완료 여부 |
| :--- | :--- | :--- | :---: | :--- | :---: |
| 경매 조건 설정 | POST | `/lives/{liveId}/auctions` | ✓ | AUCT-001 | ✓ |
| 현재 경매 현황 조회 | GET | `/lives/{liveId}/auctions/current` |  | AUCT-001, AUCT-011 | ✓ |
| 경매 시작 | POST | `/auctions/{auctionId}/start` | ✓ | AUCT-002 | ✓ |
| 입찰 | POST | `/auctions/{auctionId}/bids` | ✓ | AUCT-003~010 | ✓ |
| 입찰 내역 조회 | GET | `/auctions/{auctionId}/bids` |  | AUCT-003~006 | ✓ |
| 낙찰 결과 조회 | GET | `/auctions/{auctionId}/winner` |  | AUCT-012, AUCT-013 | ✓ |

> 조건 설정 요청 바디: `{ productId, startPrice, bidUnit, durationSeconds }` → `status: "READY"` 반환. 진행 동작(시작/입찰/입찰내역/결과)은 `liveId` 없이 `/auctions/{auctionId}/...`로 처리한다.
>
> `current`는 라이브 진입 시 경매 패널 초기화용(RUNNING이 READY보다 우선, 둘 다 없으면 `data: null`). 변화는 `/topic/lives/{liveId}/auctions` STOMP 구독으로 받는다.
>
> **미구현**: `/products/{id}/auction`, `/auctions/{id}`(auctionId 단독 상세) — 상품 상세 페이지처럼 라이브 밖에서 경매 중인 상품의 현재가·종료 시각을 볼 방법이 없다.

## 포인트 / 출금 (Point)

| 이름 | Method | Endpoint | 인증 필요 여부 | 관련 기능 ID | 구현 완료 여부 |
| :--- | :--- | :--- | :---: | :--- | :---: |
| 잔액 조회 | GET | `/users/{id}/points` | ✓ | POINT-002, MY-007 | ✓ |
| 사용 내역 조회 | GET | `/users/{id}/points/logs` | ✓ | POINT-002, MY-007 | ✓ |
| 포인트 충전 준비 | POST | `/users/{id}/points/charges/ready` | ✓ | POINT-001, MY-007 | ✓ |
| 포인트 충전 승인 | POST | `/users/{id}/points/charges/confirm` | ✓ | POINT-001, MY-007 | ✓ |
| 출금 신청 | POST | `/users/{id}/withdrawals` | ✓ | POINT-004, MY-007 | ✓ |
| 출금 내역 조회 | GET | `/users/{id}/withdrawals` | ✓ | POINT-004, MY-007 | ✓ |

> 포인트 충전은 토스페이먼츠 결제위젯 연동 — `ready`로 주문정보 발급, 결제 성공 후 `paymentKey`/`orderId`/`amount`로 `confirm` 호출 시 적립. 출금은 신청까지만 처리(완료는 DB 직접 조작).

## 주문 / 배송 / 환불 (Orders)

| 이름 | Method | Endpoint | 인증 필요 여부 | 관련 기능 ID | 구현 완료 여부 |
| :--- | :--- | :--- | :---: | :--- | :---: |
| 주문 목록 조회 | GET | `/users/{id}/orders` | ✓ | MY-003, MY-004 | ✓ |
| 상시 판매 주문 생성 | POST | `/orders` | ✓ | SALE-001, SALE-002 | ✓ |
| 주문 상세 조회 | GET | `/orders/{orderId}` | ✓ | MY-003 | ✓ |
| 주문 배송지 조회 | GET | `/orders/{orderId}/address` | ✓ | ORDER-001 | ✓ |
| 주문 배송지 등록, 수정 | PATCH | `/orders/{orderId}/address` | ✓ | ORDER-001 | ✓ |
| 구매 확정 처리 | POST | `/orders/{orderId}/confirmation` | ✓ | ORDER-002, ORDER-003 | ✓ |
| 송장 정보 조회 | GET | `/orders/{orderId}/shipment` | ✓ | SHIP-002 | ✓ |
| 송장 정보 등록 | POST | `/orders/{orderId}/shipment` | ✓ | SHIP-001 | ✓ |
| 배송 조회 웹훅 수신(내부용) | POST | `/webhooks/delivery` |  | SHIP-002 | ✓ |
| 환불 요청 목록 조회 | GET | `/orders/{id}/refunds` | ✓ | REFUND-001 | ✓ |
| 환불 요청 등록 | POST | `/orders/{id}/refunds` | ✓ | REFUND-001 | ✓ |
| 환불 승인, 거절 처리 | PATCH | `/refunds/{id}` | ✓ | REFUND-002 | ✓ |

> `role`(`BUYER`/`SELLER`, 필수)로 구매/판매 내역을 구분한다. `settledAt`은 `SETTLED`가 아니면 `null`. `refundRequested`(진행 중인 환불 요청 여부)는 판매 대시보드 집계용.
>
> 즉시구매 시 결제액은 구매자 `available` → `tradeEscrow`로 이동한다. 배송완료는 `deliveryapi.co.kr` 웹훅 수신 시 반영(구독 실패 시 등록 즉시 반영 폴백). 배송완료 3일 후 자동 구매확정 → `tradeEscrow`를 판매자 `available`로 정산(`SETTLED`). 경매 낙찰 주문은 범위 밖.
>
> 환불은 **판매자**가 승인/거절한다(운영자 없음). 승인 시 대금이 구매자 `available`로 즉시 환급, 거절 시 이전 상태 유지. `CONFIRMED`/`SETTLED` 이후는 환불 불가.

## AI 가상 시착 (TryOns)

| 이름 | Method | Endpoint | 인증 필요 여부 | 관련 기능 ID | 구현 완료 여부 |
| :--- | :--- | :--- | :---: | :--- | :---: |
| 시착 프로필 사진 업로드 URL 발급 | POST | `/users/{userId}/tryon/upload-url` | ✓ | TRYON-001 | ✓ |
| 시착 프로필 조회 | GET | `/users/{userId}/tryon` | ✓ | TRYON-001, TRYON-002 | ✓ |
| 시착 프로필 등록, 수정 | PUT | `/users/{userId}/tryon` | ✓ | TRYON-001, TRYON-002 | ✓ |
| 시착 프로필 삭제 | DELETE | `/users/{userId}/tryon` | ✓ | TRYON-001 | ✓ |
| 가상 시착 생성 | POST | `/users/{id}/tryons` | ✓ | TRYON-003, TRYON-004 | ✓ |
| 시착 결과 목록 조회 | GET | `/users/{userId}/tryons` | ✓ | TRYON-005 | ✓ |
| 시착 결과 상세 조회 | GET | `/users/{userId}/tryons/{id}` | ✓ | TRYON-005 | ✓ |
| 시착 결과 삭제 | DELETE | `/users/{userId}/tryons/{id}` | ✓ | TRYON-005 | ✓ |

> 시착 결과 응답에는 상품의 대분류 카테고리(`categoryId`/`categoryName`, depth=2 기준)가 포함된다. 못 찾으면 둘 다 `null`.

## 홈 (Home)

| 이름 | Method | Endpoint | 인증 필요 여부 | 관련 기능 ID | 구현 완료 여부 |
| :--- | :--- | :--- | :---: | :--- | :---: |
| 홈 콘텐츠 조회 | GET | `/home` |  | HOME-001 | ✓ |
| 팔로잉 콘텐츠 조회 | GET | `/home/following` | ✓ | HOME-002 | ✓ |