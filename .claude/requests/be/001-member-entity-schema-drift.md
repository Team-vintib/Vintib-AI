# `Member` 엔티티와 스키마 불일치 — 남은 항목

- **요청자**: 정윤 (라이브·채팅)
- **대상**: 서윤 (회원/인증 도메인)
- **발견 시점**: 2026-07-30, 채팅 메시지 응답(CHAT-001) 작성 중
- **일부 반영됨**: `profileImageUrl`, `memberType`, `status`, `deletedAt`는 `S15P11A108-227`
  (온보딩 기본 정보 저장 API)에서 `Member` 엔티티에 추가 완료. 아래 항목은 아직 남아있다.

---

## 남은 불일치

| 항목 | `schema.sql` | `Member` 엔티티 |
| --- | --- | --- |
| 닉네임 | `nickname NOT NULL UNIQUE` | nullable (온보딩에서 채움) — **의도적으로 nullable 유지, `schema.sql`은 아직 안 고침** |
| 비밀번호 | `password_hash` (SSO는 NULL 허용) | `password`, 이제 nullable(SSO 대응) — **컬럼명은 여전히 다름** |
| 전화번호 | `phone` | `phoneNumber`(컬럼명 `phone_number`) — **컬럼명 여전히 다름** |
| 성별 | 없음 | `gender` — `schema.sql`에 컬럼 자체가 없음 |
| 주소 | 없음 | `address` — `schema.sql`에 컬럼 자체가 없음 |

닉네임은 **nullable 유지로 정했다**(온보딩 전에는 비워둔다는 기존 설계를 따름). 다만 `schema.sql`의
`NOT NULL` 제약은 아직 그대로라 문서·실제 엔티티가 계속 어긋난 상태다. 비밀번호·전화번호 컬럼명,
성별·주소 컬럼 추가는 아직 손대지 않았다 — 회원 도메인 쪽에서 언제 정리할지 판단이 필요하다.

**표시명 대체 규칙 공통화**는 아직 답하지 못했다. 라이브·채팅 쪽 `nickname != null ? nickname : name`
같은 임시 대체를 계속 유지해도 되는지, 아니면 다른 방식으로 통일할지는 이후에 다시 논의하면 좋겠다.

## 참고

- 채팅 응답 DTO: `chat/dto/response/ChatMessageResponse`
- FE 계약 문서: `.claude/requests/fe/001-live-stomp-contract.md` 5번 항목
