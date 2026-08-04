# 016 - 송장 등록 택배사 필드 계약 변경

**요청자 파트**: BE
**대상 파트**: FE

## 배경/이유

`SY034`(택배 배송 조회 실연동, deliveryapi.co.kr)로 `POST /orders/{orderId}/shipment`의 택배사 필드를
자유 문자열에서 고정 코드로 바꿨다. deliveryapi.co.kr이 지원하는 코드로만 실제 배송 조회가 가능하기 때문이다.

## 요청 내용

- `POST /orders/{orderId}/shipment` 요청 바디: `courier`(자유 문자열) → `courierCode`(아래 10개 값 중 하나, 대문자)로 변경
  - `LOTTE`(롯데택배), `CJ`(CJ대한통운), `HANJIN`(한진택배), `POST`(우체국택배), `KYUNGDONG`(경동택배),
    `DAESIN`(대신택배), `LOGEN`(로젠택배), `HAPDONG`(합동택배), `COUPANG`(쿠팡택배), `WOORI`(우리택배)
- 판매자의 송장 등록 폼에서 택배사 입력을 자유 텍스트가 아니라 위 10개 중 선택하는 UI(드롭다운 등)로 바꿔야 한다.
- `GET /orders/{orderId}/shipment`, `GET /orders/{orderId}/address` 응답에 `courierCode`(코드)와
  `courierName`(표시용 한글명, 예: "CJ대한통운")이 함께 내려온다 — 화면 표시는 `courierName`을 쓰면 된다.
- 송장 등록 직후에도 배송 상태가 곧바로 "배송완료"로 바뀌지 않을 수 있다 — 실제 택배사 배송완료 신호를
  받아야 반영된다(기존에는 등록과 동시에 배송완료 처리됐음). 주문 상태가 `SHIPPING`(배송중)으로 한동안
  머무를 수 있다는 점을 화면에 반영해달라.
