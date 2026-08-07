# JY013 라이브 정찰 구매도 상품 큐에서 즉시 빠지게 한다

## 배경/목표

라이브에서 **경매로 낙찰되면** 상품이 모든 시청자의 상품 큐에서 바로 사라진다. 그런데 **정찰가로
즉시 구매하면 산 사람 화면에서만 사라지고 다른 시청자에게는 그대로 남는다.**

### 왜 갈리는가 (양쪽 코드로 확인)

경매는 마감할 때 `AuctionCloseScheduler`가 `/topic/lives/{liveId}/auctions` 로 스냅샷을 쏘고,
FE `LiveWatchPage.applyAuctionSnapshot()` 이 `SUCCESS` 를 보고 큐의 `saleStatus` 를 `SOLD` 로
바꾼다(`LiveWatchPage.vue:350`).

정찰 구매(`OrderService.createOrder`)는 `product.markSold()` 와 판매자 알림까지 정상으로
하지만 **STOMP 를 하나도 쏘지 않는다.** BE 의 `convertAndSend` 11곳 어디에도 주문 관련이 없다.

### FE 는 이미 자기 몫을 하고 있다

확인 결과 FE 쪽에 부족한 것은 없다.

- `orderApi.createOrder(productId, liveId?)` 가 **`liveId` 를 보낸다.** `LiveWatchPage.vue:541`
  이 `createOrder(product.id, currentLive.id)` 로 호출하므로 `Order.live` 가 채워지고,
  방송 종료 요약의 정찰 판매 집계(JY011)도 정상 동작한다
- 구매 성공 직후 `product.saleStatus = 'SOLD'`(`LiveWatchPage.vue:542`) 로 **구매자 본인 화면은
  이미 갱신된다**

즉 **결함은 BE 한 곳뿐이다 — 전파가 없다.** FE 가 추가로 할 일은 새 토픽 구독 하나다.

## 설계 판단

### 1. 새 토픽을 판다 — 기존 토픽 재사용은 안 된다

- `/topic/lives/{liveId}/auctions` 는 경매 스냅샷 모양이다. 정찰 판매를 가짜 경매로 실어
  보내면 FE 핸들러가 존재하지 않는 경매를 그리게 된다
- `/topic/lives/{liveId}/product` 는 **현재 소개 중인 상품**(NOW 배지)이다. 의미가 다르다

그래서 **`/topic/lives/{liveId}/product-sold`** 를 새로 만든다. 기존 `/product` 와 한 글자
차이라 헷갈릴 수 있지만, `/products` 로 두면 더 헷갈린다(복수형은 편성 목록으로 읽힌다).

### 2. 전파 대상은 `request.liveId()` 가 아니라 편성 정보에서 찾는다

FE 가 `liveId` 를 보내 주지만, **전파 대상은 그 값으로 정하지 않는다.** `LiveProduct` 에서
그 상품이 **진행 중(LIVE) 방송에 편성돼 있는지** 찾아 그 방송으로 쏜다.

이유는 `ProductDetailView.vue:305` 다 — 상품 상세 화면은 `createOrder(product.value.id)` 로
`liveId` 없이 산다. **라이브 밖에서 사도 그 상품이 진행 중 방송에 편성돼 있으면 시청자 큐에서
빠져야 한다.** 이미 팔린 상품이 큐에 남아 있으면 시청자가 눌렀다가 에러를 본다. 요청값만
믿으면 이 경우를 통째로 놓친다.

편성 정보로 찾으면 FE 가 보낸 값과 어긋날 일도 없다 — 라이브에서 산 경우 두 값이 같은
방송을 가리키고, 편성돼 있지 않으면 애초에 쏠 이유가 없다.

`ux_live_product_active` 가 `(live_id, product_id)` 라 한 상품이 여러 방송에 걸릴 수는 있지만,
그중 `status = LIVE` 인 것은 사실상 하나다. 둘 이상이면 로그만 남기고 건너뛴다(방송을 잘못
고르는 것보다 낫다).

**`request.liveId()` 는 계속 그대로 쓴다.** 그건 "어느 방송의 실적으로 집계할지"를 정하는
값이라 목적이 다르다 — 라이브 밖 구매를 방송 실적으로 잡으면 안 되기 때문이다.

### 3. 브로드캐스트는 커밋 이후 — 컨트롤러에서 쏜다

`LiveController.changeCurrentProduct` · `AuctionCloseScheduler.closeOne` 과 같은 규칙이다.
트랜잭션 안에서 쏘면 롤백 시 **시청자 화면에서만 상품이 사라진 채로 남는다.**

`OrderService.createOrder` 는 `@Transactional` 이므로 서비스가 쏘면 커밋 전이 된다. 그래서
서비스는 "쏠 대상"을 응답에 실어 돌려주고 **`OrderController` 가 커밋 이후 쏜다.**

### 4. 경매 낙찰에는 이 이벤트를 추가하지 않는다

FE 가 이미 `/auctions` 로 처리하고 있다. 여기에도 쏘면 같은 상품을 두 번 처리하게 된다.
이 이벤트는 **정찰 판매 전용**이고, payload 의 `soldVia` 로 그 사실을 명시한다.

## 구현 목록

- [ ] `LiveProductSoldResponse` 신설 — `liveId`, `productId`, `saleStatus`(항상 `SOLD`),
      `soldVia`(`DIRECT_SALE`), `soldAt`. Swagger `@Schema` 포함
- [ ] `LiveProductRepository` — 진행 중 방송에 편성된 활성 연결 조회 메서드 추가
      (`live.status = LIVE AND removed_at IS NULL`)
- [ ] `OrderService` — 전파 대상을 찾는 조회 메서드를 분리한다. `createOrder` 의 반환 타입은
      건드리지 않는다(호출부·테스트 파급이 크다)
- [ ] `OrderController.createOrder` — 커밋 이후 `/topic/lives/{liveId}/product-sold` 발행
- [ ] 테스트 — 편성 상품 구매 시 발행 / 미편성 상품은 발행 안 함 / 방송이 LIVE 가 아니면
      발행 안 함
- [ ] FE 요청 문서 — 새 토픽 구독 하나

## FE 가 해야 할 일 (요청 문서로 넘긴다)

**`/topic/lives/{liveId}/product-sold` 구독 하나뿐이다.** 받으면 큐의 해당 상품 `saleStatus` 를
`SOLD` 로 바꾼다 — `applyAuctionSnapshot` 의 SUCCESS 처리와 같은 동작이다.

구매자 본인은 이미 로컬에서 갱신하므로(`LiveWatchPage.vue:542`) 자기 이벤트를 다시 받아도
결과가 같다. 멱등이라 따로 걸러낼 필요가 없다.

## 검증

- [ ] 시청자 A/B 가 같은 방송을 볼 때, A 가 정찰 구매하면 **B 의 큐에서도** 즉시 빠진다
- [ ] 구매자 본인 화면은 지금처럼 즉시 빠진다(이벤트를 또 받아도 깨지지 않는다)
- [ ] 라이브 밖 상품 상세에서 사도 진행 중 방송의 큐에서 빠진다
- [ ] 포인트 부족으로 주문이 실패하면 아무것도 발행되지 않는다
- [ ] CI 동일 `./gradlew build` 통과
