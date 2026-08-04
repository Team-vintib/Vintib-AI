# 공개 회원/판매자 프로필 계약

**요청자**: BE → **대상**: FE

## API

| 기능 | Method | Endpoint | 인증 |
| --- | --- | --- | --- |
| 공개 프로필 조회 | GET | `/users/{userId}/profile` | 선택(비회원 가능) |
| 판매자 상품 목록 | GET | `/products?sellerId={userId}` | 선택(비회원 가능) |
| 판매자 라이브 목록 | GET | `/lives?hostId={userId}` | 선택(비회원 가능) |

`/users/{userId}`(본인 전용, MY-001)와는 별개 경로다 — 비회원 접근 가능, 민감정보 없음.

`products`/`lives`는 기존 목록 API에 필터만 추가한 것 — DRAFT/비공개 상태나 종료·취소 이력은 안 보인다(공개용).

## 프로필 응답

- `id`, `nickname`, `profileImageUrl`, `description`, `coverImageUrl`
- `followerCount`, `followingCount`, `productCount`, `liveCount`
- `isFollowing` — 비회원이면 항상 `false`
- `businessVerified` — 승인 여부만 boolean

```json
{
  "id": 10, "nickname": "seller", "profileImageUrl": null,
  "description": "빈티지 셀러입니다.", "coverImageUrl": null,
  "followerCount": 124, "followingCount": 20, "productCount": 8, "liveCount": 3,
  "isFollowing": false, "businessVerified": true
}
```

## 처리 결과

(FE 반영 후 기입)
