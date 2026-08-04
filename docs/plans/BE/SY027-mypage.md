# SY027 — 마이페이지 (MY-001~009)

## Context

에픽 `S15P11A108-207 [MY] 마이페이지` 아래 스토리 9개(MY-001~009)를 각각 커밋으로 나눠 구현한다. 브랜치는 이미 만들어져 있는 `feat/207-user-info`를 그대로 쓴다(스토리 MY-001의 Jira description에도 이 브랜치명이 적혀 있어 확인됨).

**조사 결과, 9개 중 3개는 이미 완료돼 있다** — 새로 만들 필요가 없다:
- **MY-006(찜/팔로우 목록 관리)**: `GET /api/users/{userId}/wishes`(찜 목록), `GET /api/users/{userId}/followings`(팔로잉 목록) 이미 있음(`social/controller/WishController.java`, `FollowController.java`). 대응 Jira 태스크(445, 446)는 상태만 "해야 할 일"로 안 갱신된 것.
- **MY-008(사업자 정보/인증 상태 관리)**: 방금 전 세션에서 완성(`business/controller/BusinessInfoController.java`).
- **MY-009(상품 찜/해제)**: `social/controller/WishController.java`의 `wish`/`unwish`로 이미 완성(대응 태스크 312도 Jira상 완료 처리됨).

실제로 새로 구현할 것은 **MY-001(조회만 빠짐)/002/003/004/005/007** 6개다. MY-005(라이브 관리)는 `live` 패키지(정윤 담당)에 새 엔드포인트가 필요한데, 사용자 확인 결과 **직접 추가하기로 확정**했다.

추가로, FE 요청 문서(`docs/requests/BE/011-user-mypage-contract.md`) §3.4의 **마이페이지 요약 API**(`GET /api/users/{userId}/mypage`)는 이번에 만드는 모든 도메인(주문/포인트 등)이 갖춰져야 의미가 생기므로, 6개 구현 후 마지막에 보너스로 추가한다. 같은 문서 §3.3의 **공개 프로필**(`GET /api/users/{userId}`, 비로그인 조회)은 MY-001~009 어디에도 없는 별개 스토리라 이번 범위에서 제외한다 — `GET /api/users/{userId}`는 **본인 전용 조회**(인증 필요)로만 구현한다.

## 재사용할 기존 패턴/DTO

- `requireSelf` IDOR 방지 패턴(`TryOnProfileController`, `WishController` 등과 동일) — 전 엔드포인트에 적용.
- 목록 카드 DTO는 새로 안 만들고 기존 걸 감싸는 패턴을 따른다(`WishItemResponse`가 `ProductResponse`를 감싸는 것과 동일):
  - MY-002(판매 상품 목록): `product/dto/response/ProductResponse` 그대로 재사용.
  - MY-003/004(구매/판매 내역): 신규 `OrderListItemResponse`가 `ProductResponse`를 필드로 감싼다.
  - MY-005(라이브 목록): 기존 `live/dto/response/LiveListItemResponse`와 `LiveService`의 카테고리/시청자수 배치 조회 로직(`toListItem` 주변)을 그대로 재사용.
- "상위 도메인이 하위 도메인 레포지토리를 직접 참조" 컨벤션(`WishService`→`ProductRepository`, `InvoiceService`→`BusinessInfoRepository`와 동일) — 마이페이지 요약 API에서 order/social/notification/point 레포지토리를 직접 참조할 때 그대로 적용.
- `PageResponse<T>` — 목록 API 전부 이 래퍼를 쓴다(기존 관례).
- 에러코드는 최대한 기존 것 재사용: `USER_NOT_FOUND`, `MEMBER_FORBIDDEN`, `PRODUCT_NOT_FOUND`, `NOT_PRODUCT_OWNER`, `ORDER_NOT_FOUND`, `INVOICE_FORBIDDEN` 계열, `NOT_LIVE_HOST`, `INSUFFICIENT_POINTS`. 정말 안 맞는 경우에만 최소로 신규 추가.

## 커밋별 구현 내용

### 1) `[S15P11A108-124]` MY-001 회원 정보 관리 — 조회 엔드포인트만 추가

수정/관심사 조회·수정은 이미 `UserController`/`UserService`에 있다. 빠진 건 **조회** 하나뿐.

- `member/dto/response/MemberProfileResponse`에 `businessVerificationStatus`(String: `NONE`/`PENDING`/`APPROVED`/`REJECTED`) 필드 추가.
- `UserService`에 `BusinessInfoRepository` 주입, `getProfile(requesterId, targetId)` 추가 — `requireSelf` 후 `Member` + `BusinessInfo`(없으면 NONE)를 조합해 응답.
- `UserController`에 `GET /api/users/{id}` 추가.
- 기존 `updateBasicInfo`/`completeOnboarding`도 이 필드를 채우도록 `MemberProfileResponse.from` 시그니처에 businessStatus 파라미터 추가(또는 오버로드).

### 2) `[S15P11A108-125]` MY-002 판매 상품 관리

- 신규 `product/controller/MyProductController.java` — `@RequestMapping("/api/users/{userId}/products")` (기존 `ProductController`는 `/api/products` 고정이라 별도 컨트롤러가 자연스러움, `TryOnController`/`TryOnProfileController` 분리와 같은 이유).
- `ProductRepository`에 `findBySeller_Id(Long, Pageable)` 추가(선택적 `saleStatus` 필터는 JPQL로, 없으면 전체 상태 — DRAFT/PRIVATE 포함, 본인만 보는 화면이므로 전부 노출).
- `ProductService`(또는 신규 `MyProductService`)에 조회 메서드 추가, 응답은 `ProductResponse` 그대로.
- `requireSelf` 체크.

### 3) `[S15P11A108-126]` MY-003 구매/낙찰 내역 조회

- 신규 `order/dto/response/OrderListItemResponse` — `orderId`, `product`(`ProductResponse`), `sellerId`, `sellerNickname`, `orderPrice`, `status`, `createdAt`.
- `OrderRepository`에 `findByBuyer_Id(Long, Pageable)` 추가.
- 신규 `order/service/OrderService`(기존 `InvoiceService`와 별개), `order/controller/OrderController` 신규.
- `GET /api/users/{userId}/orders/purchases` — `requireSelf`.

### 4) `[S15P11A108-127]` MY-004 판매/정산 내역 조회

- `OrderRepository`에 `findBySeller_Id(Long, Pageable)` 추가.
- `OrderService`에 조회 메서드 추가, 같은 `OrderListItemResponse` 재사용(구매자 관점 필드 대신 buyer 정보로 채움 — 또는 필드에 buyer/seller 양쪽 다 넣고 관점에 따라 프론트가 골라 쓰게 함. 간단히 후자로 통일: `buyerId/buyerNickname/sellerId/sellerNickname` 둘 다 포함).
- `GET /api/users/{userId}/orders/sales` — `requireSelf`.
- **"정산" 자체는 수수료 계산이나 실제 정산 트리거가 없다** — `order.status`가 `SETTLED`인지만으로 정산 완료 여부를 표시하고, 정산액은 `orderPrice` 그대로 쓴다(수수료 정책 없음). 이 조회 API는 완전히 동작하지만, 애초에 주문 생성 API가 없어 실제 데이터는 DB에 직접 심어야 확인 가능하다(BIZ-002 때와 동일한 제약).

### 5) `[S15P11A108-128]` MY-005 라이브 관리

- `LiveRepository`에 `findByHost_Id(Long, Pageable)` 추가(전체 상태 — SCHEDULED/LIVE/ENDED/CANCELED 다 노출, 관리 화면이므로).
- `LiveService`에 `getMyLives(hostId, pageable)` 추가 — 기존 `getPublicLives`의 카테고리/시청자수 배치 조회+`toListItem` 매핑 로직을 재사용.
- `LiveController`에 `GET /api/users/{userId}/lives` 추가(정윤 담당 패키지지만 직접 추가하기로 확정) — `requireSelf` 실패 시 기존 `NOT_LIVE_HOST`(L004) 재사용.

### 6) `[S15P11A108-130]` MY-007 포인트/출금 관리 — `point` 패키지 신규

담당 분배표에 `point`는 이미 서윤 담당으로 명시돼 있다(`README.md`). 스키마(`point_account`, `point_transaction`)는 이미 있고 엔티티/서비스/컨트롤러가 전무하다.

- `point/entity/PointTransactionType.java` — `CHARGE/BID_HOLD/BID_RELEASE/PAYMENT/SETTLEMENT/REFUND/WITHDRAW`(스키마 CHECK 그대로).
- `point/entity/PointAccount.java` — 공유 PK 1:1(`BusinessInfo`와 동일 패턴), `available/bidHeld/tradeEscrow/settling/withdrawing`, `updatedAt`.
- `point/entity/PointTransaction.java` — `member`, `type`, `amount`(부호 있음), `balanceAfter`, `refType`/`refId`(nullable), `createdAt`.
- `point/repository/PointAccountRepository.java`, `PointTransactionRepository.java`(`findByMember_Id` 최신순 페이지네이션).
- `point/service/PointService.java`:
  - `getBalance(memberId)`: `PointAccount`가 없으면 그 자리에서 0으로 생성(lazy init) 후 반환 — 별도 회원가입 훅을 만드는 대신 조회 시점 upsert로 처리한다(가입 경로가 여러 개여도 놓칠 위험이 없다).
  - `getTransactions(memberId, pageable)`.
  - `charge(memberId, amount)`: 결제 연동 없이 금액만 받아 `available += amount` + `PointTransaction`(CHARGE, `+amount`) 기록 — 출금 테스트용 잔액을 만들 수 있게 간단히 함께 만든다(실결제 검증 없음, 데모/테스트 전용임을 Swagger 설명에 명시).
  - `requestWithdrawal(memberId, amount)`: `available >= amount` 검증(부족하면 기존 `INSUFFICIENT_POINTS` W001) → `available -= amount`, `withdrawing += amount` → `PointTransaction`(WITHDRAW, `-amount`) 기록. **출금 "완료" 처리(관리자 승인)는 범위 밖** — BIZ-001의 사업자 승인과 동일하게, 신청 이후는 DB 직접 조작으로만 완료 처리된다.
- `point/controller/PointController.java`:
  - `GET /api/users/{userId}/point` — 잔액 조회
  - `GET /api/users/{userId}/point/transactions` — 원장 목록
  - `POST /api/users/{userId}/point/charges` — 충전(테스트/데모 전용, 실결제 없음)
  - `POST /api/users/{userId}/point/withdrawals` — 출금 신청

### 7) `[S15P11A108-207]` 보너스 — 마이페이지 요약 API

에픽 키를 직접 쓴다(특정 스토리에 속하지 않는 통합 API라, `[S15P11A108-27]` chore 커밋 때처럼 에픽 키를 그대로 쓴 전례를 따른다).

- `member/dto/response/MypageSummaryResponse` 신규 — `user`(id/nickname/profileImageUrl/memberType/businessVerificationStatus), `counts`(orders/sales/wishes/followers/unreadNotifications), `pointBalance`.
- 카운트용 레포지토리 메서드 추가: `OrderRepository.countByBuyer_Id`/`countBySeller_Id`, `WishRepository.countByMember_Id`, `NotificationRepository.countByMember_IdAndReadFalse`(`FollowRepository.countByFollowing_Id`는 이미 있음).
- `UserService.getMypageSummary(requesterId, targetId)`, `UserController`에 `GET /api/users/{userId}/mypage` 추가.

## 확인 필요한 미결정 사항

- MY-004 정산액은 수수료 없이 `orderPrice` 그대로 — 나중에 수수료 정책이 생기면 조정.
- MY-005 라이브 목록은 취소/종료된 방송도 다 노출(관리 목적) — 필요하면 나중에 상태 필터 추가.
- 포인트 충전은 실결제 검증 없이 금액만 받는 테스트/데모 전용 엔드포인트로 확정(사용자 승인).
- 포인트 출금 "완료" 처리(관리자 승인)는 사업자 승인과 동일하게 범위 밖 — 신청까지만 구현(사용자 승인).

## 구현 목록

계획 대비 실제 구현은 일부 경로/구조가 바뀌었다 — 확정된 최종 계약은 `docs/requests/FE/018-mypage-contract.md`와 `docs/APIs.md` 참고.

- [x] MY-001: `MemberProfileResponse`에 `businessVerificationStatus` 추가, `UserService.getProfile`, `UserController GET /{id}`
- [x] MY-002: `MyProductController`, `ProductRepository.findBySeller_Id`, 서비스 메서드
- [x] MY-003/004: 계획은 `orders/purchases`+`orders/sales` 두 엔드포인트였으나, 실제로는 `GET /users/{id}/orders?role=BUYER|SELLER` 하나로 통합(`MyOrderController`)하고 `GET /orders/{orderId}` 상세 조회를 추가했다. `OrderListItemResponse`, `OrderRepository.findByBuyer_Id`/`findBySeller_Id`, `OrderService`
- [x] MY-005: 계획은 신규 `GET /api/users/{userId}/lives` 엔드포인트였으나, 실제로는 기존 `GET /lives`에 `hostId` 쿼리 파라미터를 추가하는 방식으로 구현(`LiveController`/`LiveService.getLives`) — 신규 엔드포인트/`LiveRepository.findByHost_Id`는 만들지 않았다
- [x] MY-007: `point/` 패키지 전체(entity 3개, repository 2개, service, controller) — 잔액/내역/충전. 경로는 계획의 `point`(단수)가 아니라 `points`(복수)로 확정했고, 내역 명칭도 `transactions`가 아니라 `logs`로 확정했다. 출금은 계획대로 `point` 하위가 아니라 `WithdrawalController`(`/users/{id}/withdrawals`) 독립 리소스로 만들었고, 계획엔 없던 출금 내역 조회(`GET /users/{id}/withdrawals`)도 추가했다
- [x] 보너스: `MypageSummaryResponse`, 각 레포지토리 count 메서드, `UserController GET /{userId}/mypage` — 최초 구현 때는 범위 제외(`docs/requests/FE/012`에 명시)했다가 이후 요청으로 추가 구현했다
- [x] 각 서비스 Mockito 테스트
- [x] `./gradlew build` 통과 확인(로컬 `bootRun` E2E 검증은 각 커밋 시점에 curl로 수행)
- [x] 커밋 6~7개로 분리(MY-006/008/009는 이미 완료라 커밋 없음)

## 테스트

각 신규 서비스(`UserService.getProfile`, `MyProductService`(또는 `ProductService` 확장), `OrderService`, `LiveService.getMyLives`, `PointService`)에 Mockito 단위 테스트 최소 1개 이상, 기존 테스트 스타일(한글 메서드명) 그대로.

## 검증 방법

1. `./gradlew build` — 전체 테스트 통과 확인.
2. 로컬 `bootRun` + curl로 각 엔드포인트 실호출 검증(BIZ 때와 동일 방식) — 특히 포인트 lazy-init(최초 조회 시 0 잔액 생성), 출금 신청 후 available/withdrawing 버킷 이동, 마이페이지 요약의 각 count가 실제 데이터와 일치하는지 확인.
3. 커밋마다 해당 스토리 범위 파일만 정확히 포함되는지 `git status`로 확인 후 분리 커밋.