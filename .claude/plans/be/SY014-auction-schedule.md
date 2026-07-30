# 경매 상품 등록 (PROD-003)

## 배경/목표

기능 정의서 PROD-003("경매 상품 등록")을 구현한다: `DRAFT` 상태 상품을 경매 예정(`AUCTION_SCHEDULED`)
상태로 등록한다. 시작가·증액 단위·경매 시간은 이 단계에서 다루지 않는다 — "경매 시작 전에 설정한다"고
명시돼 있고, 그건 이미 있는 `POST /lives/{liveId}/auctions`(AUCT-001, 경매 도메인)의 영역이다.

이 브랜치는 PROD-002/003 스토리("판매 방법별 추가 정보 등록") 중 아직 안 된 경매 등록 쪽만 다룬다.
`AUCTION_FAILED` 제거·PROD-004(`ON_SALE → AUCTION_SCHEDULED`) 관련 리워크는 다른 브랜치
(`feat/211-item-sale-type`, 이미 푸시됨)에서 처리했고 이 브랜치와는 별개다 — 여기서는 손대지 않는다.

## 작업 내용

- `Product.scheduleAuction()`은 이미 있다(`saleType=AUCTION`, `price=null`,
  `saleStatus=AUCTION_SCHEDULED`) — 새로 안 만들어도 된다.
- 새 서비스 메서드 `scheduleAuction(sellerId, productId)`: 소유권 확인 → 소스 상태가 `DRAFT`가
  아니면 `INVALID_PRODUCT_STATE` → `product.scheduleAuction()` 호출. 요청 바디는 없다(시작가 등은
  여기서 안 받으므로).
- 새 엔드포인트 `PATCH /products/{id}/auction-schedule` (요청 바디 없음) → 200 + `ApiResponse<ProductResponse>`.
  `registerDirectSale`(`/status`)과 대칭되는, "경매 예정으로 등록"만 전담하는 엔드포인트.
- `APIs.md` "상품(Products)" 섹션에 "경매 상품 등록 | PATCH | /products/{id}/auction-schedule | ✓ | PROD-003" 행 추가.
- Swagger 문서화, 서비스 단위 테스트(한글 메서드명) 추가.

## 구현 목록

- [x] `product/service/ProductService.java`에 `scheduleAuction(sellerId, productId)` 추가
- [x] `product/controller/ProductController.java`에 `PATCH /{id}/auction-schedule` 추가
- [x] 서비스 테스트: `DRAFT`에서 성공, `DRAFT`가 아니면 400, 본인 소유 아니면 403, 존재하지 않으면 404
- [x] Swagger 어노테이션
- [x] `APIs.md` 행 추가
- [x] `BE:verify` 통과 확인 (`BUILD SUCCESSFUL`, ProductServiceTest 30개 전부 통과)

## 완료

구현 완료.

## 확인 필요한 미결정 사항

- 없음. `ON_SALE → AUCTION_SCHEDULED`(PROD-004, 자유 전환의 나머지 방향)는 이 계획 범위 밖이며,
  나중에 이 서비스 메서드의 소스 상태 가드에 `ON_SALE`을 추가하는 식으로 확장하면 된다(다른
  브랜치에서 이미 그렇게 했던 패턴과 동일).