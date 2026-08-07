# SY040 - 주문/배송/포인트 알림 4종 (004 §3.2 나머지)

## 배경/목표

`docs/requests/FE/004-social-notification-contract.md` §3.2 표에서 라이브·경매 알림 4종
(`LIVE_REMINDER`/`LIVE_STARTED`/`AUCTION_OUTBID`/`AUCTION_WON`)은 정윤 도메인 트리거라 이미
반영 완료됐다. 남아 있던 "서윤 확인 필요" 5개(`ORDER_PAID`/`SHIPMENT_STARTED`/
`SHIPMENT_COMPLETED`/`POINT_CHARGED`/`POINT_REFUNDED`/`WITHDRAW_COMPLETED`, 사실상 6개)를
이번에 붙인다.

## 작업 내용

### 1. `NotificationCommandPort` 위치 이동

지금 `live.port.NotificationCommandPort`/`NotificationCommandAdapter`는 라이브 도메인
전용처럼 패키지가 이름 붙어 있지만, 실제 구현(`NotificationCommandAdapter`)은
Member/문자열/Long만 받는 도메인 무관 코드다. order/point가 이걸 그대로 가져다 쓰면
"order가 live.port에 의존"하는 이상한 모양이 되므로, `notification.port` 패키지로
옮긴다(동작 변화 없는 기계적 이동).

- `notification.port.NotificationCommandPort`/`NotificationCommandAdapter`로 이동
- 기존 사용처(`AuctionService`, `AuctionCloseService`, `LiveService`, `LiveReminderService`
  + 테스트 3개) import 경로만 갱신 — 로직 변경 없음

### 2. 알림 6종

| 이벤트 | `type` | `refType` / `refId` | 수신자 | 트리거 위치 |
| --- | --- | --- | --- | --- |
| 상시 판매 결제 완료 | `ORDER_PAID` | `ORDER` / order id | **판매자** | `OrderService.createOrder` |
| 송장 등록 | `SHIPMENT_STARTED` | `ORDER` / order id | 구매자 | `OrderService.registerShipment` |
| 배송 완료 | `SHIPMENT_COMPLETED` | `ORDER` / order id | 구매자 | `OrderService.deliver`(private, 웹훅·즉시확정 폴백 공통) |
| 포인트 충전 완료 | `POINT_CHARGED` | `POINT` / point transaction id | 충전한 회원 | `PointService.confirmCharge`(→`charge`) |
| 환불 완료 | `POINT_REFUNDED` | `POINT` / point transaction id | 구매자 | `PointService.refundOrder` |
| 출금 신청 | `WITHDRAW_COMPLETED` | `POINT` / point transaction id | 출금한 회원 | `PointService.requestWithdrawal` |

- `refId`가 "order id인지 shipment id인지" 확인이 필요했던 부분: `OrderShipment`는 `Order`와
  공유 PK(1:1)라 **둘이 같은 숫자값**이다. 그냥 `order.getId()`를 쓴다.
- **`refType`은 `SHIPMENT`를 따로 두지 않고 `ORDER`로 통일한다**(원래 "권장"란은 `SHIPMENT`였으나
  변경). 이동 대상이 어차피 둘 다 `/my?section=orders`로 같고(FE 004 §3.1 임시 이동표), 카테고리
  분류("배송" 여부)도 `refType`이 아니라 `type` 문자열(`SHIPMENT_STARTED` 등)에 `SHIP`이 포함되는지로
  판정되므로(FE 004 §3.1 임시 분류표) `refType`을 나눌 실익이 없다 — 종류만 늘어난다.
- **경매 낙찰(주문 자동 생성)은 이번 범위에서 뺀다.** `ORDER_PAID`를 판매자에게도 보내려면
  `AuctionCloseService`가 상품의 판매자 Member를 알아야 하는데, 지금 그 서비스는
  `ProductCommandPort`/`OrderCommandPort`로 productId/orderId만 주고받게 격리돼 있어(경매→상품
  직접 의존 금지 패턴) 판매자 조회 경로를 새로 뚫어야 한다. 상시 판매(`createOrder`)만 우선
  반영하고, 경매 판매자 알림은 필요하면 별도로 다룬다.
- `PointService`는 `PointAccount.getMember()`로 이미 Member 엔티티를 들고 있으므로(계좌 조회
  경유), `OrderService`/`RefundService`를 거치지 않고 `PointService` 안에서 바로 알림을 만든다
  — 알림 발송 위치가 실제 포인트 원장이 만들어지는 지점과 같아서 빠뜨릴 일이 없다.
- `pointTransactionRepository.save(...)`의 반환값(저장된 엔티티, id 포함)을 변수로 받아
  `refId`로 쓴다 — 지금은 반환값을 버리고 있다.

### 3. 문구

- `ORDER_PAID`: "상품이 판매되었습니다" / "주문이 결제됐어요. 배송지를 확인하고 송장을 등록해주세요."
- `SHIPMENT_STARTED`: "배송이 시작되었습니다" / "판매자가 송장을 등록했어요."
- `SHIPMENT_COMPLETED`: "배송이 완료되었습니다" / "구매를 확정하면 거래가 끝나요. 확정하지 않으면 3일 후 자동으로 처리됩니다."
- `POINT_CHARGED`: "포인트가 충전되었습니다" / "%,d원이 충전됐어요."
- `POINT_REFUNDED`: "환불이 완료되었습니다" / "%,d원이 환불됐어요."
- `WITHDRAW_COMPLETED`: "출금이 신청되었습니다" / "%,d원 출금이 접수됐어요."

## 구현 목록

- [x] `NotificationCommandPort`/`NotificationCommandAdapter`를 `notification.port`로 이동,
      기존 4개 사용처 + 테스트 3개 import 경로 갱신(동작 변화 없음, 빌드로 확인)
- [x] `OrderService`에 `NotificationCommandPort` 주입 — `createOrder`(ORDER_PAID→판매자),
      `registerShipment`(SHIPMENT_STARTED→구매자), `deliver`(SHIPMENT_COMPLETED→구매자) + 테스트
- [x] `PointService`에 `NotificationCommandPort` 주입 — `confirmCharge`가 호출하는 `charge`
      (POINT_CHARGED), `refundOrder`(POINT_REFUNDED), `requestWithdrawal`(WITHDRAW_COMPLETED)
      + `pointTransactionRepository.save(...)` 반환값을 refId로 사용 + 테스트
- [x] `docs/requests/BE/004-social-notification-contract.md` §3.2 표 갱신(6종 반영 완료로) —
      wish delete path 확정·unread count API·카테고리별 bulk read API 등 다른 절이 아직
      열려 있어 문서 전체 삭제는 안 함(해당 항목만 반영 완료로 갱신)
- [x] `docs/requests/FE/039-order-point-notifications.md`에 6종 알림 계약 문서 작성(FE 임시
      분류 규칙이 이미 이 문자열들을 전제하고 있어 — 004 §3.1 — 새 계약이라기보다 확정 공지에
      가깝다)
- [x] `./gradlew build`로 최종 검증