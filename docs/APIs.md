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

> 공개 프로필은 비회원도 조회 가능하며
> `id/nickname/profileImageUrl/description/coverImageUrl/followerCount/followingCount/productCount/
> liveCount/isFollowing/businessVerified`를 내려준다. 소개글은 `PATCH /users/{id}/bio`(선택 입력,
> 부분 수정 아님 — 값을 안 보내면 지워짐)로 등록·수정한다.
>
> 프로필/커버 이미지는 상품 이미지·시착 프로필 사진과 동일한 presigned 2단계로 업로드한다:
> 1) `POST .../profile-image/upload-url`(또는 `cover-image/upload-url`)로 key·업로드용 URL을 발급받는다(jpeg/png/webp만, 5분 만료)
> 2) 받은 `uploadUrl`로 브라우저가 파일을 직접 PUT한다.
> 3) `PUT .../profile-image`(또는 `cover-image`)에 `{key}`를 보내 확정하면 최종 공개 URL이
> 저장된다(업로드 미확인·10MB 초과면 400). `DELETE .../profile-image`(또는 `cover-image`)로
> 지울 수 있다 — 단 S3의 이전 객체 자체는 지우지 않고 참조만 비운다(공개 버킷의 비민감 이미지라
> orphan을 남겨도 된다고 판단).

## 사업자 (Businesses)

| 이름 | Method | Endpoint | 인증 필요 여부 | 관련 기능 ID | 구현 완료 여부 |
| :--- | :--- | :--- | :---: | :--- | :---: |
| 사업자등록증 이미지 업로드 URL 발급 | POST | `/users/{userId}/business/upload-url` | ✓ | BIZ-001 | ✓ |
| 사업자 인증 상태 조회 | GET | `/users/{id}/business` | ✓ | MY-008 | ✓ |
| 사업자 정보 등록 | POST | `/users/{id}/business` | ✓ | BIZ-001 | ✓ |
| 세금계산서 발행 요청 | POST | `/orders/{orderId}/invoices` | ✓ | BIZ-002 | ✓ |
| 세금계산서 조회 | GET | `/orders/{orderId}/invoices` | ✓ | BIZ-002 | ✓ |

> 사업자 정보 수정(PATCH)은 구현하지 않는다 — 제출은 등록(POST)이 재제출까지 겸한다(REJECTED 상태에서만).

## 검색 / 추천 (Discovery)

| 이름 | Method | Endpoint | 인증 필요 여부 | 관련 기능 ID | 구현 완료 여부 |
| :--- | :--- | :--- | :---: | :--- | :---: |
| 통합 검색 (상품, 라이브, 회원) | GET | `/search` |  | SEARCH-001, SEARCH-002 |  |
| 개인화 추천 조회 | GET | `/users/{id}/picks` |  | REC-001 |  |

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
| 카테고리 전체 목록 조회 | GET | `/categories` |  | PROD-001 | ✓ |
| 브랜드 전체 목록 조회 | GET | `/brands` |  | PROD-001 | ✓ |

> 상품 목록 조회(`GET /products`)는 `sellerId` 쿼리 파라미터로 특정 판매자의 상품만 필터링할 수 있다(공개 프로필 판매 상품 목록). 비회원도 조회 가능하다.
> 상품 목록 조회 필터: `categoryIds`(복수), `conditionGrade`(복수), `saleType`(`DIRECT_SALE`/`AUCTION`), `minPrice`, `maxPrice`, `sort`(`LATEST`(기본값)/`PRICE_ASC`/`PRICE_DESC`).
>
> 상품 이미지는 `role`(`FRONT`/`BACK`/`ADDITIONAL`, 등록 시 필수)로 구분한다. 상품당 `FRONT`·`BACK`은 각 1장만 허용하며 중복 등록 시 400(`PRODUCT_IMAGE_ROLE_ALREADY_EXISTS`)이다. `ADDITIONAL`을 포함한 전체 이미지 상한은 여전히 10장이다. 이 컬럼이 생기기 전에 등록된 기존 이미지는 전부 `ADDITIONAL`로 채워져 있다.
>
> 상품 상세 조회(`GET /products/{id}`) 응답에는 `aiQualityAnalysis`(AI 품질 분석) 객체가 포함된다. 등록(`POST /products`) 요청의 `aiQualityFindings`(판매자가 "하자로 인정"으로 확정한 후보 목록 — `photoRole`/`description`/`box`, `FRONT`·`BACK` 사진에만 등록 가능)를 저장했다가 사진별로 묶어 그대로 돌려준다. `status`는 `NOT_REQUESTED`(등록 시 findings 없음)/`NO_FINDINGS`(요청은 있었으나 0건)/`COMPLETED`(1건 이상) 세 가지뿐이다 — AI 분석이 진행 중이거나 실패한 상태는 BE로 전달되지 않는 시점의 데이터라 관측할 수 없다(FE가 AI 게이트웨이를 직접 폴링해 그 상태를 판단한다). 수정(`PATCH /products/{id}`)에는 아직 `aiQualityFindings`가 없다 — DRAFT 우선 생성 후 PATCH로 최종 제출하는 상품은 이 값이 저장되지 않는다(`docs/requests/BE/046-product-update-quality-findings.md`).
>
> 상품 정보 수정(`PATCH /products/{id}`)의 `price`(선택)로 상시 판매(`ON_SALE`) 중인 상품의 가격을 바로 바꿀 수 있다. 경매 상품(`saleType=AUCTION`)에 보내면 400(`INVALID_PRODUCT_STATE`) — 경매 시작가는 별도 API(`/products/{id}/auction-schedule`)로 다룬다.

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

> 라이브 목록 조회는 `hostId` 쿼리 파라미터로 특정 호스트만 필터링할 수 있다(MY-005, 마이페이지 라이브 관리). 인증된 본인의 `hostId`를 넘기면 종료·취소된 방송까지 포함해 전체 상태를 볼 수 있고, 그 외에는 예정·진행 중만 보인다.
>
> 채팅 메시지 전송은 REST API가 아닌 **STOMP WebSocket**으로 처리한다(`001-live-stomp-contract.md` 참고).
> 라이브 상태 변경에서 방송을 종료할 때는 body `{ "status": "ENDED" }`를 전달한다. 호스트 본인만 허용(아니면 403), 이미 종료·취소된 방송은 400(멱등 아님).

## 경매 / 입찰 (Auctions)

| 이름 | Method | Endpoint | 인증 필요 여부 | 관련 기능 ID | 구현 완료 여부 |
| :--- | :--- | :--- | :---: | :--- | :---: |
| 경매 조건 설정 | POST | `/lives/{liveId}/auctions` | ✓ | AUCT-001 | ✓ |
| 경매 시작 | POST | `/lives/{liveId}/auctions/{auctionId}/start` | ✓ | AUCT-002 |  |
| 경매 조건 조회 | GET | `/products/{id}/auction` |  | AUCT-001 |  |
| 경매 상세 조회 | GET | `/auctions/{id}` |  | AUCT-011 |  |
| 입찰 내역 조회 | GET | `/auctions/{id}/bids` |  | AUCT-003~006 |  |
| 입찰 | POST | `/auctions/{id}/bids` | ✓ | AUCT-003~010 |  |
| 낙찰 결과 조회 | GET | `/auctions/{id}/winner` |  | AUCT-012, AUCT-013 |  |

> 경매 조건 설정 요청 바디: `{ productId, startPrice, bidUnit, durationSeconds }` → 생성된 경매(`status: "READY"`) 반환.
> 생성(조건 설정)과 시작(`/start`)은 별개 API로 분리한다. 경매 시작 API는 아직 미구현.

## 포인트 / 출금 (Point)

| 이름 | Method | Endpoint | 인증 필요 여부 | 관련 기능 ID | 구현 완료 여부 |
| :--- | :--- | :--- | :---: | :--- | :---: |
| 잔액 조회 | GET | `/users/{id}/points` | ✓ | POINT-002, MY-007 | ✓ |
| 사용 내역 조회 | GET | `/users/{id}/points/logs` | ✓ | POINT-002, MY-007 | ✓ |
| 포인트 충전 준비 | POST | `/users/{id}/points/charges/ready` | ✓ | POINT-001, MY-007 | ✓ |
| 포인트 충전 승인 | POST | `/users/{id}/points/charges/confirm` | ✓ | POINT-001, MY-007 | ✓ |
| 출금 신청 | POST | `/users/{id}/withdrawals` | ✓ | POINT-004, MY-007 | ✓ |
| 출금 내역 조회 | GET | `/users/{id}/withdrawals` | ✓ | POINT-004, MY-007 | ✓ |

> 포인트 충전은 토스페이먼츠 결제위젯(테스트 키) 연동이다. `ready`로 주문번호(`orderId`)와 위젯 클라이언트 키를 발급받아 FE가 위젯을 띄우고, 결제 성공 리다이렉트에서 받은 `paymentKey`/`orderId`/`amount`로 `confirm`을 호출하면 토스 승인 후 포인트가 적립된다. 계약은 `docs/requests/FE/026-toss-payments-charge-widget.md` 참고. 출금은 신청까지만 처리하며(관리자 승인 체계 없음), 완료 처리는 DB 직접 조작으로만 가능하다.

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

> 주문 목록 조회는 `role` 쿼리 파라미터(`BUYER`/`SELLER`, 필수)로 구매 내역(MY-003)/판매·정산 내역(MY-004)을 구분한다. 정산 완료 여부는 주문 상태가 `SETTLED`인지로 판단하며, 정산액은 수수료 없이 주문 금액 그대로다.
>
> 상시 판매 즉시구매(`POST /orders`)로 주문을 생성하면 결제 금액이 구매자 포인트 `available`에서 `tradeEscrow`(거래 대금 보관)로 옮겨진다. 송장 등록(`POST /orders/{orderId}/shipment`)은 택배사 코드를 고정 목록(`CourierCode`)에서만 받으며, `deliveryapi.co.kr` 웹훅 구독에 성공하면 배송완료(`DELIVERED`)는 그 웹훅(`POST /webhooks/delivery`, 내부용·JWT 인증 아님·서명 검증)이 왔을 때만 반영된다. 구독에 실패하면(자격증명 미설정 등) 등록 즉시 배송완료로 처리하는 폴백을 쓴다. 배송완료 3일 뒤로 자동 구매 확정 시각을 계산해 둔다. 구매 확정(`POST /orders/{orderId}/confirmation`)은 수동 호출 또는 3일 경과 시 스케줄러가 자동으로 처리하며, `tradeEscrow`를 판매자 `available`로 정산하고 주문 상태를 `SETTLED`로 바꾼다(거래 완료). 경매 낙찰 주문(AUCT 연동)은 아직 범위 밖이다.
>
> 환불(REFUND-001/002)은 **판매자**가 승인/거절한다(이 프로젝트엔 운영자 역할이 없어 사용자 지시로 결정 — `docs/plans/BE/SY037-refund.md` 참고). 구매자가 `PAID`/`SHIPPING`/`DELIVERED` 상태의 주문에 사유(`NOT_AS_DESCRIBED`/`UNDISCLOSED_DEFECT`/`NOT_SHIPPED`/`DUPLICATE_PAYMENT`/`SYSTEM_ERROR`)와 상세 사유를 담아 요청하면, 판매자가 승인/거절한다. 승인되면 보관 중이던 대금이 판매자에게 정산되지 않고 구매자 `available` 포인트로 바로 환급되며 주문이 `REFUNDED`로 바뀐다. 거절되면 주문은 요청 이전 상태 그대로 이어간다(재요청 가능). 이미 구매 확정·정산된 주문(`CONFIRMED`/`SETTLED`)은 환불 대상이 아니다.

## AI 가상 시착 (TryOns)

| 이름 | Method | Endpoint | 인증 필요 여부 | 관련 기능 ID | 구현 완료 여부 |
| :--- | :--- | :--- | :---: | :--- | :---: |
| 시착 프로필 사진 업로드 URL 발급 | POST | `/users/{userId}/tryon/upload-url` | ✓ | TRYON-001 | ✓ |
| 시착 프로필 조회 | GET | `/users/{userId}/tryon` | ✓ | TRYON-001, TRYON-002 | ✓ |
| 시착 프로필 등록, 수정 | PUT | `/users/{userId}/tryon` | ✓ | TRYON-001, TRYON-002 | ✓ |
| 시착 프로필 삭제 | DELETE | `/users/{userId}/tryon` | ✓ | TRYON-001 | ✓ |
| 가상 시착 생성 | POST | `/users/{id}/tryons` | ✓ | TRYON-003, TRYON-004 |  |
| 시착 결과 목록 조회 | GET | `/users/{userId}/tryons` | ✓ | TRYON-005 | ✓ |
| 시착 결과 상세 조회 | GET | `/users/{userId}/tryons/{id}` | ✓ | TRYON-005 | ✓ |
| 시착 결과 삭제 | DELETE | `/users/{userId}/tryons/{id}` | ✓ | TRYON-005 | ✓ |

## 홈 (Home)

| 이름 | Method | Endpoint | 인증 필요 여부 | 관련 기능 ID | 구현 완료 여부 |
| :--- | :--- | :--- | :---: | :--- | :---: |
| 홈 콘텐츠 조회 | GET | `/home` |  | HOME-001 | ✓ |
| 팔로잉 콘텐츠 조회 | GET | `/home/following` | ✓ | HOME-002 | ✓ |