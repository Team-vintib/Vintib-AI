# 현재 소개 상품(`NOW` 배지) + 상품 카드 필드 인계 — Phase 5

- **요청 파트**: BE
- **대상 파트**: FE
- **관련 이슈**: `S15P11A108-87` (LIVE-004)
- **상태**: ✅ **구현 완료, 바로 붙일 수 있다**
- **선행 문서**: [`006-live-contract-corrections.md`](./006-live-contract-corrections.md)에서 "Phase 5에 온다"고 한 것이 이번 건이다

---

## 1. 한 줄 요약

**`NOW` 배지를 띄울 수 있게 됐고, 시청 화면 상품 패널이 이제 이 응답만으로 그려진다.**

`006`에서 "`productTitle`만 온다"고 알렸던 상품 카드에 **브랜드·가격·썸네일·판매방식·상태등급**이 채워졌다.

## 2. 지금 소개 중인 상품

### 초기값은 REST, 변화는 STOMP

시청자 수와 같은 패턴이다.

```
GET /api/lives/{liveId}  →  currentProductId (초기값)
        ↓
/topic/lives/{liveId}/product 구독  →  이후 전환
```

**구독만 하고 초기값을 토픽에서 기다리면 배지가 안 뜬다.** 호스트가 상품을 바꾸기 전까지는
아무 프레임도 오지 않는다.

### 브로드캐스트 payload

```json
{ "liveId": 101, "currentProductId": 2001 }
```

| 필드 | 타입 | 비고 |
| --- | --- | --- |
| `liveId` | `Long` | 여러 방송을 한 연결에서 구독할 때 구분용 |
| `currentProductId` | `Long` | **`null`이면 소개 중인 상품이 없다** |

**상품 정보를 통째로 싣지 않고 ID만 보낸다.** 편성 상품의 상세는 화면 진입 시 라이브 상세로
이미 받아 뒀다. 전환할 때마다 같은 내용을 다시 보내면 중복 payload가 나가고, 상품 정보가 두
경로로 들어와 어느 쪽이 최신인지 모호해진다.

**FE는 이 ID로 이미 갖고 있는 편성 목록에서 찾아** 배지를 옮기면 된다.

### 호스트가 바꾸는 API

```http
PATCH /api/lives/{liveId}/current-product
Authorization: Bearer {accessToken}
Content-Type: application/json

{ "productId": 2001 }
```

- **호스트만** 가능
- **이 방송에 편성된 상품**이어야 한다
- `productId`를 **`null`로 보내면 해제**된다 (잡담 구간 등 아무것도 소개하지 않는 상태)

응답은 브로드캐스트와 같은 형태다.

### ⚠️ 편성 변경과 규칙이 다르다

| | 상품 편성(`POST /products`) | 소개 상품 전환(이번 API) |
| --- | --- | --- |
| 방송 시작 후 | ❌ 잠긴다 | ✅ **가능하다** |
| 종료·취소 방송 | ❌ | ❌ |

전환은 **방송 중에 하는 것이 본래 용도**라 진행 중에도 열려 있다. 종료·취소된 방송에서만 막힌다.

### 에러

| HTTP | 코드 | 상황 |
| --- | --- | --- |
| 400 | `L007` | 종료·취소된 방송 |
| 403 | `L004` | 호스트가 아님 |
| 404 | `L001` | 라이브 없음 |
| 404 | `L006` | **이 방송에 편성되지 않은 상품** |

> `L006`을 404로 준다. 상품 자체는 있지만 **이 방송의 편성 목록에 없다**는 뜻이라
> 기존 `LIVE_PRODUCT_NOT_FOUND` 코드를 그대로 쓴다.

### 방송이 끝나면 자동으로 해제된다

`PATCH /api/lives/{liveId}/status`로 `ENDED`가 되면 `currentProductId`가 `null`이 된다.
종료 화면이나 다시보기에서 특정 상품만 계속 강조되면 안 되기 때문이다.

## 3. 상품 카드 필드가 채워졌다

`GET /api/lives/{liveId}`의 `products[]`와 `GET /api/lives/{liveId}/products` 양쪽에 적용된다.

```json
{
  "id": 5001,
  "liveId": 101,
  "productId": 2001,
  "productTitle": "리바이스 501 빈티지",
  "brandName": "Levi's",
  "price": 45000,
  "saleType": "AUCTION",
  "conditionGrade": "A",
  "thumbnailUrl": "https://.../vintib-public/product-images/2001/abc.jpg",
  "sortOrder": 0,
  "addedAt": "2026-07-28T11:00:00"
}
```

| 필드 | 타입 | nullable | 비고 |
| --- | --- | --- | --- |
| `brandName` | `String` | 가능 | 브랜드 미지정 상품 |
| `price` | `Long` | 가능 | **경매 예정 상품은 아직 가격이 없다** → '경매 예정'으로 표시 |
| `saleType` | enum | 가능 | **`DIRECT_SALE` / `AUCTION`.** `FIXED_PRICE` 아님 |
| `conditionGrade` | `String` | 가능 | **자유 문자열** — enum으로 굳히지 말 것 |
| `thumbnailUrl` | `String` | 가능 | 등록된 이미지가 없으면 null |

### 상품이 삭제돼도 목록에서 사라지지 않는다

연결 후 판매자가 상품을 지우면 **상품 관련 필드만 전부 `null`**이 되고 연결 자체는 남는다.
조용히 사라지면 호스트가 왜 하나가 없어졌는지 알 수 없기 때문이다.

FE는 `productTitle`이 `null`이면 "삭제된 상품"으로 표시해 주면 된다.

## 4. 라이브 목록에도 들어간다

`GET /api/lives`의 각 항목에 `currentProductId`가 추가됐다. 목록 카드에서 "지금 이 상품"
배지를 띄울 때 쓴다. 필요 없으면 무시해도 된다.

## 5. 테스트 가이드

### 준비

```bash
docker compose up -d postgres redis
```

```bash
cd BE && ./gradlew bootRun
```

### 5-1. 소개 상품 전환

Swagger(`/swagger-ui/index.html`)가 편하다.

1. 로그인 → access token
2. `POST /api/lives` 즉시 개설 (**`productIds` 최소 1개 필수**)
3. `PATCH /api/lives/{liveId}/current-product` → `{"productId": <편성한 상품 ID>}`
   - `200`, `currentProductId`가 그 값
4. `GET /api/lives/{liveId}` → `currentProductId`가 반영됐는지
5. `{"productId": null}` → 해제되는지

### 5-2. 실패 케이스

| 시도 | 기대 |
| --- | --- |
| 편성하지 않은 상품 ID | `404` `L006` |
| 다른 계정 토큰 | `403` `L004` |
| `ENDED`로 바꾼 뒤 호출 | `400` `L007` |

### 5-3. 브로드캐스트 확인

브라우저 콘솔에서 시청자로 구독한다.

```js
const ws = new WebSocket('ws://localhost:8080/ws');
ws.onmessage = (e) => console.log(e.data);
ws.onopen = () => {
  ws.send('CONNECT\naccept-version:1.2\nhost:localhost\n\n\0');
  setTimeout(() => ws.send('SUBSCRIBE\nid:p\ndestination:/topic/lives/1/product\n\n\0'), 300);
};
```

이 상태에서 Swagger로 `PATCH .../current-product`를 호출하면 콘솔에
`{"liveId":1,"currentProductId":2001}`이 찍힌다.

**검증에 실패하면(404/403/400) 브로드캐스트가 나가지 않는다** — 시청자 화면이 잘못 바뀌지 않는다.

### 5-4. 자동 테스트

```bash
cd BE && ./gradlew test --tests '*LiveCurrentProductStompTest' --tests '*LiveControllerTest'
```

## 6. `006`에서 아직 안 채워진 것 (2026-08-04 갱신)

| 항목 | 상태 |
| --- | --- |
| 경매 패널 | ❌ Phase 6~8(조건 설정만 있고 시작/입찰/종료/조회 없음) |
| `hostProfileImageUrl` | ❌ 아직 없음. **막던 이유는 해소됨** — `Member` 엔티티에 `profileImageUrl`이 이제 있다. `LiveDetailResponse` 노출만 안 됨 |
| `live.description` | ❓ **개설 화면에서 실제로 입력받는지 알려 달라** — 넣기로 하면 컬럼을 추가한다(`live` 테이블에 여전히 없음) |
| `material`·`measurements` | ⚠️ `product` 엔티티에는 이제 있다. `LiveProductResponse` 노출만 안 됨 |
| `defectSummary` | ❌ `product`에도 아직 컬럼 자체가 없다 |

## 7. FE에서 확인 부탁

1. **`currentProductId` 초기값은 라이브 상세에서** — 토픽에서 기다리면 배지가 안 뜬다
2. 브로드캐스트는 **ID만** 온다 — 편성 목록에서 찾아 매칭
3. `currentProductId`가 `null`이면 배지를 아무 상품에도 달지 않기
4. `saleType`은 `DIRECT_SALE` (`FIXED_PRICE` 아님)
5. `conditionGrade`는 자유 문자열
6. `productTitle`이 `null`이면 삭제된 상품
7. `live.description` 필요 여부 회신

바꿔야 할 부분이 있으면 이 문서에 이어서 적어 주시면 된다.
