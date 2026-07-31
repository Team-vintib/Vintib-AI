# 알림 전체 읽음 처리 API

## 배경/목표

기능 정의서(`FE/docs/notion/화면 기반 개발 요구 문서.md` `[NOTI-001] 알림센터`)의 "모두 읽음" 동작
("사용자 행동: 모두 읽음 → 처리 내용: 읽음 처리 요청 → 결과: 현재 화면 갱신")을 구현한다.

[[SY011-notification-list]]에서 이 기능을 계획 범위 밖으로 미뤄뒀던 이유는 `APIs.md`에 해당
엔드포인트가 아직 없었기 때문이다. 이번 계획에서 `APIs.md`에 새 행을 추가하고 함께 구현한다.

## 작업 내용

- **엔드포인트 신설**: `PATCH /api/users/{userId}/alerts/read-all`. `APIs.md` "알림(Notifications)"
  섹션에 `알림 전체 읽음 처리 | PATCH | /users/{userId}/alerts/read-all | ✓ | NOTI-001` 행을 추가한다.
- 소유권 검증은 기존 `NotificationController.requireSelf`를 그대로 재사용한다 (path의 `userId` ≠ 본인이면 403).
- 본인 소유이면서 아직 읽지 않은(`is_read=false`) 알림을 모두 읽음 처리한다. 대상이 0건이어도 에러 없이
  200을 반환한다(빈 알림함에 눌러도 정상 동작 — 멱등성은 [[SY010-notification-read]]의 단건 읽음 처리와
  같은 원칙).
- 알림 개수가 많을 수 있으므로 각 행을 엔티티로 로드해 `markAsRead()`를 반복 호출하는 대신, JPQL
  벌크 업데이트(`@Modifying @Query("update Notification n set n.read = true where ...")`)로 한 번에
  처리한다. 이 리포지토리에서 벌크 업데이트를 쓰는 첫 사례라 `@Modifying(clearAutomatically = true)`를
  붙여 영속성 컨텍스트 캐시가 낡은 상태로 남지 않게 한다.
- 응답은 몇 건을 읽음 처리했는지 클라이언트가 바로 알 수 있게 `{ "updatedCount": number }` 형태의 최소
  응답 DTO(`NotificationReadAllResponse`)로 반환한다(200). FE가 화면을 갱신하려면 어차피 목록을
  다시 조회해야 하므로 목록 자체를 함께 내려주지는 않는다.
- Swagger 문서화(`.claude/skills/swagger` 컨벤션)와 서비스 단위 테스트(한글 메서드명) 추가.

## 구현 목록

- [x] `APIs.md` "알림(Notifications)" 섹션에 "알림 전체 읽음 처리" 행 추가
- [x] `notification/repository/NotificationRepository.java`에 `@Modifying @Query`로
      `markAllAsReadByMemberId(Long memberId)` (읽지 않은 알림만 대상, 갱신 건수 반환) 추가
- [x] `notification/dto/response/NotificationReadAllResponse.java` 신설
- [x] `notification/service/NotificationService.java`에 `markAllAsRead(memberId)` 추가
- [x] `notification/controller/NotificationController.java`에
      `PATCH /api/users/{userId}/alerts/read-all` 추가 (기존 컨트롤러에 같이 둠)
- [x] 서비스 테스트 (한글 메서드명): 읽지 않은 알림이 있는 경우, 이미 모두 읽은 경우(0건) 확인.
      다른 회원 알림은 건드리지 않는지는 JPQL의 `WHERE member.id = :memberId` 조건으로 보장되며,
      리포지토리 모킹 단위 테스트로는 직접 검증할 수 없어 memberId 인자 전달 여부까지만 확인했다.
- [x] Swagger 어노테이션
- [x] `BE:verify` 통과 확인 (`BUILD SUCCESSFUL`)