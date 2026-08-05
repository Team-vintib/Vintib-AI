# SY030 팔로우/언팔로우 카운트 동기화 + 라벨/확인

## 배경/목표

마이페이지 팔로워·팔로잉 탭에서 팔로우/언팔로우해도 상단 통계 카드·탭 배지 숫자가 안 갱신되는 버그를 고치고, 팔로우/팔로잉 대신 팔로우/언팔로우로 라벨을 나누고 언팔로우 시 확인 다이얼로그를 추가한다(`docs/requests/FE/014-follow-unfollow-confirm.md` 반영).

## 작업 내용

- `MyPage.vue`의 `toggleSocialFollow`: 성공 시 `followingCount` +1/-1 갱신, 언팔로우 시 `followingsList`에서 제거.
- `FollowButton.vue`/`LiveWatchHeader.vue`/`MyPage.vue` 소셜 카드 버튼: 라벨을 `팔로우`/`언팔로우`로 변경, 언팔로우 클릭 시 `window.confirm`으로 확인 후 처리.
- `docs/requests/FE/014-follow-unfollow-confirm.md` 삭제(반영 완료).

## 구현 목록

- [ ] `MyPage.vue` 카운트/목록 동기화
- [ ] 라벨 + 확인 다이얼로그 3곳
- [ ] 요청 문서 삭제
- [ ] `vue-tsc --build` 통과 확인
