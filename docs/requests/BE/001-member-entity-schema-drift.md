# `Member` 엔티티와 스키마 불일치 — 프로필 이미지 등

- **요청자**: 정윤 (라이브·채팅)
- **대상**: 서윤 (회원/인증 도메인)
- **발견 시점**: 2026-07-30, 채팅 메시지 응답(CHAT-001) 작성 중
- **급한 것**: `profileImageUrl` 1건. 나머지는 확인 요청

---

## 급한 것 — `Member.profileImageUrl`이 없다

FE 요청서(`012-live-watch-detail-contract-gaps.md`)가 채팅 메시지에 **작성자 프로필 이미지**를
요청했는데 채울 값이 없다.

- `docs/db/schema.sql`의 `member` 테이블에는 **`profile_image_url VARCHAR(500)`이 있다**
- 그런데 `Member` 엔티티에는 **그 필드 매핑이 없다**
- `ddl-auto`가 엔티티에서 DDL을 만들므로 **실제 DB에도 컬럼이 없는 상태**다

채팅 응답에는 `senderProfileImageUrl` 필드를 넣어 두고 **항상 `null`로 내리고 있다**(FE에는
통보 완료). 필드가 추가되면 저희 쪽은 한 줄만 고치면 된다.

`home/dto/response/FollowedSellerResponse`도 `profileImageUrl`을 내리는데 지금은 picsum
placeholder다 — 같은 필드가 생기면 그쪽도 실제 값으로 바꿀 수 있다.

**요청**: `Member`에 `profileImageUrl` 필드를 추가해 주시고, 추가되면 알려 주시면 채팅·홈 응답을
연결하겠다.

## 확인 요청 — 엔티티와 `schema.sql`이 여러 군데 어긋난다

채팅 작업 중 `Member`를 읽다가 발견했다. **`schema.sql`은 "단일 기준"이라고 README에 적혀
있는데 실제 DB는 엔티티에서 생성되므로**, 지금은 두 문서가 서로 다른 사실을 말하고 있다.

| 항목 | `schema.sql` | `Member` 엔티티 |
| --- | --- | --- |
| 프로필 이미지 | `profile_image_url VARCHAR(500)` | **없음** |
| 닉네임 | `nickname NOT NULL UNIQUE` | nullable (온보딩에서 채움) |
| 비밀번호 | `password_hash` (SSO는 NULL 허용) | `password` `nullable = false` |
| 전화번호 | `phone` | `phoneNumber` |
| 회원 구분 | `member_type` (GENERAL/BUSINESS) | **없음** |
| 상태 | `status` (ACTIVE/SUSPENDED/WITHDRAWN) | **없음** |
| 탈퇴 | `deleted_at` | **없음** |
| 성별 | 없음 | `gender` |
| 주소 | 없음 | `address` |

어느 쪽이 맞는지는 회원 도메인 담당이 판단할 일이라 고치지 않았다. 다만 **`nickname`이
nullable인 것은 라이브·채팅에 실제로 영향이 있다**:

- 스키마는 `NOT NULL`인데 엔티티는 nullable이라, 온보딩 전 회원이 발언하면 작성자명이 비어
  **이름 없는 말풍선**이 된다
- 저희 쪽에서는 `nickname != null ? nickname : name`으로 대체하고 있다(`ChatMessage.senderDisplayName`)
- 같은 문제가 `LiveDetailResponse.hostNickname`, `LiveListItemResponse.hostNickname`,
  `ProductDetailResponse.sellerNickname`에도 있는데 그쪽은 대체 없이 그대로 내린다

**요청**: 닉네임을 필수로 갈 것인지(= 온보딩 완료 전에는 방송·발언 불가) 아니면 nullable을
유지하고 표시명 대체 규칙을 공통화할 것인지 정해 주시면, 라이브·채팅 쪽도 맞추겠다.

## 참고

- 채팅 응답 DTO: `chat/dto/response/ChatMessageResponse`
- FE 계약 문서: `.claude/requests/fe/001-live-stomp-contract.md` 5번 항목