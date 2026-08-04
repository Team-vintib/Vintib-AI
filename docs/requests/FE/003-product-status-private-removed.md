# 상품 상태 `PRIVATE` 제거 알림

**요청자 파트**: BE
**대상 파트**: FE

## 배경/이유

기획 변경으로 미낙찰 상품(`AUCTION_FAILED`) 후속 처리 선택지가 "상시 판매 전환" / "경매 예정 유지"
둘로 확정되고, "비공개 전환" 선택지가 빠졌다. `product.sale_status`에서 `PRIVATE`로 들어오는 화살표가
이 선택지 하나뿐이었어서, 그 선택지가 없어지면 `PRIVATE`는 앞으로 절대 나오지 않는 값이 된다. 그래서
BE에서는 `PRIVATE`를 enum·DB 제약에서 완전히 제거했다(`SaleStatus`에 더 이상 존재하지 않음).

## 요청 내용

- FE 코드에 `PRIVATE`를 다루는 부분이 있어 공유한다. 지금 당장 동작이 깨지진 않는다(그냥 절대 매치되지
  않는 죽은 분기가 됨) — 편한 시점에 정리하면 된다.
  - `FE/src/domains/product/types/productDetail.types.ts` — `SaleStatus` 유니온 타입에서 `'PRIVATE'` 제거
  - `FE/src/domains/product/components/ProductPurchaseSummary.vue` — `isPurchaseDisabled`,
    `isCartDisabled` 계산 프로퍼티의 상태 배열에서 `'PRIVATE'` 제거
- API 응답의 `saleStatus` 필드는 현재(2026-08-04) `DRAFT | ON_SALE | AUCTION_SCHEDULED | AUCTION_IN_PROGRESS | SOLD` 중 하나만 온다. `AUCTION_FAILED`(미낙찰)는 아직 enum에 없다 — 경매 입찰/종료 자체가 미구현이라 그 상태가 될 경로가 없다(`docs/requests/BE/014-unsold-product-disposition.md` 참고). 추가되면 다시 알린다.

## 관련 자료

- `BE/docs/db/erd.md` §3-1 (상품 판매 상태 다이어그램·표)
- `.claude/plans/be/SY013-auction-failed-followup.md`
