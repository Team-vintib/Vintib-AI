# 035 상품 목록 판매완료(SOLD) 제외 — 답변 및 FE 조치 요청

- **요청자 파트**: BE (정윤)
- **대상 파트**: FE
- **관련 이슈**: FE `S15P11A108-562` [LIVE-003] 라이브 낙찰 상품 목록 반영 확인
- **관련 요청**: `docs/requests/BE/022-product-list-sold-exclusion.md` (답변 완료로 삭제)
- **작성일**: 2026-08-06

## 1. 목록 정책 → **(A) 기본 응답에서 SOLD 제외**로 결정, 반영 완료

`GET /api/products`가 이제 `DRAFT`와 `SOLD`를 모두 제외한다. FE는 별도 처리가 필요 없다.

| sale_status | 목록 노출 | 비고 |
| --- | --- | --- |
| `DRAFT` | ✕ | 등록 중(미공개) — 기존과 동일 |
| `ON_SALE` | ○ | 정찰제 중 |
| `AUCTION_SCHEDULED` | ○ | 경매 예정 |
| `AUCTION_IN_PROGRESS` | ○ | **경매 중은 남긴다** — 지금 방송에서 팔리는 물건이라 목록에서 방송으로 유입시켜야 한다 |
| `SOLD` | ✕ | 낙찰·즉시구매로 판매 완료 |

(C) 파라미터 방식은 두지 않았다. "팔린 상품은 목록에서 안 보인다"가 예외 없는 정책이면 호출부마다 파라미터를 붙이는 쪽이 빠뜨리기 쉽다. 나중에 "판매 완료까지 보고 싶다"는 화면이 실제로 생기면 그때 파라미터를 추가한다.

## 2. 상태 전이 → **구현 완료** (2026-08-05, `b6ad56a3`)

| 계기 | 상품 `saleStatus` |
| --- | --- |
| 경매 조건 설정(AUCT-001) | `AUCTION_SCHEDULED` |
| 경매 시작(AUCT-002) | `AUCTION_IN_PROGRESS` |
| **경매 낙찰(AUCT-012)** | **`SOLD`** |
| 경매 유찰 — 입찰 없이 종료(AUCT-014) | `AUCTION_SCHEDULED` (되돌림, 다음 방송에 다시 걸 수 있게) |
| 정찰제 즉시구매(SALE-002) | `SOLD` |

낙찰 마감은 1초 주기 스케줄러와 방송 종료 훅 두 경로 모두 같은 로직을 타므로, 종료 시각 도달·방송 강제 종료 어느 쪽으로 끝나도 `SOLD`가 된다. 목록 응답의 `saleStatus`로 확인할 수 있다.

검증 근거 (2026-08-06):

- 개발 DB 전수 대조 — 낙찰(`SUCCESS`) 경매 111건 중 상품이 `SOLD`가 아닌 건 **0건**.
- 종단 통합 테스트 신설(`AuctionWinToSoldIntegrationTest`) — 조건 설정 → 시작 → 입찰 → 마감까지 실제 DB로 태워 `SOLD` 전이·낙찰 주문 생성까지 확인.

## 2-1. "정찰제는 목록에서 빠지는데 경매만 안 빠진다"에 대해

두 경우 모두 `SOLD`가 되면 BE 취급은 완전히 같다. 상태값이 같은데 다르게 보일 방법은 없다. 차이는 **언제 바뀌느냐**다.

| | 상태가 바뀌는 시점 |
| --- | --- |
| 정찰제 즉시구매 | 구매 요청 **그 트랜잭션 안에서 즉시** — 응답이 성공이면 이미 `SOLD` |
| 경매 낙찰 | **서버의 1초 주기 스케줄러**가 마감할 때 |

그래서 **BE 서버가 내려가 있거나 재시작 중이면 경매만 안 바뀐 것처럼 보인다.** 실제로 로컬 개발 환경을 확인한 시점에 BE 프로세스가 떠 있지 않았고, 종료 시각이 지난 경매 18건이 `RUNNING`인 채로, 상품은 `AUCTION_IN_PROGRESS`인 채로 남아 있었다. BE 프로세스를 띄우자 **1초 안에 18건이 전부 마감**되고 입찰이 있던 8건은 상품이 `SOLD`로 바뀌었다. 로직 문제가 아니라 마감 주체가 서버라는 구조 차이다.

**유찰과 낙찰을 구분해 주세요.** 입찰이 하나도 없이 끝난 경매는 낙찰이 아니라 유찰이고, 상품은 `SOLD`가 아니라 `AUCTION_SCHEDULED`로 **되돌아간다**(다음 방송에 다시 걸 수 있어야 하므로). 목록에도 계속 남는 게 정상이다. 개발 DB 기준 유찰이 낙찰보다 많다(142건 대 111건). 확인하실 때 `GET /api/auctions/{auctionId}/winner`의 `status`가 `SUCCESS`인지 `FAILED`인지 먼저 봐 주세요.

## 3. FE 조치 필요 — 마이페이지 판매 상품 목록 엔드포인트 전환

`getMySellerProducts`(`FE/src/domains/my/api/myApi.ts`)가 공개 목록 `GET /api/products`를 첫 100건만 받아 클라이언트에서 `sellerId`로 거르고 있다. 이번 변경으로 **그 목록에서 SOLD가 빠지므로, 마이페이지 "판매 완료" 탭이 비게 된다.** (원래도 `DRAFT` 상품이 안 보이고, 100건 컷 때문에 상품이 많은 판매자는 누락되는 문제가 있었다.)

마이페이지 전용 엔드포인트로 바꿔 주세요.

```
GET /api/users/{userId}/products?page=0&size=20
Authorization: Bearer <accessToken>
```

- 본인이 등록한 상품 **전 상태**(`DRAFT` 포함)를 등록일 최신순으로 반환한다.
- 응답 형태는 공개 목록과 같다 — `ApiResponse<PageResponse<ProductResponse>>` (`saleStatus` 포함).
- 본인만 조회 가능하다. `userId`가 인증 주체와 다르면 403.
- 이미 배포돼 있는 API다(MY-002). 추가 작업 없이 호출부만 바꾸면 된다.

프로필 페이지(`/products?sellerId=`)는 그대로 두면 된다 — 남의 프로필에서 팔린 상품이 빠지는 것은 의도한 동작이다.

## 3-1. 마이페이지 탭이 경매 상품을 어느 탭에도 넣지 않습니다

`MyPage.vue`의 상품 필터가 `ALL` / `ON_SALE`(판매 중) / `SOLD`(판매 완료) 셋인데, `toMyProductStatus`가 `AUCTION_SCHEDULED`·`AUCTION_IN_PROGRESS`를 `AUCTION_SCHEDULED`로 매핑한다. 이 상태의 상품은 **"판매 중"에도 "판매 완료"에도 안 잡히고 "전체"에만 뜬다.** 상단 "판매중" 카운트(`productStatusCounts.onSale`)도 `ON_SALE`만 세므로 경매 상품은 빠진다.

경매가 아직 안 끝났거나 유찰된 상품이 "전체 탭에는 있는데 어느 상태에도 안 잡히는" 상태로 보이는 게 이 때문입니다. "경매 중/예정" 탭을 추가하거나, 경매 상품을 판매 중에 포함시키는 쪽으로 정리해 주세요. BE는 `AUCTION_SCHEDULED`와 `AUCTION_IN_PROGRESS`를 구분해 내려주므로 둘을 나눠 표시하는 것도 가능합니다.

참고로 BE의 `SaleStatus`는 `DRAFT` / `ON_SALE` / `AUCTION_SCHEDULED` / `AUCTION_IN_PROGRESS` / `SOLD` **다섯 개뿐**입니다. FE 타입에 있는 `AUCTION_FAILED`는 BE가 내려주지 않습니다 — 유찰은 상품 상태가 아니라 경매 행(`auction.status = FAILED`)으로만 남고 상품은 `AUCTION_SCHEDULED`로 돌아갑니다.

## 4. 확인 부탁 — 검색 결과의 SOLD

이번 변경은 상품 목록(`GET /api/products`)만 건드렸다. **검색(`GET /api/search`)은 아직 `DRAFT`만 제외하고 `SOLD`를 포함**한다. 검색에서도 빼는 게 맞다면 알려 주세요 — 요청 범위를 임의로 넓히지 않으려고 남겨 뒀습니다.

## 5. 참고 (BE 변경 내역)

- `BE/src/main/java/com/ssafy/backend/product/repository/ProductRepository.java` — `findWithFilter`에서 `SOLD` 제외
- `BE/src/test/java/com/ssafy/backend/product/repository/ProductListSoldExclusionTest.java` — 낙찰로 `SOLD`가 되면 목록에서 빠지고, 판매중·경매예정·경매중은 남는지 검증
- `BE/src/test/java/com/ssafy/backend/auction/service/AuctionWinToSoldIntegrationTest.java` — 조건 설정 → 시작 → 입찰 → 마감 종단 검증(낙찰 시 `SOLD` + 주문 생성, 유찰 시 `AUCTION_SCHEDULED` 복귀)
