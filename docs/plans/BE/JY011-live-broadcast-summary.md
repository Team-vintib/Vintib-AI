# JY011 방송 종료 요약·유찰 목록 (Phase 8-b)

## 배경/목표

Phase 8에서 경매 마감·낙찰·유찰이 코드로 들어왔다. 그 결과를 **방송 단위로 모아 보여 줄 조회가
없다** — FE 방송 종료 대시보드(`-438`)는 판매 수·총 판매액을 하드코딩하고 있고, 미낙찰 상품 처리
화면(`-440`)은 "이 방송에서 안 팔린 상품"을 물어볼 곳이 없다.

## 작업 내용

### 1. 방송별 유찰 상품 목록 — `GET /api/lives/{liveId}/unsold-products`

- 호스트 본인만. 근거는 **`auction` 테이블의 `live_id` + `status = 'FAILED'`** —
  상품 판매 상태로 찾으면 다른 방송에서 유찰된 것까지 섞인다.
- 판매자가 다음 행동(상시 판매 전환 / 재경매)을 고를 수 있을 만큼만 담는다:
  `productId`, `title`, `thumbnailUrl`, 마지막 경매의 `startPrice`.

### 2. 방송 종료 요약 — `GET /api/lives/{liveId}/summary` (FE 요청 018)

- 호스트 본인만. `soldCount` / `unsoldCount` / `totalSales` / `results[]`.
- `results[]`는 **편성 상품 전체**가 기준이다(경매를 안 건 상품도 UNSOLD로 나와야 대시보드가
  방송 전체를 보여 준다).

**집계 범위 — 낙찰 + 방송 중 즉시구매 둘 다.**

이건 경매 실적이 아니라 **방송 실적**이라 정찰가로 팔린 것도 들어가야 한다. 문제는 주문만 봐서는
어느 방송에서 팔렸는지 알 수 없다는 것 — 경매 낙찰은 `auction.live_id`로 이어지지만 즉시구매는
경매를 거치지 않는다.

그래서 **`orders`에 `live_id`(nullable)를 추가한다.** FE에 라이브 즉시구매 화면이 아직 없어
한때 미루려 했으나, 곧 만든다는 확인을 받아 지금 함께 넣는다 — 나중에 넣으면 그 사이 팔린
주문이 요약에서 영구히 빠진다.

- 즉시구매: `OrderCreateRequest`에 선택 필드 `liveId`. FE가 라이브에서 살 때만 실어 보낸다.
- 낙찰: 서버가 `auction.getLive()`로 알아서 채운다(파생 가능하지만 비워 두면 같은 질문에 답이
  두 갈래가 된다).
- 집계에서 낙찰이 즉시구매보다 우선한다. 환불·취소된 주문은 판매액에서 뺀다.
- `results[]`의 `soldVia`가 `AUCTION`/`DIRECT_SALE`로 경로를 구분한다.

### 3. 유찰 상품 재편집 허용 (FE 요청 007 잔여분)

유찰된 상품은 `AUCTION_SCHEDULED`에 머무는데 `Product.isEditable()`이 `DRAFT`/`ON_SALE`만 허용해
"안 팔렸으니 설명 고쳐서 다시 걸자"가 400으로 막힌다. `AUCTION_SCHEDULED`를 허용에 넣는다 —
**`AUCTION_IN_PROGRESS`는 계속 막는다**(진행 중 경매의 상품 정보가 바뀌면 입찰자가 본 것과
달라진다). 경매 흐름에서 나온 요구라 상품 도메인이지만 여기서 처리한다.

### 4. 시청자 수에서 호스트 제외

판매자가 자기 방송 화면을 열면 그 STOMP 세션도 시청자로 잡혀, 아무도 안 보는 방송이 늘 "1명"으로
보였다. 집계가 세션 ID 집합이라 누가 누구인지 몰랐던 것인데, **CONNECT 시점에 심어 둔
`StompPrincipal(memberId)`이 이미 있어** 구독 이벤트에서 꺼내 쓸 수 있다.

- `LiveSessionEventListener`가 `accessor.getUser()`에서 `memberId`를 꺼내 넘기고,
  판단(`isHost`)은 `LiveViewerService`가 한다.
- 비회원은 조회 없이 바로 통과시킨다 — 토큰 없이 붙은 세션은 호스트일 수 없다.
- 회원이면 `existsByIdAndHost_Id` 한 방으로 확인한다(구독마다 불리므로 방송을 통째로 읽지 않는다).
- 호스트 세션도 `session → live` 매핑은 남긴다. 시청자 집합에 없어 나갈 때 `SREM`이 0을 돌려주고
  브로드캐스트도 안 일어나므로, 정리 경로를 한 갈래로 유지하는 편이 단순하다.
- 최고 시청자 수(`peak_viewer_count`)도 자동으로 같은 기준을 따른다.

### 5. 문서 정리

- `006` 인덱스 — 삭제된 `005` 행 제거, 표에서 빠져 있던 `007`·`008`·`009`·`018`·`019`·`020` 추가,
  `004` 행 갱신
- `004` §3.2 `AUCTION_WON` 반영 완료 표시 + §3.1 **알림 `type`/`refType` 확정표** 작성
  (정윤 도메인 4종 확정, 서윤 5종 미정 표시)
- `027` §4(완료된 3건) 정리, `024`·`025`에 `030` 포인터 추가
- 해소된 `007`·`018` 삭제. `010`(카테고리 선택 입력)은 **필수 유지로 확정**돼 삭제
- FE 핸드오프 문서 신규 — 위 계약 + 즉시구매 집계 관련 확인 요청

## 구현 목록

- [x] `orders.live_id` 추가 — `Order` 엔티티·`OrderCreateRequest.liveId`·`OrderService`,
      낙찰 주문은 `createAuctionWin`이 자동으로 채움
- [x] `OrderRepository.findLiveDirectSaleOrders` — 이 방송의 경매 아닌 주문(환불·취소 제외)
- [x] `AuctionRepository`에 방송별 결과 조회 추가(`live_id` 기준, `FAILED`/`SUCCESS`)
- [x] `LiveSummaryService` — 편성 상품 + 경매 결과를 합쳐 요약·유찰 목록 조립
- [x] `GET /api/lives/{liveId}/unsold-products` + 응답 DTO
- [x] `GET /api/lives/{liveId}/summary` + 응답 DTO(`soldVia` 포함)
- [x] `Product.isEditable()`에 `AUCTION_SCHEDULED` 추가
- [x] 시청자 수에서 호스트 제외 — `LiveViewerService.enter`가 `memberId`를 받아 판단,
      `LiveRepository.existsByIdAndHost_Id` 추가
- [x] 테스트 — 호스트 아님 403, 낙찰/유찰/경매 미설정 상품이 섞인 요약, 유찰 목록이 다른 방송
      유찰분을 안 물고 오는지, 유찰 상품 수정 허용·진행 중 상품 수정 차단
- [x] Swagger + 문서 정리(위 4번)
