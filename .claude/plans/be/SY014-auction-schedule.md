# 경매 상품 등록 (PROD-003) + 경매 전환 (PROD-004 나머지 절반)

## 배경/목표

기능 정의서 PROD-003("경매 상품 등록")을 구현한다: `DRAFT` 상태 상품을 경매 예정(`AUCTION_SCHEDULED`)
상태로 등록한다. 시작가·증액 단위·경매 시간은 이 단계에서 다루지 않는다 — "경매 시작 전에 설정한다"고
명시돼 있고, 그건 이미 있는 `POST /lives/{liveId}/auctions`(AUCT-001, 경매 도메인)의 영역이다.

이 브랜치를 만들 당시엔 PROD-002/003 스토리("판매 방법별 추가 정보 등록") 중 경매 등록 쪽만
다룰 계획이었고, `AUCTION_FAILED` 제거·PROD-004(`ON_SALE → AUCTION_SCHEDULED`) 관련 리워크는
다른 브랜치(`feat/211-item-sale-type`)에서 처리했었다. 이후 두 브랜치를 pull/merge하면서 이 브랜치가
그 리워크 결과까지 받았고, 자연스럽게 PROD-004의 나머지 절반(`ON_SALE → AUCTION_SCHEDULED`)도
같은 자리(`scheduleAuction`)에서 마저 구현했다 — `registerDirectSale`이 `DRAFT`/`AUCTION_SCHEDULED`
양쪽을 다 받도록 확장했던 것과 동일한 패턴.

### 병합 후 발견한 문제와 수정

pull 후 충돌 해결 과정에서 죽은 코드가 되살아났다:
- `ProductService.resolveAuctionFailure()`가 삭제된 `SaleStatus.AUCTION_FAILED`와 삭제된
  `ProductAuctionResultRequest`를 참조한 채로 남아있었음 → 메서드 전체 삭제.
- `ProductController`의 `PATCH /{id}/auction-result` 엔드포인트도 같은 이유로 컴파일 불가 →
  엔드포인트 전체 삭제.
- `Product.scheduleAuction()` 엔티티 메서드가 아예 빠져 있었음(서비스는 호출하는데 정의가 없음) →
  복원.
- `ProductServiceTest.java`에 테스트 하나가 깨진 채로 중복 삽입돼 있었음(메서드 시그니처 두 개가
  하나의 `{ }` 안에 겹쳐 있어 컴파일 자체가 안 됐음) → 중복 블록 삭제(정상 버전이 이미
  `미낙찰_상품을_상시_판매로_전환한다()`로 파일에 존재했음).

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
- [x] `scheduleAuction` 가드를 `DRAFT || ON_SALE`로 확장 (PROD-004 나머지 절반)
- [x] 서비스 테스트: `DRAFT`/`ON_SALE`에서 성공, 그 외 상태면 400, 본인 소유 아니면 403, 존재하지
      않으면 404
- [x] Swagger 어노테이션 (두 소스 상태 모두 반영)
- [x] `APIs.md` 행 갱신 (관련 기능 ID `PROD-003, PROD-004`)
- [x] 병합 후 되살아난 죽은 코드 제거(`resolveAuctionFailure`, `/auction-result` 엔드포인트),
      빠졌던 `Product.scheduleAuction()` 복원, 깨진 중복 테스트 정리
- [x] `BE/docs/db/erd.md` 라벨 문구 정리 후 `export-erd.sh` 재실행
- [x] `BE:verify` 통과 확인 (`BUILD SUCCESSFUL`, ProductServiceTest 26개 전부 통과)

## 완료

구현 완료. 이로써 `DRAFT ↔ ON_SALE ↔ AUCTION_SCHEDULED` 전환이 전부 구현됐다(PROD-002~005).