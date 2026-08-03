# 마이페이지 API 계약

**요청자**: BE → **대상**: FE

## API 목록

| 기능 | Method | Endpoint | 비고 |
| --- | --- | --- | --- |
| 내 정보 조회 | GET | `/users/{id}` | `businessVerificationStatus`/`profileImageUrl`/`description`/`coverImageUrl` 포함 |
| 내 정보 수정 | PATCH | `/users/{id}` | 온보딩과 겸용, 전체 교체(부분 수정 아님) |
| 소개글 수정 | PATCH | `/users/{id}/bio` | `{description}`만(선택), 전체 교체 |
| 프로필 이미지 업로드/삭제 | POST·PUT·DELETE | `/users/{id}/profile-image`(`/upload-url`) | 아래 이미지 업로드 참고 |
| 커버 이미지 업로드/삭제 | POST·PUT·DELETE | `/users/{id}/cover-image`(`/upload-url`) | 위와 동일 흐름 |
| 판매 상품 관리 | GET | `/users/{id}/products` | 본인 전용, 비공개 상태 포함 |
| 구매/판매 내역 | GET | `/users/{id}/orders?role=BUYER\|SELLER` | `role` 필수 |
| 주문 상세 | GET | `/orders/{orderId}` | 당사자만 |
| 라이브 관리 | GET | `/lives?hostId={id}` | 본인이면 종료·취소 이력까지 |
| 포인트 잔액 / 내역 / 충전 | GET·GET·POST | `/users/{id}/points`, `/points/logs`, `/points/charges` | 충전은 테스트 전용 |
| 출금 신청 / 내역 | POST·GET | `/users/{id}/withdrawals` | 신청까지만(승인 없음) |
| 마이페이지 요약 | GET | `/users/{id}/mypage` | 카운터 + 포인트 잔액 |

전부 인증 필요(본인만), 실패 시 403.

## 이미지 업로드 (presigned 2단계, 상품 이미지 `FE/001`과 동일)

1. `POST .../profile-image/upload-url`(또는 `cover-image/upload-url`) — `{contentType}`(jpeg/png/webp) → `{key, uploadUrl, expiresInSeconds}`
2. 받은 `uploadUrl`로 브라우저가 직접 PUT
3. `PUT .../profile-image`(또는 `cover-image`) — `{key}` → 확정, 최종 공개 URL이 회원 정보에 저장됨
4. `DELETE .../profile-image`(또는 `cover-image`) — 삭제

## 마이페이지 요약 응답 예시

```json
{
  "user": { "id": 1, "nickname": "vintagelover", "profileImageUrl": null, "memberType": "GENERAL", "businessVerificationStatus": "NONE" },
  "counts": { "orders": 0, "sales": 0, "wishes": 3, "followers": 12, "unreadNotifications": 1 },
  "pointBalance": 10000
}
```

## 주의

- 주문 생성 API가 아직 없어 `orders`, `counts.orders`/`counts.sales`는 항상 빈 값/0이다.
- `bio`에서 `coverImageUrl` 필드는 제거됐다 — 커버 이미지는 이제 업로드 API로만 설정한다.

## FE 요청 사항

- 마이페이지 사이드바에서 **"포인트·출금" 메뉴 항목을 없애달라**(`myMockData.ts`의
  `{ id: 'points', label: '포인트·출금' }`). 관련 API 자체는 그대로 유지한다.

## 처리 결과

(FE 반영 후 기입)
