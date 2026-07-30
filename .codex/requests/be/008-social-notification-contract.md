# 소셜/알림 도메인 API 계약 보완 요청

## 요청 파트 / 대상 파트

- 요청: FE
- 대상: BE

## 배경/이유

FE 검색, 상품 상세, 마이페이지, 알림 화면에서 팔로우/찜/알림 상태가 필요하다. 현재 BE에는 찜과 알림 일부 API가 구현되어 있지만 팔로우 API와 공개 목록 응답의 사용자 액션 상태가 부족하다.

## 현재 BE에서 사용할 수 있는 계약

| 기능 | Method | Endpoint | 인증 | 현재 BE 상태 |
| --- | --- | --- | --- | --- |
| 상품 찜 등록 | `POST` | `/api/users/{userId}/wishes` | 필요 | 구현됨 |
| 상품 찜 해제 | `DELETE` | `/api/users/{userId}/wishes/{productId}` | 필요 | 구현됨 |
| 상품 찜 목록 | `GET` | `/api/users/{userId}/wishes` | 필요 | 구현됨 |
| 알림 목록 | `GET` | `/api/users/{userId}/alerts` | 필요 | 구현됨 |
| 알림 단건 읽음 | `PATCH` | `/api/users/{userId}/alerts/{id}` | 필요 | 구현됨 |
| 알림 전체 읽음 | `PATCH` | `/api/users/{userId}/alerts/read-all` | 필요 | 구현됨 |

공통 주의:

- `{userId}`는 인증 사용자 ID와 같아야 하며 다르면 403을 반환한다.
- 목록 응답은 BE `PageResponse<T>` 구조다.
- 찜 해제 path의 `{productId}`는 찜 row ID가 아니라 상품 ID다.

## 추가 구현 요청

### 1. 팔로우/언팔로우 API

FE 검색 결과와 판매자 카드에서 회원 팔로우 상태를 표시하고 토글해야 한다.

요청 endpoint 후보:

```http
POST /api/users/{targetUserId}/followers
DELETE /api/users/{targetUserId}/followers
GET /api/users/{userId}/followers
GET /api/users/{userId}/followings
```

요청 사항:

- 인증 사용자와 대상 사용자 관계로 팔로우를 생성/해제한다.
- 자기 자신 팔로우 가능 여부와 오류 코드를 확정한다.
- 중복 팔로우/미팔로우 해제 요청의 HTTP status와 오류 코드를 확정한다.
- 목록 응답에 `id`, `nickname`, `profileImageUrl`, `followerCount`, `productCount`, `isFollowing`을 포함한다.

### 2. 공개 목록/검색 응답의 사용자 액션 상태

상품 목록, 상품 상세, 홈, 검색 결과에서 FE가 별도 찜 목록을 매번 조합하지 않도록 다음 필드를 응답에 포함해 달라.

| 응답 | 요청 필드 |
| --- | --- |
| 상품 카드/상세 | `isWished` |
| 회원 카드 | `isFollowing` |
| 판매자 요약 | `followerCount`, `productCount` |

비회원 요청 정책:

- `isWished`와 `isFollowing`을 `false`로 줄지 `null`로 줄지 endpoint별로 문서화한다.
- FE는 `null`이면 비로그인/확인 불가 상태로 처리한다.

### 3. 알림 생성 이벤트와 ref 이동 계약

현재 알림 조회/읽음 API는 있으나, 어떤 이벤트가 어떤 `type`, `refType`, `refId`로 생성되는지 FE가 알 수 없다.

요청:

- 알림 `type` enum 전체 목록을 문서화한다. 예: `AUCTION_WON`, `BID_OUTBID`, `ORDER_CREATED`, `SHIPMENT_STARTED`, `LIVE_STARTED`.
- `refType`별 FE 이동 경로를 확정할 수 있도록 `refType` enum과 `refId` 의미를 문서화한다.
- 알림 보관 기간, 읽음 처리 후 목록 유지 여부, `unreadOnly=true`의 정렬 정책을 명시한다.

## FE 관련 파일

- `FE/src/domains/product/api/productApi.ts`
- `FE/src/domains/search/pages/SearchResultsPage.vue`
- `FE/src/domains/home/api/homeViewApi.ts`
- `FE/docs/frontend/api/api-index.md`
- `FE/docs/frontend/decisions/open-questions.md`
