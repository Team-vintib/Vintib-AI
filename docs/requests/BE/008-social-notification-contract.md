# 008 Social/Notification API 요청

## 1. 요청 개요

- 요청 파트: FE
- 대상 파트: BE
- 요청 목적: 찜, 팔로우, 알림 API의 FE 연동 상태와 남은 계약 요청을 정리한다.
- 우선순위: P1
- 시연 필수 여부: 상품 상세 찜, 팔로우, 알림센터는 현재 실제 API로 시연 가능.

## 2. 현재 연동 상태

- 연동 완료 API
  - `POST /api/users/{userId}/wishes`
  - `DELETE /api/users/{userId}/wishes/{productId}`
  - `GET /api/users/{userId}/alerts?unreadOnly=true&page=0&size=20`
  - `GET /api/users/{userId}/alerts?unreadOnly=true&page=0&size=1`
  - `PATCH /api/users/{userId}/alerts/{id}`
  - `PATCH /api/users/{userId}/alerts/read-all`
  - `POST /api/users/{userId}/followers`
  - `DELETE /api/users/{userId}/followers`
  - `GET /api/users/{userId}/followers`
  - `GET /api/users/{userId}/followings`
- FE 구현 완료 범위
  - 상품 상세 찜 추가/해제
  - 상품 목록/검색/상세에서 `isWished` 표시 후보
  - `/notifications` 읽지 않은 알림 목록, 카테고리 탭, 더보기, 빈 목록/오류/필터 결과 없음 상태
  - 공통 헤더 알림 팝업, 최근 알림, unread badge
  - 단건 읽음 처리, 전체 읽음 처리
- 현재 임시 처리 또는 Mock 사용 여부
  - 팔로우/언팔로우 화면 연결은 아직 없다.
  - 알림 도메인의 FE mock data와 `mock` query는 제거했다.
  - 알림 수동 확인용 DB seed row도 제거했다. 현재 로컬 `notification` 테이블은 비어 있다.
  - unread badge는 `unreadOnly=true` 조회의 `totalElements`를 사용한다.
  - 읽음 처리된 알림은 FE 목록에서 즉시 제거한다.

### 2.1 2026-07-31 알림 API 재검증 결과

- 검증 환경: 로컬 FE `VITE_API_BASE_URL=http://localhost:8080/api`, 로컬 BE/DB
- 검증 계정: `notification.viewer@vintib.local`
- 검증 방식: 임시 `notification` row 1건을 생성해 API 확인 후 삭제
- 결과
  - `POST /api/auth/signin`: 정상
  - `GET /api/users/{userId}/alerts?unreadOnly=true&page=0&size=20`: 정상, PageResponse 수신
  - `PATCH /api/users/{userId}/alerts/{id}`: 정상, `id/isRead` 수신
  - `GET /api/users/{userId}/alerts?unreadOnly=true&page=0&size=20` 재조회: 읽음 처리된 알림 제외 확인
  - `PATCH /api/users/{userId}/alerts/read-all`: 정상, 대상 0건이면 `updatedCount=0`
- 현재 문제
  - 조회/읽음 API는 정상이나, 실제 도메인 이벤트에서 `notification` row를 생성하는 흐름이 확인되지 않아 mock/seed 없이 시연할 알림 데이터가 없다.
  - FE는 특정 탭의 `모두 읽음`을 현재 필터에 보이는 알림 각각에 `PATCH /alerts/{id}`를 호출해 처리한다. BE에는 타입/카테고리별 bulk read API가 없다.

## 3. 추가 구현 요청

### 3.1 알림 type/ref 문서화

- Method / Endpoint
  - `GET /api/users/{userId}/alerts`
  - `PATCH /api/users/{userId}/alerts/read-all`
  - `PATCH /api/users/{userId}/alerts/{id}`
- 요청 목적: 알림 목록에서 아이콘, 문구, 이동 대상을 안정적으로 분기한다.
- FE 사용처: 알림센터
- 요청 데이터
  - Header: `Authorization: Bearer {accessToken}`
- 응답 데이터
  - `id`, `type`, `title`, `body`, `isRead`, `refType`, `refId`, `createdAt`
- 응답 예시

```json
{
  "success": true,
  "data": {
    "content": [
      {
        "id": 1,
        "type": "BID_OUTBID",
        "title": "상위 입찰이 발생했습니다",
        "body": "다른 사용자가 더 높은 금액으로 입찰했습니다.",
        "isRead": false,
        "refType": "AUCTION",
        "refId": 1,
        "createdAt": "2026-07-31T12:00:00"
      }
    ]
  },
  "error": null
}
```

확정 요청:

- `type` enum 전체 목록과 각 값의 발생 이벤트를 문서화해 주세요.
- `refType` enum 전체 목록과 `refId`가 가리키는 테이블/리소스를 문서화해 주세요.
- `refType/refId`가 없는 알림이 존재할 수 있는지, 존재한다면 FE가 이동 없이 읽음 처리만 하면 되는지 확정해 주세요.
- 같은 알림 `type`에서 `refType`이 여러 개 나올 수 있는지 확정해 주세요.

FE 현재 임시 분류:

| FE 카테고리 | 현재 분류 기준 |
| --- | --- |
| 라이브 | `type/refType`에 `LIVE` 또는 `BROADCAST` 포함 |
| 경매 | `type/refType`에 `AUCTION` 또는 `BID` 포함 |
| 배송 | `type/refType`에 `SHIP`, `SHIPMENT`, `SHIPPING`, `DELIVERY` 포함 |
| 포인트 | `type/refType`에 `POINT`, `WALLET`, `WITHDRAW` 포함 |
| 거래 | 위 기준에 걸리지 않는 알림 |

FE 현재 임시 이동:

| refType | 이동 |
| --- | --- |
| `LIVE` | `/lives/{refId}` |
| `PRODUCT` | `/products/{refId}` |
| `POINT`, `WALLET` | `/points` |
| `ORDER`, `SHIPMENT`, `SHIPPING` | `/my?section=orders` |
| `AUCTION` | `/my?section=auctions` |
| 기타/null | 이동하지 않고 알림센터에 머묾 |

### 3.2 실제 알림 생성 이벤트 연결

- Method / Endpoint: 내부 도메인 이벤트 또는 서비스 호출
- 요청 목적: FE가 mock 없이 실제 DB/API로만 알림센터를 확인할 수 있도록 주요 도메인 이벤트에서 `notification` row가 생성되어야 한다.
- FE 사용처: 알림센터, 공통 헤더 알림 팝업
- 요청 데이터: 해당 없음
- 응답 데이터: 해당 없음

우선 생성 요청 이벤트:

| 이벤트 | 권장 type | 권장 refType/refId |
| --- | --- | --- |
| 팔로우한 판매자 라이브 시작 | `LIVE_STARTED` | `LIVE` / live id |
| 예약 라이브 시작 전 알림 | `LIVE_REMINDER` | `LIVE` / live id |
| 상위 입찰 발생 | `AUCTION_OUTBID` | `AUCTION` / auction id |
| 낙찰 | `AUCTION_WON` | `AUCTION` / auction id |
| 결제 완료 | `ORDER_PAID` | `ORDER` / order id |
| 송장 등록/배송 시작 | `SHIPMENT_STARTED` | `SHIPMENT` / order or shipment id |
| 배송 완료 | `SHIPMENT_COMPLETED` | `SHIPMENT` / order or shipment id |
| 포인트 충전/환불/출금 완료 | `POINT_CHARGED`, `POINT_REFUNDED`, `WITHDRAW_COMPLETED` | `POINT` / point transaction id |

### 3.2.1 예약 라이브 알림 신청과 스케줄러

- Method / Endpoint 제안
  - `POST /api/lives/{liveId}/reminders`
  - `DELETE /api/lives/{liveId}/reminders`
  - `GET /api/lives/{liveId}` 또는 라이브 목록 응답에 `isReminderSet` 포함
- 요청 목적: 사용자가 예정된 라이브에 알림을 신청하고, 라이브 시작 시점 또는 시작 N분 전에 실제 `notification` row가 생성되도록 한다.
- FE 사용처: 라이브 예정 목록/상세의 알림 신청 버튼, 알림센터, 공통 헤더 알림 팝업
- 요청 데이터
  - Header: `Authorization: Bearer {accessToken}`
  - Path: `liveId`
- 응답 데이터 제안
  - `liveId`: number
  - `isReminderSet`: boolean
  - `reminderCount`: number
  - `scheduledAt`: string

응답 예시:

```json
{
  "success": true,
  "data": {
    "liveId": 15,
    "isReminderSet": true,
    "reminderCount": 8,
    "scheduledAt": "2026-07-31T20:00:00"
  },
  "error": null
}
```

BE 구현 요청:

- `live_reminder` 또는 동등한 구독 테이블을 두고 `(user_id, live_id)` 중복 신청을 방지해 주세요.
- 라이브 시작 시점 또는 시작 10분 전 등 정책으로 정한 시점에 스케줄러가 `notification` row를 생성해 주세요.
- 생성 알림의 권장 값은 `type=LIVE_REMINDER`, `refType=LIVE`, `refId={liveId}`입니다.
- 이미 시작했거나 종료된 라이브에는 신청할 수 없는지, 신청 가능하다면 어떤 응답을 줄지 정책을 정해 주세요.
- 스케줄러 재시도나 서버 재기동 시 같은 라이브 알림이 중복 생성되지 않도록 idempotency 기준을 정해 주세요.
- 목록/상세 응답에 `isReminderSet`이 없으면 FE가 버튼의 현재 상태를 표시할 수 없으므로 필드 제공이 필요합니다.

FE 현재 처리 방침:

- 위 API가 없을 때 localStorage/mock 상태로 알림 신청을 흉내 내지 않습니다.
- API가 제공되면 라이브 예정 카드/상세에 신청 토글을 연결하고, 실제 notification 목록에서만 알림 노출을 확인합니다.

### 3.3 unread count 전용 API 검토

- Method / Endpoint 후보
  - `GET /api/users/{userId}/alerts/unread-count`
- 요청 목적: 현재 FE는 `GET /alerts?unreadOnly=true&page=0&size=1`의 `totalElements`로 unread badge를 계산한다. 동작은 가능하지만 헤더 진입마다 목록 API를 2회 호출하므로 전용 count API가 있으면 더 단순하고 가볍다.
- FE 사용처: 공통 헤더 알림 badge, 알림센터 요약
- 응답 데이터 후보
  - `unreadCount`: number

응답 예시:

```json
{
  "success": true,
  "data": {
    "unreadCount": 4
  },
  "error": null
}
```

### 3.4 카테고리/타입별 읽음 처리 API 검토

- Method / Endpoint 후보
  - `PATCH /api/users/{userId}/alerts/read-all?category=POINT`
  - 또는 `PATCH /api/users/{userId}/alerts/read-all` body `{ "refTypes": ["POINT"] }`
- 요청 목적: FE 알림센터는 전체/라이브/경매/거래/배송/포인트 탭을 제공한다. 현재 전체 탭은 기존 `read-all`을 사용하지만, 특정 탭에서는 해당 탭에 보이는 알림 ID마다 단건 읽음 API를 여러 번 호출해야 한다.
- FE 사용처: 알림센터 탭별 `모두 읽음`
- 응답 데이터 후보
  - `updatedCount`: number

응답 예시:

```json
{
  "success": true,
  "data": {
    "updatedCount": 3
  },
  "error": null
}
```

## 4. 기존 API 변경 요청

- 기존 요청·응답에서 변경할 내용
  - `DELETE /api/users/{userId}/wishes/{productId}`에서 path id가 wish row id인지 product id인지 문서화 요청
- 추가할 필드
  - 알림 item의 `refType`, `refId` enum 문서화
  - 가능하면 unread count 전용 응답
  - 가능하면 타입/카테고리별 bulk read 처리
- 변경 영향 범위
  - 찜 해제 API adapter
  - 알림 클릭 이동
  - 헤더 unread badge
  - 알림센터 탭별 모두 읽음

## 5. 보류 또는 시연 제외 범위

- 현재 구현하지 않아도 되는 기능
  - 팔로우/언팔로우 UI가 시연 범위가 아니면 보류 가능
  - 알림 실시간 push는 이번 알림센터 API 연결 범위 밖이면 보류 가능
- 추후 구현 예정 기능
  - 찜 목록 화면
  - 팔로워/팔로잉 목록 화면
  - 알림 실시간 push

## 6. 협의 필요 사항

- FE·BE 간 결정이 필요한 내용
  - wish delete path의 `{productId}` 의미 확정
  - 알림 `type`, `refType` enum 목록
  - 배송 알림의 `refId`가 order id인지 shipment id인지 확정
  - 알림센터 카테고리 기준을 BE enum으로 둘지 FE 분류 규칙으로 둘지 확정
- 아직 확정되지 않은 응답 구조나 정책
  - 실제 알림 생성 이벤트와 중복 알림 방지 정책

## 7. 추가 요청 없음

- 이미 정상 연동된 API
  - 상품 상세 찜 추가
  - 상품 상세 찜 해제
  - 알림 목록 조회
  - 알림 단건 읽음 처리
  - 알림 전체 읽음 처리
  - 팔로우/팔로우 해제
  - 팔로워/팔로잉 목록 조회
- 기존 규격을 유지하면 되는 기능
  - 찜 목록 API endpoint 자체는 BE에 있으나 FE 화면이 없어 미연결
  - 알림 목록/읽음 API endpoint는 현재 규격 유지 시 FE에서 계속 사용 가능
  - 팔로우/팔로잉 목록 API endpoint도 BE에 있으나 FE 화면이 없어 미연결
