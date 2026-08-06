# 037 라이브 편성 상품 목록에 `saleStatus` 추가

- **작성자 파트**: BE (정윤) / **대상 파트**: FE
- **작성일**: 2026-08-06
- **대상 API**: `GET /api/lives/{liveId}/products`, `POST /api/lives/{liveId}/products`(연결 응답)

---

## 무엇이 바뀌나

응답 상품 객체에 **`saleStatus` 한 필드가 추가**됩니다. 기존 필드는 이름·타입 모두 그대로라
**FE 코드를 안 고쳐도 깨지지 않습니다.** 필드를 쓰기로 할 때만 반영하시면 됩니다.

```jsonc
{
  "id": 12,
  "liveId": 3,
  "productId": 2001,
  "productTitle": "리바이스 501 빈티지",
  "brandName": "Levi's",
  "price": 45000,
  "saleType": "AUCTION",          // 기존
  "saleStatus": "AUCTION_SCHEDULED", // ★ 추가
  "conditionGrade": "A",
  "thumbnailUrl": "https://...",
  "material": "코튼 100%",
  "measurements": { "어깨너비": 45, "총장": 70 },
  "defectSummary": "밑단 오염",
  "sortOrder": 0,
  "addedAt": "2026-07-28T11:00:00"
}
```

## 이름이 `salesStatus`가 아니라 `saleStatus`인 이유

상품 도메인(`GET /api/products`, `GET /api/products/{id}`)과 마이페이지가 이미 **`saleStatus`**
를 쓰고 있어 그쪽에 맞췄습니다. FE의 `liveCreateApi.ts`·`myApi.ts`도 같은 이름입니다.

> ⚠️ 홈 화면 상품 카드(`homeViewApi.ts`)만 `sellStatus`라는 다른 이름을 씁니다. 그건 홈
> 도메인만의 예외이고, 라이브는 여기서 `saleStatus`로 갑니다. 두 이름을 섞지 않도록 주의해 주세요.

## 값 목록

| 값 | 의미 |
| --- | --- |
| `DRAFT` | 등록만 되고 판매 방식 미정 |
| `ON_SALE` | 즉시 구매 판매 중 |
| `AUCTION_SCHEDULED` | 경매 예정(아직 시작 전) |
| `AUCTION_IN_PROGRESS` | 경매 진행 중 |
| `SOLD` | 판매 완료(낙찰·즉시구매 공통) |

`null`이 올 수 있습니다 — **상품 행을 찾지 못한 경우**(연결 후 상품이 삭제된 상황)입니다.
그때는 `productTitle` 등 다른 상품 필드도 전부 `null`이며, 연결 자체는 목록에 남습니다.
(호스트가 "왜 하나가 사라졌는지" 알 수 없게 되는 것을 막기 위한 기존 동작입니다.)

## `saleType`과 헷갈리지 마세요

**두 필드는 별개 축입니다.**

- `saleType` = 어떻게 파는가 (`DIRECT_SALE` / `AUCTION`)
- `saleStatus` = 지금 어떤 상태인가 (위 표)

경매 상품도 팔리면 `saleType`은 `AUCTION` 그대로이고 `saleStatus`만 `SOLD`가 됩니다.
**`saleType`으로 판매 완료 여부를 판단할 수 없습니다.**

## 쓰실 때 참고

- 판매 완료 배지는 `saleStatus === "SOLD"` 로 판단하시면 됩니다
- 경매가 유찰되면 상품은 `AUCTION_SCHEDULED`로 **되돌아갑니다**(다시 편성 가능). `SOLD`가
  아니라는 뜻이지 "실패" 상태가 따로 있는 것이 아닙니다
- 라이브 중 상태가 바뀌어도 이 목록은 **폴링/재조회 시점에만 갱신**됩니다. 실시간 반영이
  필요하면 기존 경매 STOMP 이벤트를 쓰시고, 필요한 게 더 있으면 요청 문서 남겨 주세요
