# 미낙찰 상품 후속 처리 API (+ PRIVATE 상태 제거)

## 배경/목표

기획 변경: 경매 종료 후 미낙찰 상품(`AUCTION_FAILED`)의 후속 처리는 **상시 판매 전환(`ON_SALE`) /
경매 예정 유지(`AUCTION_SCHEDULED`) 두 가지뿐**이다. 비공개(`PRIVATE`)는 선택지에서 빠진다.

`BE/docs/db/erd.md` §3-1 상태 다이어그램에서 `PRIVATE`로 들어오는 화살표는
`AUCTION_FAILED --> PRIVATE`(비공개 선택) **하나뿐이었다.** 그 선택지가 없어지면 `PRIVATE`는
시스템 전체에서 영원히 도달 불가능한 상태가 되므로, 상태 자체를 완전히 제거하기로 확인했다
(대안: 이번 기능에서만 선택지를 빼고 `PRIVATE`는 나중을 위해 남겨두는 방안도 있었지만, 다른
진입점이 생길 계획이 없어 죽은 코드로 남기지 않기로 함).

이 계획은 이전 [[SY013-auction-failed-followup]] 초안(3지선다: ON_SALE/AUCTION_SCHEDULED/PRIVATE)을
대체한다.

## 작업 내용 A — `PRIVATE` 상태 완전 제거 (이미 구현된 코드에 대한 정리)

- `SaleStatus` enum에서 `PRIVATE` 제거.
- `Product` 엔티티: `@CheckConstraint`의 `sale_status IN (...)` 목록에서 `'PRIVATE'` 제거.
  `isPrivate()`는 남는 조건이 `saleStatus == DRAFT` 하나뿐이라 이름이 더 이상 실상을 반영하지
  못한다 — **`isDraft()`로 이름을 바꾼다.** `isEditable()`는 `DRAFT || ON_SALE`로 단순화한다
  (`PRIVATE` 분기만 제거).
- `ProductService`: `HIDDEN_FROM_LIST`를 `List.of(SaleStatus.DRAFT)`로 축소. `isPrivate()` 호출부는
  이름 변경에 맞춰 `isDraft()`로 교체.
- `WishService`: `.filter(p -> !p.isPrivate())` → `.filter(p -> !p.isDraft())`로 교체.
- Swagger 설명 문구 정리: `ProductController`(목록 조회/상세 조회/수정/삭제 4곳), `WishController`(찜/찜
  목록 조회 2곳)에서 "DRAFT/PRIVATE" 언급을 "DRAFT"로, "판매완료(SOLD)·비공개(PRIVATE)" 언급을
  "판매완료(SOLD)"로 정리한다.
- DB 문서 3종 정리 후 재생성: `schema.sql`의 `ck_product_sale_status` CHECK 목록에서 `'PRIVATE'` 제거,
  `comments.sql`의 `sale_status` 코멘트에서 `PRIVATE` 제거 → `bash BE/docs/db/regen.sh`로
  `data-dictionary.md` 재생성.
- `erd.md`: mermaid 다이어그램에서 `AUCTION_FAILED --> PRIVATE` 줄 삭제, 상태 표에서 `PRIVATE` 행
  삭제, `AUCTION_FAILED` 관련 설명 문단에서 "비공개" 언급 정리 → `bash BE/docs/db/export-erd.sh`로
  이미지 재생성.
- 기존 테스트 수정(컴파일 깨짐 방지 + 의미 갱신): `ProductServiceTest`(`상품_목록_조회시_DRAFT와_PRIVATE_상태는_제외하고_조회한다`,
  `DRAFT_또는_PRIVATE_상품은_본인만_조회할_수_있다` 등 이름·내용에서 PRIVATE 제거),
  `WishServiceTest`(`SaleStatus.PRIVATE`를 쓰는 케이스들을 다른 비공개 상태 표현으로 교체하거나 제거).
- **FE에 알림**: FE `productDetail.types.ts`의 `SaleStatus` 유니온과
  `ProductPurchaseSummary.vue`의 상태 배열에 `'PRIVATE'`가 남아있다(그레도 동작은 깨지지 않는
  죽은 분기가 됨). `.claude/requests/fe/`에 계약 변경 요청 문서를 남긴다.

## 작업 내용 B — 미낙찰 상품 후속 처리 API (PROD-005, AUCT-014)

- **새 엔드포인트**: `PATCH /products/{id}/auction-result` (요청 바디: `nextStatus` + 조건부 `price`).
  기존 `/status`(DRAFT→ON_SALE 전용, PROD-002)와 소스 상태·의미가 달라 분리한다.
- 요청 DTO `ProductAuctionResultRequest(nextStatus, price)`:
  - `nextStatus`: `ON_SALE` / `AUCTION_SCHEDULED` 둘 중 하나 (`@NotNull`).
  - `price`: `nextStatus=ON_SALE`일 때만 필수, `AUCTION_SCHEDULED`면 없어야 한다. 조건부라 서비스
    계층에서 `ErrorCode.INVALID_INPUT_VALUE`로 직접 검증한다(이 코드베이스에 커스텀 크로스필드
    검증기 선례가 없음).
- 소스 상태 가드: 상품이 `AUCTION_FAILED`가 아니면 기존 `ErrorCode.INVALID_PRODUCT_STATE`(400).
- 소유권 검증: 기존 `NOT_PRODUCT_OWNER`(403) 패턴 재사용.
- 엔티티 메서드:
  - `ON_SALE` 선택 → 기존 `registerDirectSale(price)` 재사용(가드 없는 메서드라 재사용 가능).
  - `AUCTION_SCHEDULED` 선택 → 새 메서드 `scheduleAuction()` 추가(`saleType=AUCTION`,
    `saleStatus=AUCTION_SCHEDULED`, `price=null`). **가드 없이 범용으로 만들어서** 나중에
    "경매 예정 상태 변경"(PROD-003/004) 브랜치가 `DRAFT`/`ON_SALE` 소스에서도 이 메서드를 그대로
    재사용하도록 한다 — 그쪽은 자신만의 서비스 메서드(다른 소스 상태 가드)만 추가하면 된다.
- 응답은 기존 `ProductResponse` 재사용(200 + `ApiResponse<ProductResponse>`).
- `APIs.md` "상품(Products)" 섹션에 "미낙찰 상품 후속 처리 | PATCH | /products/{id}/auction-result | ✓ | PROD-005, AUCT-014" 행 추가.
- Swagger 문서화, 서비스 단위 테스트(한글 메서드명) 추가.

## 구현 목록

### PRIVATE 제거
- [x] `product/entity/SaleStatus.java` — `PRIVATE` 제거
- [x] `product/entity/Product.java` — CHECK 목록, `isPrivate()`→`isDraft()` 개명, `isEditable()` 단순화
- [x] `product/service/ProductService.java` — `HIDDEN_FROM_LIST`, `isDraft()` 호출로 교체
- [x] `social/service/WishService.java` — `isDraft()` 호출로 교체
- [x] `product/controller/ProductController.java`, `social/controller/WishController.java` — Swagger 설명 정리
- [x] `BE/docs/db/schema.sql`, `comments.sql` 수정 후 `bash BE/docs/db/regen.sh`
- [x] `BE/docs/db/erd.md` 수정 후 `bash BE/docs/db/export-erd.sh`
- [x] `ProductServiceTest`, `WishServiceTest`의 PRIVATE 관련 테스트 수정
- [x] `.claude/requests/fe/003-product-status-private-removed.md` 작성

### 미낙찰 후속 처리 API
- [x] `product/entity/Product.java`에 `scheduleAuction()` 추가 (`registerDirectSale()`는 기존 것 재사용)
- [x] `product/dto/request/ProductAuctionResultRequest.java` 신설 (`nextStatus` enum + `price`)
- [x] `product/service/ProductService.java`에 `resolveAuctionFailure(sellerId, productId, request)` 추가
- [x] `product/controller/ProductController.java`에 `PATCH /api/products/{id}/auction-result` 추가
- [x] 서비스 테스트 (한글 메서드명): 두 선택지 각각 성공, `AUCTION_FAILED`가 아닌 상태에서 시도(400),
      본인 소유 아님(403), `ON_SALE` 선택인데 가격 누락(400), `AUCTION_SCHEDULED` 선택인데 가격을
      같이 보낸 경우(400)
- [x] Swagger 어노테이션
- [x] `APIs.md` "미낙찰 상품 후속 처리" 행 추가 (기존 "판매 가격 설정 및 상시 판매 등록" 행의 관련
      기능 ID도 `PROD-002~005, PROD-007, AUCT-014` → `PROD-002`로 바로잡음 — 실제로는 그 endpoint가
      PROD-002만 구현하고 있었음)
- [x] `BE:verify` 통과 확인 (`BUILD SUCCESSFUL`, ProductServiceTest 26개·WishServiceTest 9개 전부 통과)

## 완료

구현 완료. `BE/docs/db/constraint-test.sql`을 실행해보니 이 계획과 무관한 기존 문제를 하나 발견했다 —
시드 데이터가 `product.category_id`(NOT NULL)를 채우지 않아 스크립트 자체가 처음부터 실패한다. 이건
이 브랜치 이전부터 있던 문제라 여기서 고치지 않았다.

## 확인 필요한 미결정 사항

- 없음. `AUCTION_FAILED` 진입 트리거(AUCT-014의 "경매 종료 시 상태 전환" 부분)는 경매 도메인 쪽 작업이라
  이 계획에 포함하지 않는다.
