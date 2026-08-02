# 011 User/MyPage API 요청

## 1. 요청 개요

- 요청 파트: FE
- 대상 파트: BE
- 요청 목적: 내 정보, 공개 프로필, 마이페이지 요약 API 계약을 정리한다.
- 우선순위: P1
- 시연 필수 여부: 마이페이지/공개 프로필 화면이 없어 현재 시연 필수 아님. Auth guard 안정화 목적의 `GET /api/me`는 P0 Auth 요청과 중복된다.

## 2. 현재 연동 상태

- 내 정보 조회/수정, 판매 상품 관리, 구매/판매 내역, 라이브 관리, 포인트/출금(MY-001~005, MY-007) 구현 완료 — 확정 계약은 `docs/requests/FE/012-mypage-contract.md` 참고
- FE 구현 완료 범위
  - `domains/my` 마이페이지 화면 없음
  - 공개 프로필 상세 화면 없음
  - auth route guard는 현재 `authStore.user`의 최소 정보만 사용
- 현재 임시 처리 또는 Mock 사용 여부
  - 마이페이지/공개 프로필은 화면 설계 후 연결해야 한다.

## 3. 추가 구현 요청

### 3.3 공개 회원/판매자 프로필

- Method / Endpoint: `GET /api/users/{userId}`
- 요청 목적: 상품 상세 판매자, 검색 회원, 라이브 호스트의 공개 프로필을 조회한다.
- FE 사용처: 공개 프로필 화면, 상품 상세 판매자 영역, 검색 회원 결과
- 요청 데이터
  - Path: `userId`
- 응답 데이터
  - `id`, `nickname`, `profileImageUrl`, `coverImageUrl`, `description`, `followerCount`, `followingCount`, `productCount`, `liveCount`, `isFollowing`, `businessVerified`
- 응답 예시

```json
{
  "success": true,
  "data": {
    "id": 10,
    "nickname": "seller",
    "profileImageUrl": null,
    "coverImageUrl": null,
    "description": "빈티지 셀러입니다.",
    "followerCount": 124,
    "followingCount": 20,
    "productCount": 8,
    "liveCount": 3,
    "isFollowing": false,
    "businessVerified": true
  },
  "error": null
}
```

### 3.4 마이페이지 요약

- Method / Endpoint: `GET /api/users/{userId}/mypage`
- 요청 목적: 마이페이지 첫 화면에 필요한 카운터와 요약 정보를 한 번에 조회한다.
- FE 사용처: 향후 마이페이지 첫 화면
- 요청 데이터
  - Header: `Authorization: Bearer {accessToken}`
  - Path: `userId`
- 응답 데이터
  - `user.id`, `user.nickname`, `user.profileImageUrl`, `user.memberType`, `user.businessVerificationStatus`
  - `counts.orders`, `counts.sales`, `counts.wishes`, `counts.followers`, `counts.unreadNotifications`
  - `pointBalance`
- 응답 예시

```json
{
  "success": true,
  "data": {
    "user": {
      "id": 1,
      "nickname": "vintagelover",
      "profileImageUrl": null,
      "memberType": "GENERAL",
      "businessVerificationStatus": "NONE"
    },
    "counts": {
      "orders": 0,
      "sales": 0,
      "wishes": 3,
      "followers": 12,
      "unreadNotifications": 1
    },
    "pointBalance": 10000
  },
  "error": null
}
```

### 3.5 판매자 프로필용 목록

**주의 — 경로가 MY-002/005와 겹친다.** `GET /api/users/{userId}/products`(MY-002)와 `GET /api/lives?hostId={userId}`(MY-005)를 구현했지만, 둘 다 **본인 전용**이다(타인이 호출하면 403, `products`는 DRAFT 등 비공개 상태까지 노출하기 때문에 공개용으로 그대로 못 쓴다). 이 §3.5가 요청한 "공개 프로필에서 판매자 상품/라이브 보여주기"는 아직 없다 — 필요하면 별도 계약으로 다시 요청해달라(예: 상시 판매 상태만 보이는 조회 전용 엔드포인트).

## 4. 기존 API 변경 요청

- 기존 요청·응답에서 변경할 내용
  - 기존 상품/라이브 목록 API에 `sellerId` 또는 `hostId` filter를 추가하면 공개 프로필용 별도 목록 API를 줄일 수 있다.
- 추가할 필드
  - 없음
- 변경 영향 범위
  - 공개 프로필 상품/라이브 목록

## 5. 보류 또는 시연 제외 범위

- 현재 구현하지 않아도 되는 기능
  - 마이페이지 화면
  - 공개 프로필 화면
- 추후 구현 예정 기능
  - 프로필 이미지 업로드
  - 소개글/커버 이미지 수정
  - 사용자 활동 내역
  - 마이페이지 요약(§3.4), 공개 프로필(§3.3) — 아직 미구현

## 6. 협의 필요 사항

- FE·BE 간 결정이 필요한 내용
  - 공개 프로필과 마이페이지 요약을 분리할지
  - 프로필 이미지 업로드 방식
  - 비회원 공개 프로필의 `isFollowing` 값 정책
  - 판매자 프로필 상품/라이브 목록을 별도 공개 엔드포인트로 만들지(§3.5 참고 — MY-002/005는 본인 전용이라 재사용 불가)
- 아직 확정되지 않은 응답 구조나 정책
  - 마이페이지 카운터 범위(§3.4)

## 7. 추가 요청 없음

- 이미 정상 연동된 API: 없음
- 기존 규격을 유지하면 되는 기능: 없음
