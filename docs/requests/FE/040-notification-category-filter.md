# 040 알림 `category` 쿼리 파라미터 반영

- **작성자 파트**: BE (서윤) / **대상 파트**: FE
- **작성일**: 2026-08-07
- **원 요청**: `docs/requests/BE/004-social-notification-contract.md` §3.4(카테고리별 bulk read),
  §6(카테고리 기준을 BE enum으로 둘지 FE 규칙으로 둘지)

알림센터 탭(라이브/경매/거래/배송/포인트) 분류를 FE가 `type`/`refType` 문자열 포함 검사로 하던 걸
BE가 `category` 쿼리 파라미터로 직접 지원하도록 바꿨습니다.

## 1. `GET /api/users/{userId}/alerts`에 `category` 파라미터 추가

```
GET /api/users/{userId}/alerts?category=SHIPPING&unreadOnly=true&page=0&size=20
```

- 선택 파라미터입니다. 생략하면 지금처럼 전체 알림을 조회합니다(기존 동작 그대로, 하위 호환).
- 값은 다섯 개 중 하나: `LIVE` / `AUCTION` / `SHIPPING` / `POINT` / `TRADE`.
- 다섯 개 밖의 값을 보내면 400(`INVALID_INPUT_VALUE`)입니다.

## 2. `PATCH /api/users/{userId}/alerts/read-all`에도 같은 파라미터 추가

```
PATCH /api/users/{userId}/alerts/read-all?category=POINT
```

- 마찬가지로 선택입니다. 생략하면 지금처럼 전체 읽음 처리입니다.
- 탭별 "모두 읽음"에서 알림 ID마다 단건 읽음 API를 여러 번 호출하던 걸 이 호출 하나로 대체하시면
  됩니다.

## 3. `category` ↔ `type` 매핑

| `category` | 매핑되는 `type` |
| --- | --- |
| `LIVE` | `LIVE_REMINDER`, `LIVE_STARTED` |
| `AUCTION` | `AUCTION_OUTBID`, `AUCTION_WON` |
| `SHIPPING` | `SHIPMENT_STARTED`, `SHIPMENT_COMPLETED` |
| `POINT` | `POINT_CHARGED`, `POINT_REFUNDED`, `WITHDRAW_COMPLETED` |
| `TRADE` | 위에 안 걸리는 나머지(현재는 `ORDER_PAID`) — catch-all |

- 지금 FE가 쓰는 임시 분류 표(004 §3.1 — `type/refType`에 `SHIP`/`POINT`/`WITHDRAW` 등 포함되는지
  검사)와 결과가 똑같이 나오도록 맞췄습니다. 이 파라미터를 쓰기 시작하면 그 문자열 포함 검사 로직은
  걷어내셔도 됩니다.
- `TRADE`는 고정 목록이 아니라 "나머지 네 카테고리에 안 걸리는 전부"라서, 앞으로 BE가 새 `type`을
  추가했는데 이 표에 반영을 깜빡해도 그 알림이 사라지거나 에러 나지 않고 `TRADE`로 자동 분류됩니다.

## 4. unread count 전용 API도 같이 반영(004 §3.3)

```
GET /api/users/{userId}/alerts/unread-count?category=POINT
```

- `category`는 선택입니다. 생략하면 전체 안 읽은 알림 수를 반환합니다.
- 응답: `{ "unreadCount": 4 }`
- 헤더 unread badge는 계속 지금 방식(목록 API의 `totalElements`)을 써도 되고, 이 API로 바꾸면
  목록을 안 불러오고 카운트만 받을 수 있습니다. 탭별 배지가 필요하면 `category`를 붙여서 쓰시면
  됩니다.

## 참고

- 설계: `docs/plans/BE/SY041-notification-category-filter.md`
- 계약 원본: `docs/requests/BE/004-social-notification-contract.md` §3.2 "2026-08-07 확정"
