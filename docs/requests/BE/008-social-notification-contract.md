# 008 Social/Notification API 요청

## 1. 요청 개요

- 요청 파트: FE
- 대상 파트: BE
- 요청 목적: 찜, 팔로우, 알림 API의 FE 연동 상태와 남은 계약 요청을 정리한다.
- 우선순위: P1
- 시연 필수 여부: 상품 상세 찜은 현재 시연 가능. 팔로우/알림 화면을 시연하면 추가 구현 필요.

## 2. 현재 연동 상태

- 연동 완료 API
  - `POST /api/users/{userId}/wishes`
  - `DELETE /api/users/{userId}/wishes/{productId}`
- FE 구현 완료 범위
  - 상품 상세 찜 추가/해제
  - 상품 목록/검색/상세에서 `isWished` 표시 후보
- 현재 임시 처리 또는 Mock 사용 여부
  - 팔로우/언팔로우 화면 연결은 아직 없다.
  - 알림 목록 화면은 route만 있고 실제 UI/연동은 제한적이다.

## 3. 추가 구현 요청

### 3.1 팔로우/언팔로우

- Method / Endpoint
  - `POST /api/users/{targetUserId}/followers`
  - `DELETE /api/users/{targetUserId}/followers`
- 요청 목적: 공개 프로필/검색 결과에서 사용자를 팔로우하거나 해제한다.
- FE 사용처: 검색 회원 카드, 공개 프로필, 판매자 영역
- 요청 데이터
  - Header: `Authorization: Bearer {accessToken}`
  - Path: `targetUserId`
- 응답 데이터
  - `targetUserId`: number
  - `isFollowing`: boolean
  - `followerCount`: number
- 응답 예시

```json
{
  "success": true,
  "data": {
    "targetUserId": 10,
    "isFollowing": true,
    "followerCount": 124
  },
  "error": null
}
```

### 3.2 팔로워/팔로잉 목록

- Method / Endpoint
  - `GET /api/users/{userId}/followers`
  - `GET /api/users/{userId}/followings`
- 요청 목적: 공개 프로필 또는 마이페이지에서 팔로워/팔로잉 목록을 표시한다.
- FE 사용처: 공개 프로필, 마이페이지
- 요청 데이터
  - Path: `userId`
  - Query: `page`, `size`
- 응답 데이터
  - `id`: number
  - `nickname`: string
  - `profileImageUrl`: string | null
  - `followerCount`: number
  - `productCount`: number
  - `isFollowing`: boolean
- 응답 예시

```json
{
  "success": true,
  "data": {
    "content": [
      {
        "id": 10,
        "nickname": "seller",
        "profileImageUrl": null,
        "followerCount": 124,
        "productCount": 8,
        "isFollowing": true
      }
    ],
    "page": 0,
    "size": 20,
    "totalElements": 1,
    "totalPages": 1,
    "hasNext": false
  },
  "error": null
}
```

### 3.3 알림 type/ref 문서화

- Method / Endpoint
  - `GET /api/users/{userId}/alerts`
  - `PATCH /api/users/{userId}/alerts/read-all`
  - `PATCH /api/users/{userId}/alerts/{id}`
- 요청 목적: 알림 목록에서 아이콘, 문구, 이동 대상을 안정적으로 분기한다.
- FE 사용처: 알림센터
- 요청 데이터
  - Header: `Authorization: Bearer {accessToken}`
- 응답 데이터
  - `id`, `type`, `title`, `message`, `isRead`, `refType`, `refId`, `createdAt`
- 응답 예시

```json
{
  "success": true,
  "data": {
    "content": [
      {
        "id": 1,
        "type": "BID_OUTBID",
        "title": "상위 입찰이 발생했습니다",
        "message": "다른 사용자가 더 높은 금액으로 입찰했습니다.",
        "isRead": false,
        "refType": "AUCTION",
        "refId": 1,
        "createdAt": "2026-07-31T12:00:00"
      }
    ]
  },
  "error": null
}
```

## 4. 기존 API 변경 요청

- 기존 요청·응답에서 변경할 내용
  - `DELETE /api/users/{userId}/wishes/{productId}`에서 path id가 wish row id인지 product id인지 문서화 요청
- 추가할 필드
  - 알림 item의 `refType`, `refId` enum 문서화
- 변경 영향 범위
  - 찜 해제 API adapter
  - 알림 클릭 이동

## 5. 보류 또는 시연 제외 범위

- 현재 구현하지 않아도 되는 기능
  - 팔로우/언팔로우 UI가 시연 범위가 아니면 보류 가능
  - 알림센터 화면을 시연하지 않으면 알림 목록/읽음 연결 보류 가능
- 추후 구현 예정 기능
  - 찜 목록 화면
  - 팔로워/팔로잉 목록 화면
  - 알림 실시간 push

## 6. 협의 필요 사항

- FE·BE 간 결정이 필요한 내용
  - wish delete path의 `{productId}` 의미 확정
  - 비회원 요청에서 `isWished`, `isFollowing`을 `false` 또는 `null` 중 무엇으로 줄지
  - 알림 `type`, `refType` enum 목록
- 아직 확정되지 않은 응답 구조나 정책
  - 팔로우 중복 요청 처리
  - 자기 자신 팔로우 요청 처리
  - 알림 읽음 처리 응답 body

## 7. 추가 요청 없음

- 이미 정상 연동된 API
  - 상품 상세 찜 추가
  - 상품 상세 찜 해제
- 기존 규격을 유지하면 되는 기능
  - 찜 목록 API endpoint 자체는 BE에 있으나 FE 화면이 없어 미연결
  - 알림 목록/읽음 API endpoint 자체는 BE에 있으나 FE 화면 정비 후 연결
