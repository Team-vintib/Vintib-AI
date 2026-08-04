# SY029 팔로우/언팔로우 실 연동

## 배경/목표

`ProfilePage.vue`의 팔로우 버튼은 이미 실 API로 동작하지만, 라이브 시청 페이지(`LiveWatchHeader`)의 팔로우 버튼은 API 호출 없는 로컬 토글이었고 마이페이지 "팔로워·팔로잉" 탭은 목록도 항상 비고 버튼도 `disabled` 더미였다. 이 두 곳을 실 API로 연동한다.

## 작업 내용

- `LiveWatchPage.vue`: 라이브 로드 시 `getPublicProfile(hostId)`로 실제 `isFollowing` 초기값을 받아오고, 팔로우 토글을 `followUser`/`unfollowUser` 실 API + `followStore` 낙관적 업데이트(`ProfilePage.vue`의 `toggleProfileFollow`와 동일 패턴)로 교체.
- `MyPage.vue` "팔로워·팔로잉" 탭: `getFollowers`/`getFollowings`로 실제 목록을 가져와 표시, 카드의 팔로우/언팔로우 버튼을 `disabled` 더미에서 실 API 호출로 교체. `introduction`/`followedAt` 등 실 API에 없는 필드는 표시에서 제거.

## 구현 목록

- [ ] `LiveWatchPage.vue` 팔로우 실 연동
- [ ] `MyPage.vue` 팔로워·팔로잉 탭 실 연동
- [ ] `vue-tsc --build` 통과 확인
