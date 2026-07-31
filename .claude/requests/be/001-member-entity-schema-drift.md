# `Member` 엔티티와 스키마 불일치 — 남은 항목

- **요청자**: 정윤 (라이브·채팅)
- **대상**: 서윤 (회원/인증 도메인)
- **발견 시점**: 2026-07-30, 채팅 메시지 응답(CHAT-001) 작성 중
- **일부 반영됨**: `profileImageUrl`, `memberType`, `status`, `deletedAt`, `gender`, `address`,
  `detailAddress`, `postalCode` 추가, `nickname` NOT NULL 제거, `phone` → `phone_number` 컬럼명 통일까지
  `S15P11A108-227`(온보딩 기본 정보 저장 API)에서 반영 완료. 아래 항목만 남았다.

---

## 남은 불일치

| 항목 | `schema.sql` | `Member` 엔티티 |
| --- | --- | --- |
| 비밀번호 | `password_hash` (SSO는 NULL 허용) | `password`, 이제 nullable(SSO 대응) — **컬럼명은 여전히 다름** |

비밀번호는 회원가입/로그인(AUTH) 도메인이 다루는 컬럼이라 온보딩 브랜치에서는 건드리지 않았다.
회원가입/로그인 쪽 작업할 때 `schema.sql`의 `password_hash`와 엔티티의 `password` 중 어느 쪽 이름으로
통일할지 정리해주면 좋겠다.

**표시명 대체 규칙 공통화**는 아직 답하지 못했다. 라이브·채팅 쪽 `nickname != null ? nickname : name`
같은 임시 대체를 계속 유지해도 되는지, 아니면 다른 방식으로 통일할지는 이후에 다시 논의하면 좋겠다.

## 참고

- 채팅 응답 DTO: `chat/dto/response/ChatMessageResponse`
- FE 계약 문서: `.claude/requests/fe/001-live-stomp-contract.md` 5번 항목
