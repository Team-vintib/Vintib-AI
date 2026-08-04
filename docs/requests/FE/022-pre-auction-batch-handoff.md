# 022 경매 진입 전 일괄 반영 — FE 요청 처리 결과

- **작성자 파트**: BE (정윤) / **대상 파트**: FE
- **작성일**: 2026-08-03
- **관련 브랜치**: `feat/217-live-fixes-pre-auction`
- **관련 이슈**: [-217](https://ssafy.atlassian.net/browse/S15P11A108-217) `[LIVE]`,
  [-279](https://ssafy.atlassian.net/browse/S15P11A108-279) `[HOME-001]`,
  [-68](https://ssafy.atlassian.net/browse/S15P11A108-68) `[SEARCH-001/002]`

`docs/requests/BE/`에 올려 주신 요청을 완료 코드와 대조해 일괄 반영했습니다.
**어떤 요청을 어떻게 반영했는지, 반영하지 않은 것은 왜인지**를 항목별로 남깁니다.

---

## 0. 요약 — 요청별 처리 결과

| 원 요청 | 처리 | 어디에 |
| --- | --- | --- |
| `004` §3.1 홈 라이브 카드 `hostId` | ✅ 반영 | §3 |
| `004` §3.2 홈 섹션 노출 정책 문서화 | ✅ 반영 | §3 |
| `004` §3.3 홈 `liveNow`가 종료 라이브 노출 | ✅ 반영(원인 제거) | §3 |
| `005` 통합 검색 `GET /api/search` | ✅ 반영 | §4 |
| `007` §3.1 생성용 연결 가능 상품 조회 | ⚠️ **기존 API로 충족** — 새로 안 만듦 | §6-A |
| `007` §3.5 `LiveProductResponse` 필드 보강 | ✅ 반영(Phase 5) | §2 |
| `007` §3.5 `LiveDetailResponse` currentProductId / hostProfileImageUrl / description | ✅ 반영 | §2 |
| `007` §3.5 `material`·`measurements`·`defectSummary` | ❌ 미반영 | §6-B |
| `007` §3.5 불필요 필드 제거(`addedAt`·`liveId`·연결 `id`) | ❌ 미반영(유지) | §6-C |
| `007` §3.3·§3.6 AI 시착 생성 | ❌ 미반영(내 파트 아님) | §6-D |
| `008` §3.2.1 예약 라이브 알림 신청·스케줄러 | ✅ 반영 | §5 |
| `008` §3.2.1 `reminderCount` | ❌ 미반영 | §6-E |
| `009` 경매 snapshot/start/bid/close/STOMP | ⏳ **다음 작업**(Phase 6~8) | §6-F |
| `013` §2 현재 소개 상품 전환 트리거 | ✅ 반영(Phase 5) | §2 |
| `013` 방송 종료 시청자 실시간 전파 | ✅ 반영 | §2 |

**추가로, 요청에 없었지만 고친 것** — 서버 시각이 9시간 어긋나던 문제(§1). FE 화면 전반에 영향이 있으니 §1을 먼저 읽어 주세요.

---

## 1. ⚠️ 모든 시각 필드가 9시간 어긋나던 문제 (요청 외, 중요)

### 무슨 일이었나

백엔드 컨테이너가 **UTC로 돌고 있었습니다.** 우리 API의 시각 필드는 전부 오프셋이 없는
문자열(`"2026-08-03T12:30:00"`)이라, 브라우저가 이걸 KST로 읽으면서 **정확히 9시간 차이**가 났습니다.

- 라이브 개설/시작 시각이 9시간 전으로 표시
- 경과 방송 시간이 0이 아니라 **9시간부터 시작**
- 예약 검증(`@Future`)도 UTC 기준이라 **KST로는 과거인 시각까지 예약이 통과**

### 어떻게 고쳤나

서버 컨테이너 타임존을 `Asia/Seoul`로 고정했습니다(`docker-compose.yml`의 `TZ`,
`BE/Dockerfile`의 `-Duser.timezone`). 배포되면 그때부터 정상 값이 나갑니다.

### FE가 알아야 할 계약

> **모든 datetime 필드는 오프셋 없는 KST 벽시계입니다.** `Z`도 `+09:00`도 붙지 않습니다.

- `new Date("2026-08-03T21:30:00")`처럼 그대로 파싱하면 KST로 해석돼 맞습니다.
- **뒤에 `Z`를 붙이거나 `.toISOString()` 왕복을 하면 다시 9시간이 틀어집니다.** 혹시 지금
  임시로 9시간을 더하거나 빼는 보정 코드를 넣어 두셨다면 **배포 후 반드시 제거**해 주세요.
- 요청으로 보내는 시각(`scheduledAt` 등)도 같은 형식(로컬 벽시계)으로 보내면 됩니다.

오프셋을 실어 보내는 방식(`OffsetDateTime`)으로 바꾸는 것도 검토했지만, BE 전 도메인 DTO와
FE 파싱을 동시에 바꿔야 해서 이번 주 일정에서는 위 규약으로 통일했습니다.

---

## 2. 라이브 시청 화면

### 2.1 `GET /api/lives/{liveId}` 응답에 추가된 필드

```jsonc
{
  "id": 101,
  "hostId": 1,
  "hostNickname": "빈티지장인",
  "hostProfileImageUrl": "https://.../profile/1.jpg", // 추가 (007 §3.5)
  "isHost": false,                                     // 추가 — 아래 2.2
  "isReminderSet": false,                              // 추가 — 아래 5
  "title": "빈티지 데님 라이브",
  "thumbnailUrl": null,
  "description": "90년대 리바이스 위주로 소개합니다",   // 추가 (007 §3.5)
  "status": "LIVE",
  "scheduledAt": null,
  "startedAt": "2026-08-03T21:30:00",
  "endedAt": null,
  "peakViewerCount": 152,
  "currentViewerCount": 128,
  "currentProductId": 2001,
  "products": [ /* ... */ ],
  "categories": [ /* ... */ ]
}
```

### 2.2 `isHost` — "내 방송인데 팔로우 버튼이 뜬다" 문제

**증상**: 라이브에서 나갔다 다시 들어오면, 내가 만든 방송인데도 다른 사람 방송처럼
팔로우 버튼이 활성화됨.

**원인**: 상세 응답이 `hostId`만 주고 있어서 FE가 `hostId === me.id`로 직접 판정해야 했는데,
새로고침·재입장 시 **회원 정보 복원이 라이브 상세 렌더보다 늦으면** `me.id`가 `undefined`라
판정이 뒤집힙니다. FE 타이밍 문제이기도 하지만 **판정 근거를 클라이언트에 맡긴 계약 자체**가
원인이라 서버가 계산해 내려주는 쪽으로 바꿨습니다.

**요청**: `hostId` 직접 비교를 **`isHost`로 교체**해 주세요. 판매자 전용 UI(종료 버튼, 상품 전환
버튼)와 팔로우 버튼 노출을 이 값으로 가르면 경합이 사라집니다.

- 이 엔드포인트는 계속 **비회원 공개**입니다. 토큰을 함께 보내면 `isHost`가 채워지고,
  없으면 항상 `false`입니다. → **로그인 상태라면 이 요청에도 `Authorization` 헤더를 붙여 주세요.**
- `hostId`는 그대로 남습니다(프로필 이동용).

### 2.3 방송 종료 실시간 전파 — 신규 토픽

`013`에서 요청하신 "종료 시 시청자 전파"입니다. 지금까지는 호스트가 종료해도 시청 화면이
그대로 남고, 새로고침해야 404를 만났습니다.

```
SUBSCRIBE /topic/lives/{liveId}/status
```

payload:

```json
{
  "liveId": 101,
  "status": "ENDED",
  "startedAt": "2026-08-03T21:30:00",
  "endedAt": "2026-08-03T22:40:00"
}
```

- `status`는 `LIVE` | `ENDED` | `CANCELED`. `ENDED`·`CANCELED`면 종료 안내로 전환하면 됩니다.
- **커밋 이후에 나갑니다** — 전이가 거부되면(400) 아무것도 전파되지 않습니다.
- `PATCH /api/lives/{liveId}/status` 응답(`LiveResponse`)에도 `endedAt`이 추가됐습니다.

### 2.4 개설 요청에 `description` 추가 (선택)

`POST /api/lives`, `POST /api/lives/schedule` 본문에 `description`(선택, 최대 1000자)을 넣을 수
있습니다. 안 보내면 `null`이고 기존 요청은 그대로 동작합니다.

### 2.5 이미 반영돼 있던 것 (Phase 5, `docs/requests/FE/007` 참고)

- `PATCH /api/lives/{liveId}/current-product` + `/topic/lives/{liveId}/product` 전파 → `013` §2
- `LiveProductResponse`의 `brandName`·`price`·`thumbnailUrl`·`saleType`·`conditionGrade` → `007` §3.5
  - ⚠️ `saleType`은 `FIXED_PRICE`가 아니라 **`DIRECT_SALE`**입니다.

---

## 3. 홈 — Mock 제거 및 실데이터 전환

### 3.1 `liveNow`에 종료된 라이브가 뜨던 버그 (`004` §3.3)

**원인은 `HomeService`가 통째로 Mock이었던 것**입니다. `liveId` 101·102가 코드에
하드코딩돼 있어서, 홈에는 뜨는데 상세는 404가 났습니다(재현하신 그대로입니다).

이제 홈·팔로잉 홈의 **모든 섹션이 실데이터**입니다. `liveNow`는 리포지토리 질의에서
상태를 `LIVE`로 고정해, 호출부 실수로 종료 방송이 다시 새어 나올 수 없게 했습니다.

### 3.2 `hostId` 추가 (`004` §3.1)

`GET /api/home`·`GET /api/home/following`의 라이브 카드에 `hostId: number`가 추가됐습니다.

### 3.3 섹션 노출 정책 (`004` §3.2)

| 섹션 | 대상 | 정렬 | 최대 |
| --- | --- | --- | --- |
| `liveNow` | 상태가 `LIVE`인 방송만 | 최근 시작순 | 10 |
| `scheduledLives` | `SCHEDULED`이면서 **예정 시각이 아직 안 지난** 방송 | 임박순 | 10 |
| `onSaleProducts` | `ON_SALE` 상품 | 최신 등록순 | 20 |
| `upcomingAuctionProducts` | `AUCTION_SCHEDULED` 상품 | 최신 등록순 | 20 |
| `categoryProductSections` | 대분류 6개, 각 탭의 `ON_SALE` 상품 | 최신 등록순 | 탭당 8 |

- **빈 섹션도 키는 항상 내려갑니다**(빈 배열). 키가 사라지는 일은 없습니다.
- 카드의 `viewerCount`는 **진행 중일 때만** 값이 있고 예약 방송은 `null`입니다
  (예약 방송의 0명과 "집계 대상 아님"은 다른 뜻이라 구분했습니다).
- `isWished`는 **비회원이면 `null`**(false 아님)입니다. 기존 정책 그대로입니다.
- 경매 예정 카드의 `startingBid`·`auctionStartsAt`은 그 상품에 걸린 경매와 **그 경매가 얹힌
  방송의 예정 시각**에서 나옵니다. 경매가 아직 안 걸렸으면 둘 다 `null`입니다.

### 3.4 팔로잉 홈 `lives`가 채워집니다

지금까지 빈 배열이던 `GET /api/home/following`의 `lives`가 **팔로우한 판매자들의
진행 중·예정 방송**으로 채워집니다. 판매자 카드의 `liveId`·`liveStatus`·`liveTitle`·`liveAt`도
같이 채워집니다(방송이 없으면 넷 다 `null`, 기존 계약 그대로).

- 진행 중인 방송이 있으면 **그쪽이 예약 방송보다 우선**해서 배지에 잡힙니다.

---

## 4. 통합 검색 `GET /api/search` (`005`)

**비회원 공개**입니다. 토큰을 붙이면 `isWished`·`isFollowing`이 채워집니다.

### 요청

| 파라미터 | 타입 | 기본값 | 비고 |
| --- | --- | --- | --- |
| `keyword` | string | (필수) | 최대 100자. 앞뒤 공백은 서버가 다듬음. 공백만 보내면 400 |
| `type` | `ALL`\|`PRODUCT`\|`LIVE`\|`USER` | `ALL` | |
| `categoryIds` | number[] | — | **상품 전용**. 소분류 ID 기준 |
| `conditionGrades` | string[] | — | **상품 전용** |
| `saleTypes` | `DIRECT_SALE`\|`AUCTION` (복수) | — | **상품 전용** |
| `minPrice` / `maxPrice` | number | — | **상품 전용** |
| `sort` | `LATEST`\|`PRICE_ASC`\|`PRICE_DESC` | `LATEST` | 가격 정렬은 상품에만 적용 |
| `page` / `size` | number | `0` / `20` | 세 섹션에 동일 적용 |

> 요청서의 `categories`는 **`categoryIds`**, `conditions`는 **`conditionGrades`**로 이름을 맞췄습니다
> — 기존 라이브 목록 API(`GET /api/lives?categoryIds=`)와 표기를 통일하기 위해서입니다.
> 배열은 `?categoryIds=1&categoryIds=2` 또는 `?categoryIds=1,2` 둘 다 받습니다.

### 응답

```jsonc
{
  "success": true,
  "data": {
    "products": { "content": [ /* ProductCardResponse */ ], "page": 0, "size": 20,
                  "totalElements": 3, "totalPages": 1, "hasNext": false },
    "lives":    { "content": [ /* LiveCardResponse */ ], /* ... */ },
    "users":    { "content": [ /* UserSearchItem */ ], /* ... */ }
  },
  "error": null
}
```

> **`null`과 빈 배열은 뜻이 다릅니다.** `type`에 포함되지 않은 섹션은 **`null`**(조회하지 않음),
> 조회했지만 결과가 없으면 `content: []` + `totalElements: 0`입니다.

**상품·라이브 카드는 홈(`GET /api/home`)과 완전히 같은 타입입니다.** 요청서에는
`{ id, title, brandName, thumbnailUrl, price, saleType, saleStatus, isWished }`로 적어 주셨는데,
검색 전용 DTO를 새로 만들면 같은 카드 컴포넌트에 두 가지 모양을 먹여야 하고 필드가 하나 늘 때마다
두 곳을 고쳐야 합니다. **검색은 "같은 카드를 다른 조건으로 찾아 주는 것"**이라 판단해 홈 카드를
그대로 재사용했습니다. 필드명 대응은 아래와 같습니다.

| 요청서 필드 | 실제 필드(`ProductCardResponse`) |
| --- | --- |
| `id` | `productId` |
| `title` | `name` |
| `brandName` | `brand` |
| `thumbnailUrl` | `thumbnailUrl` |
| `price` | `price` (경매 상품은 `null`, 대신 `startingBid`) |
| `saleType` | `sellType` (`NORMAL` \| `AUCTION_SCHEDULED`) |
| `saleStatus` | `sellStatus` (`ON_SALE` \| `SOLD_OUT`) |
| `isWished` | `isWished` |

**이 매핑이 불편하면 말씀해 주세요.** 검색 전용 DTO로 분리하는 것도 어렵지 않습니다 —
지금 고르지 않은 이유가 위 한 가지뿐이라, FE 쪽 어댑터 사정이 다르면 바꾸는 게 맞습니다.

`UserSearchItem`:

```json
{ "id": 31, "nickname": "빈티지장인", "profileImageUrl": null,
  "followerCount": 1284, "productCount": 37, "isFollowing": false }
```

### 검색 범위 정책

- **대소문자를 무시한 부분 일치**입니다(전문 검색 인덱스 없음).
- 상품은 **상품명**, 라이브는 **방송명**, 회원은 **닉네임만** 대상입니다.
  - 회원을 이메일·실명으로 찾게 두면 개인정보가 검색으로 새어 나가서 막았습니다.
- 임시 저장(`DRAFT`)·삭제된 상품, 종료·취소된 방송은 결과에 들어가지 않습니다.
- 관련도순 정렬은 없습니다 — 부분 일치라 점수를 매길 근거가 없습니다.

---

## 5. 예약 라이브 시작 알림 (`008` §3.2.1)

### 엔드포인트

| Method | Path | 설명 |
| --- | --- | --- |
| `POST` | `/api/lives/{liveId}/reminders` | 신청 |
| `DELETE` | `/api/lives/{liveId}/reminders` | 취소 |

둘 다 인증 필요. 응답은 동일합니다:

```json
{ "success": true, "data": { "liveId": 101, "isReminderSet": true }, "error": null }
```

신청 상태는 `GET /api/lives/{liveId}`의 **`isReminderSet`**으로도 확인할 수 있습니다
(비회원이면 항상 `false`).

### 확인 주셨던 정책 항목

| 질문 | 정한 것 |
| --- | --- |
| 중복 신청 방지 | `live_reminder` 테이블 + `(live_id, member_id)` unique |
| 발송 시점 | **시작 10분 전** 또는 **호스트가 실제로 시작한 직후**, 둘 중 먼저 오는 쪽 |
| 알림 값 | `type=LIVE_REMINDER`, `refType=LIVE`, `refId={liveId}` (요청하신 값 그대로) |
| 이미 시작·종료된 방송에 신청 | **예정(`SCHEDULED`) 상태에만 신청 가능.** 아니면 `400 L007` |
| idempotency | `notified_at` 컬럼. 스케줄러는 이 값이 비어 있는 신청만 집고, 알림 생성과 **같은 트랜잭션**에서 채웁니다. 서버가 재기동돼도 이미 보낸 건은 다시 잡히지 않습니다 |

### 그 밖에 FE가 알아야 할 것

- **같은 방송에 두 번 신청해도 `200`입니다.** 중복 클릭에 에러를 띄우면 사용자가 무엇이
  잘못됐는지 알 수 없어서, 상태가 이미 원하는 대로면 그대로 성공으로 돌려줍니다.
  **취소도 신청한 적이 없으면 그냥 `200`**입니다.
- 발송은 **최대 1분 주기 스케줄러**가 처리합니다. 초 단위 정확도는 보장하지 않습니다.
- 호스트 본인도 신청할 수 있습니다(막을 이유가 없어 예외 처리를 만들지 않았습니다).

---

## 6. 반영하지 않은 것과 그 이유

### A. `007` §3.1 생성용 연결 가능 상품 조회 — **새 API를 만들지 않았습니다**

요청하신 `GET /api/lives/create/products` 대신 **이미 있는 API로 충족됩니다.**

```
GET /api/users/{userId}/products?page=0&size=20
```

본인이 등록한 상품 전체를 최신순으로 주고 **`DRAFT` 등 비공개 상태도 포함**합니다(라이브에 걸
상품을 고르는 화면에 필요한 그대로입니다). 인증 필요, 본인 것만 조회 가능(타인이면 403).

- `keyword` 검색은 지원하지 않습니다. 필요하시면 말씀해 주세요 — 지금은 상품 수가 적어
  클라이언트 필터로 충분하다고 봤습니다.

### B. `007` §3.5 `material` / `measurements` / `defectSummary` — 미반영

요청서에 **(선택)**으로 표시된 항목이고, "있으면 표시, 없어도 화면은 동작"이라고 적어 주셨습니다.
이 값들을 라이브 상품 카드에 넣으려면 편성 상품 수만큼 상품 상세를 더 읽어야 해서, 시청 화면
진입 비용이 커집니다. **상품 상세(`GET /api/products/{id}`)에 이미 다 있으니** 상세 패널을 열 때
그쪽에서 가져오는 편이 낫습니다. 꼭 카드에 필요하면 다시 요청해 주세요.

### C. `007` §3.5 불필요 필드 제거(`addedAt`·`liveId`·연결 `id`) — 유지

"유지/제거는 BE 판단(우선순위 낮음)"으로 적어 주셔서 **유지**를 골랐습니다. 지우면 이 필드를
읽는 기존 코드가 깨지는데, 얻는 게 응답 크기 몇 바이트뿐입니다.

### D. `007` §3.3·§3.6 AI 시착 생성 — 미반영 (**내 담당이 아닙니다**)

시착(TRYON)은 서윤·AI 파트 범위입니다. 요청 문서
`docs/requests/BE/003-live-tryon-contract.md`에 **시착 항목만 남겨** 두었으니 그쪽에서 처리됩니다.
제가 임의로 만들면 AI 서버 계약과 어긋납니다.

### E. `008` §3.2.1 `reminderCount` — 미반영

응답 예시에 있던 "이 방송에 알림 신청한 사람 수"입니다. 화면에 어떻게 쓰이는지 요청서에
설명이 없었고, 넣으면 신청/취소마다 집계 질의가 한 번 더 나갑니다. **쓰이는 자리가 있으면
말씀해 주세요** — 추가는 간단합니다.

### F. `009` 경매 API·STOMP — 미반영, **바로 다음 작업입니다**

현재 경매 쪽에 있는 것은 **호스트의 경매 조건 설정(`POST /api/lives/{liveId}/auctions`)뿐**입니다.
snapshot 조회·시작·입찰·종료·입찰 내역·낙찰자 + `/topic/lives/{id}/auctions`는 전부 이번 배치
직후 착수합니다.
계약이 확정되면 별도 문서로 전달드립니다. 이 배치를 먼저 한 이유는, 라이브의 시각·호스트
판정이 틀린 상태에서 경매를 얹으면 같은 버그를 경매에서 다시 만나기 때문입니다.

---

## 7. FE에서 확인해 주셨으면 하는 것

1. **시각 보정 코드 제거** — 9시간을 더하거나 빼는 임시 처리가 있다면 배포 후 제거(§1).
2. **`hostId` 비교 → `isHost`로 교체**, 그리고 로그인 상태면 `GET /api/lives/{liveId}`에도
   `Authorization` 헤더 첨부(§2.2).
3. **`/topic/lives/{liveId}/status` 구독** 추가 — 종료 시 시청 화면 전환(§2.3).
4. **홈 mock 제거** — 이제 실데이터입니다. 데이터가 없으면 섹션이 빈 배열로 옵니다(§3).
5. **검색 mock → 실 API 연결**, 필드명 매핑 확인(§4). 매핑이 불편하면 알려 주세요.
6. **알림 신청 토글 연결**(§5).
