# 042 포인트 내역에서 입찰 보류/해제 숨김 요청

## 1. 요청 개요

- 요청 파트: 사용자 요청 (루트 세션에서 접수)
- 대상 파트: BE
- 요청 목적: `GET /api/users/{id}/points/logs`(포인트 내역)에 경매 입찰 중 생기는 `BID_HOLD`/`BID_RELEASE` 원장이 그대로 노출된다. 사용자에게는 입찰 보류·보류 해제가 아니라, 그 경매에서 **낙찰되어 실제로 상품을 구매하게 된 경우만** 내역에 보이면 된다.
- 우선순위: P3 (완화됨 — 아래 참고)
- **진행 상황**: FE는 우선 `getPointTransactions`(`FE/src/domains/point/api/pointApi.ts`)에서 응답을 받은 뒤 `BID_HOLD`/`BID_RELEASE`를 클라이언트에서 걸러내는 임시 조치를 적용했다. 화면에는 이미 안 보이므로 **급하지 않다**. 다만 클라이언트 필터링이라 `meta.totalElements`/`totalPages`는 걸러내기 전 값 그대로라 페이지네이션이 완전히 맞물리지 않는다 — 정확한 페이지네이션을 위해서는 여전히 서버 쪽에서 걸러주는 게 맞다.

## 2. 배경

- `PointCommandAdapter`(`BE/src/main/java/com/ssafy/backend/auction/port/PointCommandAdapter.java`)는 입찰마다 `holdForBid`로 `BID_HOLD` 원장을, 상위 입찰에 밀리거나 유찰되면 `releaseHoldForAuction`으로 `BID_RELEASE` 원장을 남긴다. 낙찰 시에는 `convertHoldToPayment`가 `BID_RELEASE` 1건 + `PAYMENT` 1건을 함께 남긴다.
- `PointService.getTransactions`(`BE/src/main/java/com/ssafy/backend/point/service/PointService.java:62`)와 `PointTransactionRepository.findByMember_IdOrderByCreatedAtDesc`는 타입 구분 없이 전체 원장을 그대로 페이지네이션해서 돌려준다. 그래서 입찰마다 생기는 `BID_HOLD`/`BID_RELEASE`가 사용자 화면 내역에 계속 쌓여, 낙찰과 무관한 보류·해제까지 다 노출된다.
- 낙찰로 이어진 경우는 이미 `PAYMENT` 원장(`refType=ORDER`)이 별도로 남으므로, `BID_HOLD`/`BID_RELEASE`를 숨겨도 "낙찰해서 구매한 내역" 자체는 그대로 보인다.

## 3. 요청 내용

- `GET /users/{id}/points/logs` 응답(및 페이지네이션 total)에서 `type`이 `BID_HOLD`/`BID_RELEASE`인 원장을 제외해 달라. 원장 자체(잔액 추적용 append-only 기록)는 그대로 남기고, 조회 결과에서만 걸러내면 된다 — 예: `PointTransactionRepository`에 `findByMember_IdAndTypeNotInOrderByCreatedAtDesc(memberId, List.of(BID_HOLD, BID_RELEASE), pageable)` 같은 쿼리를 추가해 `getTransactions`에서 사용.
- `GET /users/{id}/withdrawals`(출금 내역)는 이미 `WITHDRAW` 타입만 조회하므로 영향 없음 — 확인만 부탁한다.

## 4. 관련 자료

- `BE/src/main/java/com/ssafy/backend/point/service/PointService.java`
- `BE/src/main/java/com/ssafy/backend/point/repository/PointTransactionRepository.java`
- `BE/src/main/java/com/ssafy/backend/auction/port/PointCommandAdapter.java`
