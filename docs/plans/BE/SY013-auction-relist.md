# 경매 예정 상품의 상시 판매 전환 (PROD-004) — `AUCTION_FAILED` 없이 재설계

`AUCTION_SCHEDULED → ON_SALE` 전환은 PROD-004("판매 방식 자유 전환")의 한쪽 방향이자, 미낙찰
후속 처리(PROD-005/AUCT-014)가 실제로 쓰는 경로이기도 하다. 커밋은 PROD-004(`S15P11A108-236`)
기준으로 남긴다.

## 배경/목표

기획이 다시 바뀌었다. 미낙찰(입찰자 없이 경매 종료)을 별도 상태(`AUCTION_FAILED`)로 만들지 않는다.
대신:

- 경매가 입찰자 없이 끝나도 상품은 그냥 `AUCTION_SCHEDULED`에 **그대로 머문다** (경매 도메인이 실패
  시 product를 건드릴 필요가 아예 없어짐).
- 판매자는 `AUCTION_SCHEDULED` 상품을 아무 때나 골라 가격을 넣고 `ON_SALE`로 전환하거나, 그냥
  둬서 다음 라이브에서 다시 경매하게 할 수 있다. "그대로 둔다"는 선택은 **아무 것도 안 하면 되므로
  API가 필요 없다.**
- "이 상품이 예전에 한 번 실패했었다"는 이력은 사라지지 않는다 — `product.sale_status`에는 남지
  않지만 `auction` 테이블에 그 시도가 `status='FAILED'`인 row로 남는다.

이 계획은 이전 버전(`AUCTION_FAILED`를 두고 `ON_SALE`/`AUCTION_SCHEDULED` 중 고르게 하는 안,
`S15P11A108-237`로 이미 커밋됨)을 대체한다. 그때 만든 것 중 상당 부분을 되돌린다:
`SaleStatus.AUCTION_FAILED`, `Product.scheduleAuction()`, `ProductAuctionResultRequest`,
`ProductService.resolveAuctionFailure()`, `PATCH /products/{id}/auction-result` — 전부 제거.

(PRIVATE 상태 제거는 이 되돌림과 무관하다 — 그건 그대로 유지한다.)

## 작업 내용

- `SaleStatus`에서 `AUCTION_FAILED` 제거. CHECK 제약·`comments.sql`도 함께.
- 기존 `PATCH /products/{id}/status`(`registerDirectSale`, 지금은 `DRAFT`만 허용)의 소스 상태 가드를
  **`DRAFT` 또는 `AUCTION_SCHEDULED`** 로 넓힌다. "가격 설정해서 상시 판매로 전환"이라는 동작 자체는
  두 소스 상태에서 동일해서, 새 엔드포인트를 만들 필요가 없다 — 기존 걸 그대로 재사용한다.
- `AUCTION_SCHEDULED` 유지(아무 것도 안 함)는 API가 필요 없으므로 만들지 않는다.
- ERD 다이어그램 갱신: `AUCTION_SCHEDULED --> ON_SALE`(PROD-005, 신규 화살표) 추가,
  `AUCTION_IN_PROGRESS --> AUCTION_FAILED` 화살표를 `AUCTION_IN_PROGRESS --> AUCTION_SCHEDULED`
  (입찰자 없이 종료, AUCT-014)로 교체. 상태 표에서 `AUCTION_FAILED` 행 제거, 그 상태를 별도로 뒀던
  이유를 설명하던 콜아웃을 "왜 별도 상태를 안 두는가"로 바꿔 쓴다.
- `APIs.md`: 이전에 추가했던 "미낙찰 상품 후속 처리" 행 제거. 기존 "판매 가격 설정 및 상시 판매 등록"
  행의 관련 기능 ID를 `PROD-002` → `PROD-002, PROD-005, AUCT-014`로 갱신.
- Swagger 설명 갱신(`registerDirectSale`이 이제 두 소스 상태를 받는다는 것).
- 이전 계획에서 추가했던 `resolveAuctionFailure` 관련 테스트 전부 제거하고, `registerDirectSale`
  테스트에 "`AUCTION_SCHEDULED` 상품도 상시 판매로 전환할 수 있다" 케이스를 추가한다. 기존
  "`DRAFT`가 아니면 예외" 테스트는 이제 `AUCTION_SCHEDULED`도 허용되므로, 거절돼야 하는 다른 상태
  (`SOLD`)로 바꿔서 유지한다.

## 구현 목록

- [x] `product/entity/SaleStatus.java` — `AUCTION_FAILED` 제거
- [x] `product/entity/Product.java` — CHECK 목록에서 `AUCTION_FAILED` 제거, `scheduleAuction()` 제거
      (이번 계획에서 호출하는 곳이 없음 — 나중에 "경매 예정 상태 변경" 브랜치가 필요할 때 새로 추가)
- [x] `product/dto/request/ProductAuctionResultRequest.java` 삭제
- [x] `product/service/ProductService.java` — `resolveAuctionFailure` 삭제, `registerDirectSale`
      가드를 `DRAFT || AUCTION_SCHEDULED`로 확장
- [x] `product/controller/ProductController.java` — `PATCH /{id}/auction-result` 엔드포인트 삭제,
      `registerDirectSale` Swagger 설명 갱신
- [x] `ProductServiceTest.java` — `resolveAuctionFailure` 관련 테스트 삭제, `registerDirectSale`에
      `AUCTION_SCHEDULED` 소스 케이스 추가, "DRAFT 아니면 예외" 테스트를 `SOLD` 기준으로 교체
- [x] `BE/docs/db/schema.sql`, `comments.sql` 수정 후 `bash BE/docs/db/regen.sh`
- [x] `BE/docs/db/erd.md` 수정 후 `bash BE/docs/db/export-erd.sh`
- [x] `APIs.md` 갱신 (신규 행 제거, 기존 행 관련 기능 ID `PROD-002, PROD-005, AUCT-014`로 갱신)
- [x] `BE:verify` 통과 확인 (`BUILD SUCCESSFUL`, ProductServiceTest 21개 전부 통과)
- [x] `constraint-test.sql` 재검증 (통과 11 / 실패 0, 이 변경과 무관하게 그대로 유지)

## 완료

구현 완료. `S15P11A108-237`로 커밋됐던 `AUCTION_FAILED` 버전을 걷어내고 이 방식으로 다시 커밋한다.
`S15P11A108-236`(PROD-004)으로 커밋. PROD-003(`DRAFT → AUCTION_SCHEDULED`, 경매 상품 최초 등록)은
별도 브랜치·별도 계획으로 진행하고, 그게 자리잡으면 이 서비스 메서드의 소스 상태 가드에
`ON_SALE`을 추가하는 식으로 재사용한다.

## 확인 필요한 미결정 사항

- 없음. `AUCTION_SCHEDULED --> AUCTION_IN_PROGRESS`(경매 시작, AUCT-002)와 실패 후
  `AUCTION_IN_PROGRESS --> AUCTION_SCHEDULED` 복귀는 경매 도메인(정윤) 쪽에서 구현할 때, 이 계획대로면
  product 쪽을 아예 안 건드려도 된다는 점만 공유하면 된다.
