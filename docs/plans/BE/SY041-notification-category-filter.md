# SY041 - 알림 category 쿼리 파라미터

## 배경/목표

`docs/requests/BE/004-social-notification-contract.md` §3.3(unread count 전용 API)·
§3.4(카테고리별 bulk read)·§6(카테고리 기준을 BE enum으로 둘지 FE 규칙으로 둘지)를 따로 풀지
않고, `category` 쿼리 파라미터 하나로 묶어서 해결한다. 사용자 승인 완료(2026-08-07).

## 작업 내용

### 1. `NotificationCategory` enum 신설

`com.ssafy.backend.notification.entity.NotificationCategory` — DB 컬럼이 아니라 `Notification.type`
값에서 계산해서 나가는 필터/응답 전용 값이다.

| `category` | 매핑되는 `type` |
| --- | --- |
| `LIVE` | `LIVE_REMINDER`, `LIVE_STARTED` |
| `AUCTION` | `AUCTION_OUTBID`, `AUCTION_WON` |
| `SHIPPING` | `SHIPMENT_STARTED`, `SHIPMENT_COMPLETED` |
| `POINT` | `POINT_CHARGED`, `POINT_REFUNDED`, `WITHDRAW_COMPLETED` |
| `TRADE` | 위에 안 걸리는 나머지(현재는 `ORDER_PAID`) — catch-all, 고정 목록 없음 |

- `TRADE`는 나머지 4개 카테고리의 type 합집합을 **제외(NOT IN)**하는 방식으로 구현한다 — 새 `type`을
  추가했는데 이 enum에 매핑을 깜빡해도 조회가 깨지지 않고 자동으로 `TRADE`에 걸린다.
- `types()`는 `LIVE`/`AUCTION`/`SHIPPING`/`POINT`에서만 쓰고, `TRADE`는 `isCatchAll()`로 분기해
  별도 정적 메서드(`excludedTypesForCatchAll()`)로 제외 목록을 받는다.

### 2. `NotificationRepository`에 필터 쿼리 메서드 추가

- `findByMember_IdAndTypeIn` / `findByMember_IdAndReadFalseAndTypeIn`
- `findByMember_IdAndTypeNotIn` / `findByMember_IdAndReadFalseAndTypeNotIn`
- `markAllAsReadByMemberIdAndTypeIn` / `markAllAsReadByMemberIdAndTypeNotIn`(`@Modifying` JPQL,
  기존 `markAllAsReadByMemberId`와 같은 패턴)

### 3. `NotificationService`/`NotificationController`에 `category` 파라미터 추가

- `GET /api/users/{userId}/alerts`, `PATCH /api/users/{userId}/alerts/read-all` 둘 다
  `@RequestParam(required = false) NotificationCategory category` 추가. 생략하면 기존 동작
  그대로(전체 조회/전체 읽음).
- 잘못된 `category` 값은 Spring이 `MethodArgumentTypeMismatchException`을 던지고 기존
  `GlobalExceptionHandler`가 400(`INVALID_INPUT_VALUE`)으로 변환한다 — 별도 처리 불필요
  (`ProductController`의 `saleType` 파라미터와 동일 패턴).

### 4. unread count 전용 API (§3.3, 2026-08-07 추가 승인)

`GET /api/users/{userId}/alerts/unread-count`를 신설한다. 마이페이지 요약이 쓰는
`countByMember_IdAndReadFalse`(카테고리 무관, `UserService` 사용 중이라 건드리지 않음)와는 별개로,
`category` 유무에 따라 갈리는 카운트 쿼리를 추가한다.

- 응답: `{ "unreadCount": number }`
- `category` 생략 시 전체 안 읽은 알림 수(기존 `countByMember_IdAndReadFalse`와 동일 값).
- `category` 있으면 §1의 IN/NOT IN 규칙을 그대로 카운트에 적용한다(`TRADE`는 NOT IN).
- 인증/본인 확인은 기존 두 엔드포인트와 동일하게 `requireSelf`를 그대로 쓴다.

004 §3.1 FE 임시 분류 표를 걷어내는 작업은 FE 몫이다 — 반영되면 `docs/requests/FE/`에 계약
문서로 안내한다.

### 5. wish delete path 확정 + 중복 알림 방지 정책 (2026-08-07, 004 마지막 두 항목)

004에 남아 있던 마지막 두 항목을 이 배치에서 함께 정리하고 004 자체를 삭제했다.

- **wish delete path**: 코드 확인 결과 이미 `{id}` = product id로 확정돼 있었다(`WishController`
  주석에 이미 명시, `WishService.unwish(memberId, productId)`가 그대로 씀). BE 판단이 필요한
  문제가 아니라 FE 전달 누락이었다 — `docs/requests/FE/041-wish-delete-path-clarification.md`
  작성.
- **중복 알림 방지 정책**: 알림을 만드는 8개 지점(`ORDER_PAID`/`SHIPMENT_STARTED`/
  `SHIPMENT_COMPLETED`/`POINT_CHARGED`/`POINT_REFUNDED`/`WITHDRAW_COMPLETED`/`LIVE_REMINDER`/
  `AUCTION_OUTBID`/`AUCTION_WON`, 사실 9개)을 전부 감사했다. 전부 이미 한 방향 상태 전이나
  기존 멱등성 가드(송장 재등록 불가, 웹훅 재수신 시 상태 검사, 토스 confirm 중복 대비, 환불
  재승인 불가, 스케줄러 발송 표시 트랜잭션 공유) 뒤에서만 `notify`를 호출하고 있어 알림 레벨
  dedup 장치가 따로 필요 없었다. `ORDER_PAID`/`WITHDRAW_COMPLETED`는 매 호출이 새로운 정당한
  이벤트라 애초에 "중복" 개념이 없다. 이 불변식을 `NotificationCommandPort` Javadoc에 정책으로
  남겼다 — 새 알림 트리거를 추가할 때는 상태 전이 가드 뒤에서만 `notify`를 호출해야 한다.

## 구현 목록

- [x] `NotificationCategory` enum 추가(매핑 표 + `TRADE` catch-all 로직)
- [x] `NotificationRepository`에 `TypeIn`/`TypeNotIn` 조회·읽음 처리 메서드 추가
- [x] `NotificationService.getNotifications`/`markAllAsRead`에 `category` 파라미터 추가
- [x] `NotificationController`의 두 엔드포인트에 `category` 쿼리 파라미터 추가 + Swagger 설명 갱신
- [x] 테스트: `NotificationServiceTest`에 카테고리별 조회/읽음 처리 케이스 추가(`LIVE`/`TRADE`/`POINT`),
      `NotificationCategoryTest`로 매핑 자체 단위 테스트
- [x] `docs/requests/BE/004-social-notification-contract.md` §3.3/§3.4/§6 갱신(반영 완료로) +
      `docs/requests/FE/`에 계약 문서 작성
- [x] `./gradlew build`로 최종 검증 — `BUILD SUCCESSFUL`
- [x] `NotificationRepository`에 `countByMember_IdAndReadFalseAndTypeIn`/`TypeNotIn` 추가
- [x] `NotificationService.getUnreadCount`/`NotificationController`에
      `GET /alerts/unread-count?category=` 신설 + 테스트
- [x] `docs/requests/BE/004` §3.3, `docs/requests/FE/040` 갱신(반영 완료로)
- [x] `./gradlew build`로 재검증 — `BUILD SUCCESSFUL`
- [x] wish delete path 확정 — `docs/requests/FE/041-wish-delete-path-clarification.md` 작성
- [x] 중복 알림 방지 정책 감사 + `NotificationCommandPort` Javadoc에 정책 명시
- [x] `docs/requests/BE/004-social-notification-contract.md` 삭제(마지막 두 항목까지 해소),
      `docs/requests/BE/006-be-request-index.md` 표에서 004 행 제거 + 정리 로그 추가
- [x] `./gradlew build`로 최종 재검증
