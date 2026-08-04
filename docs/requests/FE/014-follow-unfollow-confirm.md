# 언팔로우 확인 다이얼로그 — 남은 FE 항목

- **요청 파트**: BE / **대상 파트**: FE

## 반영 현황 (2026-08-04 확인)

- ✅ 본인 프로필에서 팔로우 버튼 숨김/비활성(`FollowButton.vue`, `ProfilePage.vue`, `FollowListPage.vue`), 팔로우(POST)는 확인 없이 즉시 반영 — 반영됨.
- ⏳ 언팔로우 확인 다이얼로그가 남았다.

## 남은 항목

- 이미 팔로우 중인 상대에게 팔로우 버튼을 다시 누르면, 즉시 `DELETE /api/users/{userId}/followers`를 호출하지 말고 "팔로우를 취소하시겠습니까?" 확인 다이얼로그를 먼저 띄운다. 사용자가 확인을 누른 시점에만 `DELETE`를 호출한다.
  - 현재 `ProfilePage.vue`/`FollowListPage.vue`는 확인 없이 바로 `unfollowUser()`를 호출한다.
- BE `DELETE`는 멱등(팔로우 중이 아니어도 204)이라 확인 이후 호출이든 재시도든 안전하다 — FE 별도 방어 로직 불필요.
- 참고: 팔로우/언팔로우 API 설계는 `docs/plans/BE/SY024-follow.md`.
