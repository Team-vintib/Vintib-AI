# 공개 프로필·팔로우

## 배경/목표

기존 `/my` 중심의 본인 전용 마이페이지를 공개 조회 가능한 사용자 프로필 흐름으로 확장한다. 홈 검색 → 사용자 검색 결과 → 공개 프로필 → 팔로워/팔로잉 목록 → 다른 사용자 프로필 이동이 실제 API 기반으로 이어지게 하고, 프로필/검색/목록의 팔로우 상태를 일관되게 관리한다.

## 사전 조사 결과

- 현재 라우트는 `/my`만 있고 `/profile/*` 라우트는 없다. `/my`는 `MyPage.vue`에 본인 전용 대시보드, 내 정보 수정, 상품/라이브 관리, 팔로워·팔로잉 mock 섹션이 섞여 있다.
- 기존 마이페이지 명칭은 `ROUTE_NAMES.MY`, `ROUTE_PATHS.MY`, `GlobalNavigation.vue`, `MY_SECTION_OPTIONS`, `MyPage.vue` 화면 문구에 남아 있다.
- 본인 식별은 `useAuthStore().user?.id`와 저장 토큰 hydrate/validate 흐름을 사용한다.
- 공개 프로필 API는 `GET /api/users/{id}/profile`이며 비회원도 조회 가능하다. 응답 필드는 `id`, `nickname`, `profileImageUrl`, `description`, `coverImageUrl`, `followerCount`, `followingCount`, `productCount`, `liveCount`, `isFollowing`, `businessVerified`다.
- 팔로우 API는 `POST /api/users/{id}/followers`, 언팔로우 API는 `DELETE /api/users/{id}/followers`다. 응답은 팔로우 시 `targetUserId`, `isFollowing`, `followerCount`이고, 언팔로우는 204다. 자기 자신 팔로우는 400이므로 FE에서 버튼을 숨긴다.
- 팔로워/팔로잉 목록 API는 `GET /api/users/{id}/followers`, `GET /api/users/{id}/followings`이며 공개 조회 가능하다. 로그인 상태면 각 항목의 `isFollowing`이 조회자 기준으로 채워진다.
- 사용자별 상품 목록은 기존 `GET /api/products?sellerId={userId}`로 충족된다. FE `getProductList`에는 아직 `sellerId` 파라미터가 없다.
- 사용자별 라이브 목록은 기존 `GET /api/lives?hostId={userId}`로 충족된다. FE `requestLiveList`/`LiveListQuery`에는 아직 `hostId` 파라미터가 없다.
- 통합 검색 BE 응답은 `products`, `lives`, `users` 구조이고 `type`은 `ALL|PRODUCT|LIVE|USER`다. FE `searchApi.ts`는 현재 `members` 필드를 기대하고 `SearchResultsPage.vue`는 API 래퍼를 사용하지 않는 mock/클라이언트 필터 기반이라 계약 정정과 실연동이 필요하다.
- 재사용 후보는 `ProductCard.vue`, `LiveListCard.vue`, `SearchMemberResultCard.vue`이며 공통 페이지네이션 컴포넌트는 없다. 페이지네이션 UI는 상품 목록/검색 페이지의 기존 패턴을 복제하되 필요하면 프로필 도메인 내부 컴포넌트로 분리한다.

## 작업 내용

- `domains/profile`을 새 도메인으로 추가하고 공개 프로필 조회, 팔로우/언팔로우, 팔로워/팔로잉 목록 조회 API와 타입을 둔다. 기존 `domains/follow` 빈 폴더는 별도 독립 화면이 없어 우선 사용하지 않는다.
- `/profile/me`, `/profile/:userId`, `/profile/:userId/followers`, `/profile/:userId/following` 라우트를 추가하고 기존 `/my` 진입은 `/profile/me`로 연결한다. 본인 전용 설정/관리 화면은 프로필 페이지 안에서 본인일 때만 진입 가능하게 유지하거나 기존 `/my?section=...` 호환 리다이렉트로 연결한다.
- 공개 프로필 페이지는 상단 프로필 정보와 통계(팔로잉/팔로워/상품), `상품|라이브` 탭을 중심으로 구성한다. 본인 프로필에는 팔로우 버튼을 숨기고, 타인 프로필에는 `FollowButton`을 표시한다.
- `FollowButton`을 공통으로 만들어 프로필 상단, 팔로워/팔로잉 목록, 사용자 검색 결과에서 재사용한다. 요청 중 disabled/loading, 로그인 유도, 자기 자신 방어, 실패 시 상태 복구를 포함한다.
- 팔로우 상태는 `profile/stores/followStore.ts` 같은 Pinia store로 사용자 ID 기준 관리한다. API 응답을 받으면 프로필, 목록, 검색 결과가 같은 store 상태를 참조하도록 갱신한다.
- `getProductList`에 `sellerId`를 추가하고 공개 프로필 상품 탭에서 페이지네이션으로 사용한다. 상품 카드의 찜 토글은 기존 `wishStore`와 product API를 재사용한다.
- 라이브 목록 API 래퍼에 `hostId`와 공개 프로필용 종료 포함 정책을 반영한다. 타인 프로필은 공개 API 정책상 진행/예약 중심으로 표시하고, 본인 프로필이면 종료 이력까지 볼 수 있게 현재 BE 정책(`hostId === viewerId`)을 따른다.
- 팔로워/팔로잉 목록 페이지는 `FollowUserItem`을 통해 프로필 이동과 팔로우 토글을 제공한다. 목록 항목은 API 의미와 다르게 임의 삭제하지 않고, 상태와 카운트만 즉시 반영한다.
- 검색 API를 실제 `GET /api/search`에 연결한다. FE 타입을 BE 계약(`users`, `USER`)에 맞추고, 검색 결과의 사용자 카드 클릭 시 `/profile/:userId`로 이동시킨다. 검색 결과 팔로우 버튼은 `FollowButton`을 재사용한다.
- 검색어는 trim 후 빈 값이면 요청하지 않는다. route query 변경 기준으로 요청하고, request id로 이전 응답이 최신 결과를 덮지 않게 막는다. 입력 debounce는 기존 검색 화면이 submit 기반이라 우선 submit/route 변경 단위로 처리한다.
- 화면 문구에서 공개 프로필 영역은 `프로필`, 팔로워 통계는 `팔로워` 용어를 사용한다. 본인 전용 설정/관리 섹션은 다른 사용자 프로필에 노출하지 않는다.
- 구현 후 `FE/docs/frontend/implementation/current-structure.md`, `FE/docs/frontend/implementation/status.md`, 필요 시 `FE/docs/frontend/flows/route-map.md`를 갱신한다.

## 구현 목록

- [x] `domains/profile/types/profile.types.ts`에 공개 프로필, 팔로우 응답, 팔로워/팔로잉 목록, 페이지 메타 타입 정의
- [x] `domains/profile/api/profileApi.ts`에 공개 프로필/팔로우/언팔로우/팔로워/팔로잉 API 추가
- [x] `domains/profile/stores/followStore.ts`에 사용자별 팔로우 상태와 팔로워 수 동기화 로직 추가
- [x] `FollowButton.vue` 구현: 본인 숨김, 비로그인 로그인 유도, 요청 중 disabled/loading, 실패 복구
- [x] `ProfilePage.vue` 구현: `/profile/me`, `/profile/:userId` 공통 처리, 본인 여부 분리, 상품/라이브 탭과 독립 페이지 상태
- [x] `FollowListPage.vue` 구현: followers/following 모드, 페이지네이션, 사용자 프로필 이동, 항목별 팔로우 토글
- [x] `getProductList`에 `sellerId` 파라미터 추가 및 프로필 상품 탭 연동
- [x] `liveListApi`/타입에 `hostId` 파라미터 추가 및 프로필 라이브 탭 연동
- [x] 라우트 상수와 라우터에 `/profile/me`, `/profile/:userId`, `/profile/:userId/followers`, `/profile/:userId/following` 추가
- [x] 기존 `/my`와 글로벌 내비게이션의 `마이페이지` 명칭/진입을 `프로필` 기준으로 정리
- [x] 검색 API 타입을 `users`/`USER` 계약에 맞게 정정하고 `SearchResultsPage.vue`를 실제 API 기반으로 전환
- [x] `SearchMemberResultCard.vue`를 프로필 이동/공통 FollowButton 사용 구조로 조정
- [x] 프로필/목록/검색의 로딩, 빈 상태, 실패 상태, 존재하지 않는 사용자 상태 처리
- [x] 문서(`current-structure.md`, `status.md`, route-map 필요 시) 갱신
- [x] `npm run type-check`, `npm run build-only` 검증

## 확인이 필요한 미결정 사항

- 기존 `/my?section=profile|tryon|products|sales|lives|business|cart` 본인 전용 관리 화면을 새 `/profile/me` 안에 통합할지, `/profile/me/settings` 같은 별도 본인 전용 화면으로 분리할지 결정이 필요하다. 구현 시에는 기존 진입 링크가 끊기지 않도록 호환 리다이렉트를 둔다.
- 공개 프로필의 타인 라이브 탭에서 종료 라이브까지 보여줄지는 BE 공개 정책상 제한되어 있다. 현재 계약은 타인 `hostId` 조회 시 공개 상태만 보이므로 FE는 이 정책을 따른다.
