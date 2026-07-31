# 알림 읽음 처리 API

## 배경/목표

APIs.md "알림(Notifications)" 섹션의 `PATCH /users/{userId}/alerts/{id}` (NOTI-001)를 구현한다.
알림함(웹 서비스 내부 알림 목록)에 쌓인 알림 한 건을 읽음 처리하는 기능만 다룬다.
알림 목록 조회(`GET /users/{id}/alerts`)는 이 계획 범위에서 제외하고 별도로 작업한다.

`notification` 테이블은 `BE/docs/db/schema.sql`에 이미 정의돼 있으나(작성자: 서윤), 그에 대응하는
JPA 엔티티/리포지토리/서비스/컨트롤러가 아직 없다. 이번 작업에서 도메인 패키지를 새로 만든다.

## 작업 내용

- 도메인 패키지 `com.ssafy.backend.notification`을 신설한다 (`.claude/skills/scaffold` 컨벤션).
- 엔티티는 `schema.sql`의 `notification` 테이블 컬럼을 그대로 매핑한다(id, member, type, title, body,
  refType, refId, isRead, createdAt). 목록 조회 기능에서 재사용할 수 있도록 스키마 전체를 반영하되,
  이번 작업에서 실제로 쓰는 리포지토리/서비스 메서드는 읽음 처리에 필요한 범위로 한정한다.
- 읽음 처리는 상태 변경 의도가 드러나는 엔티티 메서드(`markAsRead()` 등)로 처리한다(습관적 `@Setter` 금지 컨벤션).
- 이미 읽은 알림을 다시 읽음 처리해도 에러 없이 멱등하게 200을 반환한다(재요청·중복 클릭 대비).
- 소유권 검증은 `WishController.requireSelf` 패턴을 그대로 따른다:
  - path의 `userId`가 인증된 본인이 아니면 403 (`NotificationErrorCode` 신설, `WISH_FORBIDDEN`과 동일 패턴).
  - `userId`는 본인이 맞지만 해당 `id`의 알림이 없거나 다른 회원 소유면 404로 응답해 존재 자체를 드러내지 않는다(IDOR 방지).
- 응답은 다른 PATCH 엔드포인트(`ProductController.updateProduct` 등)와 동일하게 200 + `ApiResponse<NotificationResponse>`
  (id, isRead 정도의 최소 필드)로 통일한다. 204 No Content는 쓰지 않는다.
- `ErrorCode`에 `NOTIFICATION_NOT_FOUND`(404), `NOTIFICATION_FORBIDDEN`(403) 추가.
- Swagger 문서화(`@Tag`/`@Operation`/`@ApiResponses`)를 `.claude/skills/swagger` 컨벤션에 맞춰 채운다.
- 서비스 단위 테스트(또는 `@WebMvcTest`) 최소 1개 이상, 한글 테스트 메서드명으로 작성.
- APIs.md "알림 읽음 처리" 행의 "인증 필요 여부"에 ✓, "구현 완료 여부"에 ✓ 반영.

## 구현 목록

- [x] `notification/entity/Notification.java` — schema.sql 컬럼 매핑, `markAsRead()` 메서드
- [x] `notification/repository/NotificationRepository.java` — `findById` 등 읽음 처리에 필요한 최소 메서드
- [x] `notification/dto/response/NotificationResponse.java`
- [x] `notification/service/NotificationService.java` — `markAsRead(memberId, notificationId)`
- [x] `notification/controller/NotificationController.java` — `PATCH /api/users/{userId}/alerts/{id}`
- [x] `global/exception/ErrorCode`에 `NOTIFICATION_NOT_FOUND`, `NOTIFICATION_FORBIDDEN` 추가
- [x] 서비스/컨트롤러 테스트 (한글 메서드명)
- [x] Swagger 어노테이션
- [x] APIs.md 알림 읽음 처리 행 갱신 (인증 필요 여부 ✓, 구현 완료 여부 ✓)
- [x] `BE:verify` (CI와 동일한 검증 스크립트) 통과 확인

## 완료

`S15P11A108-379` 커밋으로 구현 완료. 목록 조회는 [[SY011-notification-list]], 전체 읽음 처리는
[[SY012-notification-read-all]]에서 이어서 진행한다.

## 확인 필요한 미결정 사항

- 없음 (스키마·컨벤션 모두 기존 도메인에서 확인됨). 다만 목록 조회를 나중에 담당할 사람이 엔티티 필드를
  추가/변경해야 한다면 이 계획 파일과 별개로 그 작업에서 조정하면 된다.