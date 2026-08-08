# HS041 — 방송 종료 대시보드·유찰 처리 보강

- Jira: `S15P11A108-438`(`[AUCT-012/013 | FE] 방송 종료 대시보드 구현`),
  `S15P11A108-440`(`[AUCT-014 | FE] 미낙찰 상품 처리 UI 구현`) / 에픽 `S15P11A108-209` `[AUCT]`
- 브랜치: `feat/209-end-dashboard-polish`

## 배경/목표

판매자 방송 종료 대시보드에서 미판매 상품이 판매 방식과 무관하게 `—`로만 보이고, 유찰 상품을
`경매 예정 유지`로 넘길 때 확인 단계 없이 즉시 처리된다. 방송 결과를 판매 방식까지 함께 읽히게
하고, 되돌릴 수 없는 선택에는 확인 단계를 둔다.

## 기준 자료

- `docs/plans/FE/HS025-seller-auction-result.md`(방송 종료 대시보드)
- `docs/plans/FE/HS026-unsold-product-restore.md`(미낙찰 상품 처리)
- `docs/requests/FE/031-broadcast-summary-unsold-contract.md`(요약·유찰 계약)
- BE `LiveBroadcastSummaryResponse`, `LiveUnsoldProductResponse`

## 확인한 계약 한계

`GET /api/lives/{id}/summary`의 `results`는 `productId`·`title`·`thumbnailUrl`·`status`·
`finalPrice`·`soldVia`만 준다. **판매 방식(`saleType`)과 등록가가 없어** 미판매 상품이
정찰제인지 경매 예정인지 구분할 수 없고, 정찰제 미판매 상품의 가격도 알 수 없다.

다만 판매자 화면은 이미 `GET /api/lives/{id}`로 편성 상품 목록(`live.products`)을 들고 있고,
여기에는 `saleType`·`saleStatus`·`price`가 들어 있다. **추가 요청 없이** 이 목록을
`productId`로 이어 붙여 부족한 필드를 채운다. 상품 상세를 상품 수만큼 조회하는 방식은 쓰지 않는다.

응답에 직접 실어 주는 편이 깔끔하므로 `docs/requests/BE`에 요청 문서를 함께 남긴다.

## 작업 내용

- 대시보드에 편성 상품 목록을 넘겨 결과 행마다 판매 방식을 판별한다.
  - `saleType === 'DIRECT_SALE'` → `정찰제`
  - `saleType === 'AUCTION'` 또는 `saleStatus`가 `AUCTION_SCHEDULED`/`AUCTION_IN_PROGRESS` → `경매 예정`
  - 둘 다 비어 있으면 가격 유무로 추정하고, 그래도 모르면 배지를 숨긴다.
- 미판매 정찰제 상품은 `—` 대신 등록가를 표시한다. 미판매 경매 상품은 값이 없으므로 `—`를 유지한다.
- 미판매 상품 목록은 제품명과 함께 `정찰제`/`경매 예정` 배지를 보여 준다.
- 유찰 상품에서 `경매 예정 유지`를 누르면 바로 처리하지 않고 확인 단계를 띄운다.
  `상시 판매로 전환`의 가격 입력 + 확인 흐름은 그대로 둔다.
- 결과 행의 가격과 판매 방식 라벨을 `가격 → 라벨` 순서로 두고 두 칸을 고정 폭으로 잡아
  행마다 세로줄이 맞게 한다.

### 관리 대상을 미판매 상품 전체로 넓힘

`GET /api/lives/{id}/unsold-products`는 **경매를 걸었다가 유찰된 상품만** 준다(BE
`LiveBroadcastResultService#getUnsoldProducts` — 마지막 경매가 `FAILED`인 상품). 그래서 경매를
한 번도 시작하지 않은 방송은 목록이 비고, 미판매 상품이 있어도 관리 화면 진입 버튼 자체가
나오지 않아 확인할 수 없었다.

FE에서 **BE 유찰 목록 + 요약의 미판매 결과**를 `productId`로 합쳐 관리 대상을 만든다. 경매를 건
적이 없는 상품은 시작가가 없으므로 편성 상품의 등록가를 기본값으로 쓰고, 그것도 없으면 비운다
(`LiveUnsoldProduct.startPrice`를 `number | null`로 넓힘).

### 판매 방식에 따라 선택지를 다르게

이미 정찰제로 걸려 있던 상품에 `상시 판매로 전환`은 의미가 없다. 항목이 이미 호출하는 상품
상세의 `saleType`으로 갈라, 선택지 자체를 바꾼다.

| 상품                 | 선택지                                                                                                                                               |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| 경매 예정(가격 없음) | `상시 판매로 전환`(가격 입력 → `PATCH /products/{id}/status`) · `경매 예정 유지`(확인만)                                                             |
| 정찰제(가격 있음)    | `가격 수정하기`(현재가 프리필 → `PATCH .../status`) · `경매 예정으로 전환`(확인 → `PATCH .../auction-schedule`) · `유지하기`(확인만, 서버 호출 없음) |

정찰제 상품에 `유지하기`가 없으면 가격을 고치거나 경매로 돌리는 것 말고는 처리할 방법이 없어,
"남은 상품을 모두 처리해 주세요" 게이트를 통과하지 못한다. 경매 상품의 `경매 예정 유지`와
같은 성격이라 서버 호출 없이 화면에서만 처리 완료로 표시한다(완료 배지: `상시 판매 유지`).

두 엔드포인트 모두 상품 등록의 판매 방식 설정에서 쓰던 것을 그대로 재사용한다
(`convertProductToDirectSale`, `scheduleProductAuction`).

판매 방식은 **편성 상품 목록에서 받은 값**을 기준으로 한다. 상품 상세(`GET /products/{id}`)는
상품에 따라 500이 나서(요청 029 — 이 방송의 상품 47·49·61이 모두 실패) 그것만 믿으면 문구가
경매용으로 굳어버린다. 상세는 브랜드·상태 보강용으로만 쓰고, 실패해도 화면은 정상 동작한다.

처리 결과(`productId`/`saleType`/`price`)는 방송 화면까지 올려 편성 상품에 반영한다. 대시보드로
돌아갔을 때 상품별 결과의 가격과 배지가 방금 바꾼 값으로 보여야 하기 때문이다.

**가격 수정은 BE 대기 중이다.** `PATCH /products/{id}/status`가 `ON_SALE`을 허용하지 않아
정찰제 상품의 가격만 바꾸는 경로가 없다(요청 048). BE가 그 상태를 허용해 주면 지금 호출이 그대로
통하므로 FE는 손댈 게 없다. 그때까지는 `P003` 응답을 "가격 수정은 아직 준비 중"으로 안내한다.

## 구현 파일

- `FE/src/domains/live/components/LiveBroadcastEndDashboard.vue`
- `FE/src/domains/live/pages/LiveBroadcastPage.vue`
- `FE/src/domains/live/components/LiveUnsoldProductItem.vue`
- `FE/src/domains/live/components/LiveUnsoldManage.vue`
- `FE/src/domains/auction/types/liveAuction.types.ts`
- `docs/requests/BE/047-broadcast-summary-sale-type.md`(별도 커밋, main 대상)
- `docs/requests/BE/048-direct-sale-price-update.md`(별도 커밋, main 대상)

## 확인 사항

- 편성 상품과 결과가 `productId`로 매칭되지 않으면(상품 삭제 등) 배지·가격을 숨기고 기존 표시를 유지한다.
- 판매된 상품의 표시(`낙찰`/`판매`, 판매 경로, 최종가)는 건드리지 않는다.
- 확인 단계는 화면 안에서 처리하며 `window.confirm`은 쓰지 않는다(라이브 화면 UI 톤 유지).
- 실제 화면은 판매자 계정과 종료된 방송이 필요하므로, 정적 검사·빌드 후 실환경에서 최종 확인한다.
