# 046 상시 판매 중인 상품의 가격 수정 요청

- **요청자 파트**: FE (김현수)
- **대상 파트**: BE
- **관련 이슈**: FE `S15P11A108-440` [AUCT-014] 미낙찰 상품 처리
- **작성일**: 2026-08-07

## 배경 / 이유

방송 종료 후 미판매 상품 관리 화면에서 **이미 상시 판매(정찰제)로 걸려 있는 상품의 가격을
바꿀 수 없다.** 방송에서 안 팔린 이유가 대부분 가격이라 판매자가 바로 조정하고 싶어 하는데,
지금은 경로가 없다.

- `PATCH /api/products/{id}/status`: `DRAFT`·`AUCTION_SCHEDULED`에서만 허용 →
  `ON_SALE` 상품은 `P003`(INVALID_PRODUCT_STATE)
- `PATCH /api/products/{id}`: 요청 본문에 `price` 필드가 없음
- 우회 경로(`auction-schedule`로 경매 예정 전환 → `status`로 재지정)는 순간적으로
  판매 방식이 바뀌고 가격이 비는 중간 상태가 생겨 쓰지 않았다.

## 요청 내용

**상시 판매 중인 상품의 가격을 바꿀 수 있게 해 주세요.** 둘 중 어느 쪽이든 좋습니다.

1. `PATCH /api/products/{id}/status`를 `ON_SALE`에서도 허용 (가격만 갱신, 판매 방식·상태 유지)
   - 이 경우 **FE는 수정할 게 없습니다.** 지금 그 엔드포인트를 그대로 호출하고 있어서,
     허용 상태만 넓히면 바로 동작합니다.
2. 또는 `PATCH /api/products/{id}` 본문에 `price`(선택) 추가

판매된 상품(`SOLD`)이나 경매 진행 중(`AUCTION_IN_PROGRESS`) 상품은 당연히 거절해 주세요.

## 관련 자료

- BE: `ProductService#registerDirectSale`, `Product#registerDirectSale`, `ProductUpdateRequest`
- FE: `LiveUnsoldProductItem.vue`(가격 수정하기 → `convertProductToDirectSale`)
- 계획: `docs/plans/FE/HS041-broadcast-end-dashboard-polish.md`
