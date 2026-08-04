# 라이브 계약 — 지금 그대로 붙이면 깨지는 것들

- **요청 파트**: BE
- **대상 파트**: FE
- **관련 이슈**: `S15P11A108-217` `[LIVE]`, `-450`, `-453`
- **상태**: ⚠️ **확인 요망.** 아래 6건은 FE 계약 문서의 가정과 BE 실제 구현이 다르다
- **작성 시점**: 2026-07-31. **모든 항목을 그날의 코드로 직접 확인했다**

FE가 `VITE_LIVE_WATCH_API_ENABLED=true`로 실 API를 켜기 직전이라 정리한다.
**목업일 때는 안 드러나던 것들이 켜는 순간 문제가 된다.**

특히 1번은 **에러도 나지 않고 빈 목록도 아니라서** 발견이 늦다.

---

## 🔴 1. `page`는 0-base다 (FE는 1-base로 쓰고 있다)

FE 계약 문서에 "`page`: FE는 현재 1-base로 사용"이라고 적혀 있다. **BE는 0-base다.**

```java
// LiveController
@RequestParam(defaultValue = "0") @Min(0) int page
```

| 보낸 값 | FE 의도 | 실제로 오는 것 |
| --- | --- | --- |
| `page=1` | 첫 페이지 | **두 번째 페이지** |
| `page=0` | — | 첫 페이지 |

**첫 페이지 12건이 통째로 안 보이는데 에러가 안 난다.** 목록이 그럴듯하게 채워져 있어서
한참 뒤에나 발견된다.

BE를 1-base로 바꾸지 않는 이유는 상품·검색 등 **다른 목록 API가 전부 Spring `Pageable`
기본(0-base)**이라, 라이브만 다르게 가면 FE 어댑터가 갈라지기 때문이다.

**FE adapter에서 `page - 1`로 보내 달라.** 응답의 `page` 필드도 0-base로 돌아온다.

## 🔴 2. 라이브 개설에 `productIds`가 **필수**다

FE 계약 문서의 개설 요청 예시에 이 필드가 없다. **그대로 보내면 400이다.**

```java
// LiveScheduleRequest / LiveInstantRequest
@NotEmpty
List<Long> productIds
```

```json
{
  "title": "빈티지 데님 라이브",
  "thumbnailUrl": "https://cdn.example.com/live/1.jpg",
  "scheduledAt": "2026-08-01T20:00:00",
  "productIds": [2001, 2002]
}
```

즉시 개설(`POST /api/lives`)도 같다. **최소 1개**이며 비어 있으면 400.

이유는 **카테고리를 편성 상품에서 유도**하기 때문이다. 상품이 없으면 카테고리도 없고 팔 것도
없는 빈 방이 목록에 뜬다.

### "개설 후 상품을 순차 연결"은 맞지 않는다

FE 문서에 그렇게 적혀 있는데, **개설 한 번에 편성까지 끝난다.**
`POST /api/lives/{liveId}/products`는 **예약 방송의 편성을 나중에 고칠 때**만 쓴다.

> **방송이 시작되면 편성을 바꿀 수 없다.** 즉시 개설은 생성 즉시 `LIVE`가 되므로 개설 요청에
> 담은 편성이 그대로 확정된다.

## 🟡 3. 카테고리는 복수이고 query 이름도 다르다

| | FE 문서 | 실제 |
| --- | --- | --- |
| query | `categoryId` (단수) | **`categoryIds`** (복수, 반복 파라미터) |
| 응답 | `categoryId` + `categoryName` | **`categories: [{ id, name }]`** |

`live` 테이블에 카테고리 컬럼이 없다. **편성 상품에서 유도**하므로 라이브 하나가 카테고리를
여러 개 가진다. 아우터·하의를 함께 파는 방송은 두 탭 모두에 잡혀야 해서 대표 하나를 뽑지 않았다.

- 값은 항상 **대분류(depth 1)로 롤업**된다
- 필터는 반대로 **대분류를 주면 하위 소분류 상품을 건 방송까지** 잡힌다

## 🟡 4. 채팅·반응은 REST가 아니라 STOMP다 — 이미 구현돼 있다

FE 문서에 "현재 BE에는 채팅 메시지, 반응 이모지 API가 없다"고 적혀 있는데 **둘 다 있다.**
요청하신 REST 후보는 **만들지 않는다.**

| FE 문서 후보 | 실제 |
| --- | --- |
| `POST /api/lives/{id}/messages` | ❌ → **`/app/lives/{id}/chat`** (STOMP 발행) |
| `GET /api/lives/{id}/messages` | ❌ → **`GET /api/lives/{id}/chat-messages`** (커서 페이징) |
| `POST /api/lives/{id}/reactions` | ❌ → **`/app/lives/{id}/reactions`** (STOMP 발행) |
| `POST /api/lives/{id}/video-token` | ✅ **그대로 있다** |

확정된 답:

- **프로토콜**: WebSocket + STOMP (SockJS 미사용, polling·SSE 아님)
- **차단 메시지**: `blocked` 필드를 주지 않는다. **응답에서 아예 빠진다** — 숨김 판단을 FE에 맡기지 않는다
- **AI 답변**: `senderType: "AI"` 값만 열어둔 상태. 현재 발생하지 않는다
- **반응 정책**: **fire-and-forget, 저장하지 않는다.** 집계도 이력 API도 없다

전체 계약은 [`001-live-stomp-contract.md`](./001-live-stomp-contract.md),
붙이는 방법·테스트 가이드는 [`002`](./002-realtime-chat-handoff.md)·[`003`](./003-viewer-count-reaction-handoff.md)·[`005`](./005-video-token-handoff.md) 참고.

## 🟡 5. `saleType` 값이 다르다

FE 문서: `AUCTION` | `FIXED_PRICE` → **실제: `AUCTION` | `DIRECT_SALE`**

`FIXED_PRICE`는 없다. 상품 도메인 enum이라 BE가 임의로 바꾸지 않는다.

같은 맥락에서 홈 카드의 `sellStatus`(`ON_SALE`/`RESERVED`/`SOLD_OUT`)도 **현재 Mock 값일 뿐**
실제 `product.sale_status`와 다르다. 실제 값은(2026-08-04 기준)
`DRAFT`, `ON_SALE`, `AUCTION_SCHEDULED`, `AUCTION_IN_PROGRESS`, `SOLD` **다섯 개뿐이다** —
`PRIVATE`는 제거됐고(003 참고), `AUCTION_FAILED`(미낙찰)는 **아직 enum에 없다**(경매 입찰/종료
자체가 미구현이라 그 상태로 갈 경로가 없음 — `014-unsold-product-disposition.md` 참고). 이전에
`AUCTION_FAILED`가 곧 추가된다고 안내했는데 아직 반영 전이다. **`RESERVED`에 대응하는 상태는
여전히 없다.** 홈 실데이터 전환 시 매핑을 다시 확정한다.

## 🟡 6. `status=ENDED`를 보내면 400이다

FE 문서는 "공개 목록은 `LIVE`, `SCHEDULED`만 반환 권장"이라고 적었는데, BE는 **반환뿐 아니라
query 허용값에서도 막는다.** `status=ENDED`는 빈 목록이 아니라 **400 + `L007`**이다.

빈 목록으로 조용히 넘기면 FE가 "그런 방송이 없다"로 오해하기 때문이다.

---

## ⚠️ `viewerCount` 타입이 바뀌었다

이전에 "항상 `null`이니 시청자 수 표시를 생략해 달라"고 전달했는데 **그 안내는 폐기다.**

| | 이전 | 지금 |
| --- | --- | --- |
| 타입 | `Integer` (항상 `null`) | **`int` (항상 값이 있다)** |
| 아무도 안 볼 때 | `null` | **`0`** |
| `sort=VIEWERS_DESC` | 400 | **200** |

`null` 체크로 시청자 수를 숨기고 있었다면 **그 분기는 이제 절대 타지 않는다.** 0명인 방송은
`0`으로 표시하거나, 진행 전(`SCHEDULED`)에만 숨기는 쪽으로 바꿔 달라.

### 시청자 수 초기값은 REST로 받는다

```
GET /api/lives/{liveId}  →  currentViewerCount (초기값)
     ↓
/topic/lives/{liveId}/viewers 구독  →  이후 변화만
```

**구독만 하면 화면이 비어 있다.** 구독 직후 브로드캐스트가 자기 세션에 오는 것은 보장되지
않고, 다음 프레임은 다른 사람이 들고 날 때까지 오지 않는다.

## 페이지 응답 규격은 이대로 간다

```json
{ "content": [], "page": 0, "size": 12, "totalElements": 25, "totalPages": 3, "hasNext": true }
```

`items`/`meta`로 바꾸지 않는다. 상품·검색 등 다른 목록이 이미 이 규격을 쓰고 있어 라이브만
다르게 갈 수 없다. **FE adapter에서 흡수해 달라** — 요청서에도 그 방향을 열어 두셨다.

---

## 라이브 상세에서 아직 비어 있는 것 (2026-08-04 갱신)

**연결 상품 상세 필수 필드와 `currentProductId`는 이제 채워진다.** 상품 패널이 더 이상 거의
비어 있지 않다 — 아래 표를 최신 상태로 갱신했다.

| 항목 | 지금 | 언제 |
| --- | --- | --- |
| 채팅 송수신·이력 | ✅ 동작 | — |
| 시청자 수 | ✅ 동작 | — |
| 반응 이모지 | ✅ 동작 | — |
| 영상 접속 토큰 | ✅ 동작 | — |
| **연결 상품 상세** | ✅ `brandName`·`price`·`thumbnailUrl`·`saleType`·`conditionGrade`(요청한 `condition`과 이름 다름) 반영됨 | — |
| **`currentProductId`** (`NOW` 배지) | ✅ 반영됨 | — |
| **경매 패널** | ❌ API 자체가 없음(조건 설정만 있음, 시작/입찰/종료/조회 없음) | Phase 6~8 |
| `hostProfileImageUrl` | ❌ 아직 없음. **막던 이유는 해소됨** — `Member` 엔티티에 `profileImageUrl` 필드가 이제 있다. `LiveDetailResponse`에 노출만 안 돼 있는 상태 | 응답 필드 추가만 남음 |
| `description` | ❌ `live` 테이블에 여전히 컬럼이 없다 | **입력 항목인지 FE 확인 필요** |
| `material`·`measurements` | ⚠️ `product` 엔티티에는 이제 있다(`conditionGrade`/`material`/`measurements`). **`LiveProductResponse`에 아직 노출 안 됨** | 응답 필드 추가만 남음 |
| `defectSummary` | ❌ `product`에도 아직 컬럼 자체가 없다 | 상품 도메인 확장 선행 |

## FE에서 확인 부탁

1. **adapter에서 `page - 1`** ← 가장 중요, 조용히 틀린다
2. 개설 요청에 `productIds` 추가 (최소 1개)
3. `categoryIds`(복수) / `categories[]` 반영
4. `viewerCount`의 `null` 분기 제거
5. 시청자 수 초기값은 라이브 상세의 `currentViewerCount`에서
6. `saleType`은 `DIRECT_SALE` (`FIXED_PRICE` 아님)
7. `status=ENDED`는 보내지 않기
8. `live.description`을 개설 화면에서 실제로 입력받는지 알려 달라 — 넣기로 하면 Phase 5에 포함한다

이견이 있거나 계약을 바꿔야 하는 부분이 있으면 이 문서에 이어서 적어 주시면 된다.
