# BE 요청 문서 인덱스

## 요청 파트 / 대상 파트

- 요청: FE
- 대상: BE

## 목적

2026-07-31 기준 BE 최신 구현을 확인한 뒤, FE API 연동에 필요한 요청 문서를 도메인별로 정리한다. 실제 구현이 확인된 항목은 FE adapter에서 바로 사용할 수 있고, 미구현/부족 항목은 각 요청 문서 기준으로 BE 보완을 요청한다.

## 문서 목록

| 번호 | 문서 | 도메인 | 상태 |
| --- | --- | --- | --- |
| 001 | `001-auth-contract.md` | 인증 | 이메일 auth 구현됨, SSO와 `GET /api/me` 필요 |
| 002 | `002-onboarding-contract.md` | 온보딩 | `/api/me/**` 온보딩 API 미구현 |
| 003 | `003-business-contract.md` | 사업자 인증 | 미구현 |
| 004 | `004-home-contract.md` | 홈 | 대부분 구현됨, `hostId` 등 일부 보강 필요 |
| 005 | `005-search-contract.md` | 검색 | 미구현 |
| 006 | `006-product-contract.md` | 상품 | 기본 API 구현됨, 목록/상세 필드와 query 보강 필요 |
| 007 | `007-live-tryon-contract.md` | 라이브/AI 시착 | 라이브 기본 구현됨, 영상/경매 진행/시착 생성 보강 필요 |
| 008 | `008-social-notification-contract.md` | 소셜/알림 | 찜/알림 일부 구현됨, 팔로우와 액션 상태 보강 필요 |
| 009 | `009-auction-chat-contract.md` | 경매/채팅 | 채팅/반응 일부 구현됨, 경매 진행 계약 필요 |
| 010 | `010-commerce-wallet-contract.md` | 주문/배송/환불/포인트 | 미구현 |
| 011 | `011-user-mypage-contract.md` | 회원/마이페이지 | 미구현 |

## FE 우선 연동 가능 순서

1. Auth 이메일 로그인/회원가입
2. Home
3. Product master/등록/이미지/상세 일부
4. Wish
5. Live 목록/상세 일부
6. Notification 목록/읽음
7. Chat 이력/STOMP

## 공통 주의

- BE `PageResponse<T>`는 `content/page/size/totalElements/totalPages/hasNext` 구조다. FE 공통 타입의 `items/meta`로 adapter 변환이 필요하다.
- FE axios `baseURL`은 `/api`이므로 FE API 함수에서는 `/auth/...`, `/home`처럼 `/api`를 제외하고 호출한다.
- 비회원 요청에서 사용자별 상태(`isWished`, `isFollowing`)가 `false`인지 `null`인지 endpoint별 문서화가 필요하다.
