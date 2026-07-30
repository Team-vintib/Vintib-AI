# 회원/마이페이지 API 계약 요청

## 요청 파트 / 대상 파트

- 요청: FE
- 대상: BE

## 배경/이유

FE 인증, 온보딩, 마이페이지, 판매자 프로필 화면에서 현재 로그인 사용자 정보와 공개 회원 정보를 조회해야 한다. 현재 BE에는 `Member` 엔티티와 인증은 있으나 `/api/me`, 회원 상세, 프로필 이미지, 판매자 요약, 마이페이지 집계 API가 없다.

## 현재 BE 구현 확인

- `/api/me` 없음
- `/api/users/{id}` 회원 상세 없음
- `/api/users/{id}/business` 없음
- 팔로워/팔로잉 API 없음
- 마이페이지 요약/판매자 프로필 API 없음

## 요청 API

### 1. 내 정보 조회

```http
GET /api/me
Authorization: Bearer {accessToken}
```

응답 최소 필드:

```json
{
  "id": 1,
  "email": "user@example.com",
  "name": "홍길동",
  "nickname": "vintagelover",
  "phoneNumber": "010-1234-5678",
  "profileImageUrl": null,
  "memberType": "GENERAL",
  "onboardingCompleted": true
}
```

요청 사항:

- FE 앱 시작 시 저장된 token의 유효성을 확인할 수 있도록 access token 기반 조회를 제공한다.
- 로그인 응답에 `user/nextStep`을 넣지 않는다면 `/api/me`는 필수다.
- `memberType` enum을 확정한다. 후보: `GENERAL`, `BUSINESS`.

### 2. 내 정보 수정

```http
PATCH /api/me
Authorization: Bearer {accessToken}
Content-Type: application/json
```

요청 후보:

```json
{
  "nickname": "vintagelover",
  "phoneNumber": "010-1234-5678",
  "postalCode": "06236",
  "address": "서울 강남구 테헤란로 212",
  "detailAddress": "3층"
}
```

요청 사항:

- 온보딩 기본 정보 저장 API와 마이페이지 수정 API를 같은 endpoint로 쓸지 분리할지 확정한다.
- 닉네임 중복 검증 endpoint 또는 PATCH 오류 코드를 확정한다.
- 주소를 단일 문자열로 저장할지 `postalCode/address/detailAddress`로 분리할지 확정한다.

### 3. 공개 회원/판매자 프로필 조회

```http
GET /api/users/{userId}
```

응답 후보:

```json
{
  "id": 31,
  "nickname": "빈티지장인",
  "profileImageUrl": null,
  "coverImageUrl": null,
  "description": "",
  "followerCount": 1284,
  "followingCount": 12,
  "productCount": 37,
  "liveCount": 4,
  "isFollowing": false,
  "businessVerified": true
}
```

요청 사항:

- 비회원 조회 가능 여부를 확정한다.
- 로그인 사용자 기준 `isFollowing`을 포함한다.
- 판매자 프로필에서 노출할 상품/라이브 목록 endpoint를 확정한다.

### 4. 마이페이지 요약

```http
GET /api/users/{userId}/mypage
Authorization: Bearer {accessToken}
```

응답 후보:

```json
{
  "user": {
    "id": 1,
    "nickname": "vintagelover",
    "profileImageUrl": null,
    "memberType": "GENERAL",
    "businessVerificationStatus": "NONE"
  },
  "counts": {
    "orders": 3,
    "sales": 2,
    "wishes": 10,
    "followers": 12,
    "unreadNotifications": 4
  },
  "pointBalance": 120000
}
```

요청 사항:

- FE가 여러 도메인 API를 조합하지 않고 마이페이지 첫 화면을 그릴 수 있는 요약 API가 필요한지 검토해 달라.
- business verification 상태 enum을 확정한다. 후보: `NONE`, `PENDING`, `APPROVED`, `REJECTED`.

## FE 관련 파일

- `FE/src/domains/auth/stores/authStore.ts`
- `FE/src/domains/onboard/api/onboarding.ts`
- `FE/docs/frontend/api/api-index.md`
- `FE/docs/frontend/decisions/open-questions.md`
- 추후 `FE/src/domains/my`
