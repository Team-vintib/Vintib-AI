# 041 찜 해제 API path 의미 확정

- **작성자 파트**: BE (서윤) / **대상 파트**: FE
- **작성일**: 2026-08-07
- **원 요청**: `docs/requests/BE/004-social-notification-contract.md` §4/§6(wish delete path의
  `{productId}` 의미 확정) — 이 항목까지 해소되어 004 문서는 삭제했다.

## 결론: `{id}`는 product id다

```
DELETE /api/users/{userId}/wishes/{id}
```

`WishController.unwish(...)`가 `id`를 그대로 `WishService.unwish(memberId, productId)`에
넘기고, 찜(`Wish`)은 `(member_id, product_id)` 복합키라 **별도 wish row PK 자체가 없다**. 즉
`{id}` 자리에는 지금 하고 계신 대로 **상품 id**를 넣으면 됩니다.

새로 바뀐 건 없습니다 — 코드는 원래부터 이렇게 동작하고 있었고, 그 사실이 문서로 전달만 안
된 상태였습니다.

## 참고

- `BE/src/main/java/com/ssafy/backend/social/controller/WishController.java` (경로 주석에
  "별도 찜 PK가 없어(복합키) 상품 ID를 그대로 받는다 — TryOnController와 동일한 표기 관례" 명시)
- `BE/src/main/java/com/ssafy/backend/social/service/WishService.java` `unwish(Long memberId, Long productId)`
