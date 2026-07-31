# 알림 목록 조회 API

## 배경/목표

APIs.md "알림(Notifications)" 섹션의 `GET /users/{id}/alerts` (NOTI-001)를 구현한다.
알림 읽음 처리([[SY010-notification-read]])에서 만든 `notification` 엔티티/도메인 패키지를 그대로 이어서 쓴다.

기능 정의서(`FE/docs/notion/화면 기반 개발 요구 문서.md` `[NOTI-001] 알림센터`)는 "전체/라이브/경매/거래/배송/포인트"
카테고리 탭과 "모두 읽음" 일괄 처리도 언급하지만, `APIs.md`에는 목록 조회(GET)와 단건 읽음 처리(PATCH) 두
엔드포인트만 확정돼 있다. 카테고리 탭 필터와 일괄 읽음 API는 이번 계획 범위에서 제외한다 (아래 "미결정 사항" 참고).

## 작업 내용

- 응답은 다른 목록 조회(`WishController.getWishList`)와 동일하게 페이지네이션(`Pageable` + `PageResponse<T>`)으로 구성한다.
- 정렬은 `schema.sql`의 `ix_notification_member` 인덱스 주석("안 읽은 것 먼저가 기본 조회")을 그대로 따른다:
  **읽지 않음(`is_read=false`) 먼저 → 그 안에서 최신순(`created_at DESC`)** 으로 고정하고, 클라이언트가
  다른 sort를 보내도 무시한다(`ProductService.getProductList`, `WishService.getWishList`와 동일한 정책).
- 읽지 않은 알림만 보는 옵션은 쿼리 파라미터 `unreadOnly`(boolean, 기본 false)로 지원한다. NOTI-001의
  "읽음·읽지 않음 상태를 구분한다" 요구사항을 충족하면서, 명세에 없는 카테고리 탭 필터보다 훨씬 단순하고
  안전하게 결정 가능한 범위다.
- 응답 아이템에는 FE가 알림 클릭 시 타입별로 라우팅할 수 있도록 `id`, `type`, `title`, `body`, `refType`,
  `refId`, `isRead`, `createdAt`을 모두 담는다("개발 시 주의사항: 알림 클릭 이동은 알림 타입별 라우팅 매핑이
  필요하다"는 기능 정의서 요구사항 반영).
- 소유권 검증은 [[SY010-notification-read]]에서 만든 `NotificationController.requireSelf`와 동일한 패턴을
  그대로 재사용한다 (path의 `userId` ≠ 본인이면 403).
- Swagger 문서화(`.claude/skills/swagger` 컨벤션)와 서비스 단위 테스트(한글 메서드명) 추가.
- APIs.md "알림 목록 조회" 행의 인증 필요 여부·구현 완료 여부에 ✓ 반영.

## 구현 목록

- [x] `notification/repository/NotificationRepository.java`에 `findByMember_Id`, `findByMember_IdAndReadFalse`
      (둘 다 `Pageable` 인자, 고정 정렬은 서비스에서 `Sort.by(asc("read"), desc("createdAt"))`로 구성) 추가
- [x] `notification/dto/response/NotificationItemResponse.java` 신설
- [x] `notification/service/NotificationService.java`에 `getNotifications(memberId, unreadOnly, pageable)` 추가
- [x] `notification/controller/NotificationController.java`에 `GET /api/users/{userId}/alerts` 추가
      (기존 `PATCH /{id}`와 같은 클래스, 같은 `@RequestMapping` 하위)
- [x] 서비스 테스트 (한글 메서드명): 전체 조회, unreadOnly 필터, 빈 목록, 정렬 순서(읽지 않음 우선) 확인
- [x] Swagger 어노테이션
- [x] APIs.md 알림 목록 조회 행 갱신 (인증 필요 여부 ✓, 구현 완료 여부 ✓)
- [x] `BE:verify` 통과 확인

## 완료

`S15P11A108-378` 커밋으로 구현 완료. "모두 읽음" 일괄 처리는 [[SY012-notification-read-all]]에서 이어서 진행한다.

## 확인 필요한 미결정 사항

- **카테고리 탭 필터(전체/라이브/경매/거래/배송/포인트) 제외**: `ref_type` 컬럼 주석은 "LIVE / AUCTION / ORDER ..."
  정도만 예시로 들 뿐, "거래"와 "배송"을 어떻게 구분할지(둘 다 주문 관련이라 `ref_type=ORDER`로 겹칠 가능성),
  "포인트"에 대응하는 `ref_type` 값이 무엇인지가 정해져 있지 않다. 이 값 체계는 NOTI-002~006(알림을 실제로
  만드는 트리거 로직, 아직 미구현)을 설계할 때 함께 정하는 게 맞다고 보고 이번 계획에서는 필터를 만들지 않는다.
  나중에 카테고리 탭이 필요해지면 이 목록 API에 `refType` 쿼리 파라미터를 추가하는 방식으로 확장한다.
- **"모두 읽음" 일괄 처리 제외**: `APIs.md`에 해당 엔드포인트가 없다. 필요하면 별도 계획(예: `PATCH /users/{userId}/alerts/read-all`)으로 추가한다.