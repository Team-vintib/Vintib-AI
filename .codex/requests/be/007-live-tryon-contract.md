# 라이브/AI 시착 도메인 API 계약 보완 요청

## 요청자 파트 / 대상 파트

- 요청자: FE
- 대상: BE

## 배경/이유

BE에는 라이브 예약/즉시 개설, 라이브 상세, 상태 전이, 라이브 상품 연결, 경매 조건 설정, 시착 결과 조회/삭제 일부가 구현되어 있다. FE 라이브 목록/개설/시청 화면과 라이브 AI 시착 패널은 이 구현에 붙일 수 있는 부분을 우선 사용하되, 공개 라이브 목록, 개설 상품 검색, 시청 화면 상품 상세 필드, 채팅/반응/시착 생성 계약이 추가로 필요하다.

기존 `009-live-list-api-contract.md`, `010-live-create-api-contract.md`, `012-live-watch-detail-contract-gaps.md`, `013-live-tryon-contract.md`를 이 문서로 병합한다.

## 현재 BE에서 그대로 사용할 수 있는 계약

| 기능 | Method | Endpoint | 인증 | 현재 BE 구현 |
| --- | --- | --- | --- | --- |
| 즉시 라이브 개설 | `POST` | `/api/lives` | 필요 | 구현됨 |
| 예약 라이브 개설 | `POST` | `/api/lives/schedule` | 필요 | 구현됨 |
| 라이브 상세 조회 | `GET` | `/api/lives/{liveId}` | 불필요 | 구현됨 |
| 라이브 상태 전이 | `PATCH` | `/api/lives/{liveId}/status` | 필요 | 구현됨 |
| 라이브 상품 연결 | `POST` | `/api/lives/{liveId}/products` | 필요 | 구현됨 |
| 라이브 상품 연결 해제 | `DELETE` | `/api/lives/{liveId}/products/{productId}` | 필요 | 구현됨 |
| 라이브 연결 상품 목록 | `GET` | `/api/lives/{liveId}/products` | 필요로 문서화됨 | 구현됨 |
| 경매 조건 설정 | `POST` | `/api/lives/{liveId}/auctions` | 필요 | 구현됨 |
| 시착 결과 목록/상세/삭제 | `GET/DELETE` | `/api/users/{userId}/tryons/**` | 필요 | 구현됨 |

## 1. 공개 라이브 목록 API

FE 라이브 목록은 `/lives` 화면에서 카드, 방송 상태, 카테고리 필터, 정렬, 페이지네이션을 제공한다. 현재 FE는 `VITE_LIVE_LIST_API_ENABLED=true`일 때 아래 계약을 기대한다.

```http
GET /api/lives
Authorization: Bearer {accessToken} 선택
```

Query:

| 파라미터 | 타입 | 필수 | 규칙 |
| --- | --- | --- | --- |
| `categoryId` | number | 선택 | 카테고리 필터 |
| `status` | enum | 선택 | `LIVE`, `SCHEDULED` |
| `sort` | enum | 선택 | `LATEST`, `VIEWERS_DESC`, `TITLE_ASC` |
| `page` | number | 필수 | FE는 현재 1-base로 사용 |
| `size` | number | 필수 | 페이지 크기 |

응답 item 필드:

| 필드 | 타입 | 필수 | 규칙 |
| --- | --- | --- | --- |
| `liveId` | number | 필수 | 라이브 ID |
| `title` | string | 필수 | 방송명 |
| `hostId` | number | 필수 | 호스트 ID |
| `hostNickname` | string | 필수 | 호스트 닉네임 |
| `thumbnailUrl` | string/null | 필수 | null이면 FE fallback 사용 |
| `broadcastStatus` | enum | 필수 | `LIVE`, `SCHEDULED`, `CANCELED`, `ENDED` 중 공개 목록은 `LIVE`, `SCHEDULED`만 반환 권장 |
| `categoryId` | number | 필수 | 대표 카테고리 |
| `categoryName` | string | 필수 | `아우터`, `상의`, `하의`, `가방`, `신발`, `액세서리` 중 하나 |
| `scheduledAt` | string/null | 상태별 | 예약 방송 필수 |
| `startedAt` | string/null | 상태별 | 진행 중 방송 필수 |
| `viewerCount` | number | 필수 | 현재 시청자 수 |

페이지 응답은 BE 실제 `PageResponse`가 `content/page/size/totalElements/totalPages/hasNext` 구조인지, FE 공통 타입의 `items/meta` 구조로 맞출지 확정 필요하다.

## 2. 라이브 개설 플로우 보완

현재 BE는 즉시/예약 개설 API가 분리되어 있으므로 FE는 이를 그대로 사용할 수 있다.

즉시 개설:

```http
POST /api/lives
Authorization: Bearer {accessToken}
Content-Type: application/json
```

```json
{
  "title": "지금 바로 여는 빈티지 라이브",
  "thumbnailUrl": "https://cdn.example.com/live/2.jpg"
}
```

예약 개설:

```http
POST /api/lives/schedule
Authorization: Bearer {accessToken}
Content-Type: application/json
```

```json
{
  "title": "빈티지 데님 라이브",
  "thumbnailUrl": "https://cdn.example.com/live/1.jpg",
  "scheduledAt": "2026-08-01T20:00:00"
}
```

필드 규칙:

| 필드 | 타입 | 필수 | 규칙 |
| --- | --- | --- | --- |
| `title` | string | 필수 | 1~200자 |
| `thumbnailUrl` | string/null | 선택 | 최대 500자 |
| `scheduledAt` | string | 예약 필수 | 미래 시각 |

추가 요청:

- 라이브에 연결할 판매 가능 상품 검색 API가 필요하다.

```http
GET /api/lives/create/products
Authorization: Bearer {accessToken}
```

응답 item 후보:

```json
{
  "id": 2001,
  "name": "리바이스 501 빈티지",
  "brand": "Levi's",
  "category": "하의",
  "condition": "A",
  "price": 45000,
  "thumbnailUrl": "https://..."
}
```

- 개설 완료 후 선택 상품들을 `POST /api/lives/{liveId}/products`로 순차 연결하는 방식이 맞는지 확정한다.
- 장비 확인은 FE 로컬 처리이며 BE 저장이 필요한지 확정한다.
- 라이브 설명/대표 브랜드 등 FE 화면 필드를 BE에 저장할지 확정한다. 현재 BE `Live`에는 `title`, `thumbnailUrl`, `scheduledAt`만 있다.

## 3. 라이브 시청 상세 응답 보완

현재 `GET /api/lives/{liveId}`는 기본 방송 정보와 연결 상품의 `productId`, `productTitle`, `sortOrder`를 내려준다. FE는 현재 부족한 상품 필드를 fallback/null로 채우고 있다.

현재 BE 응답에 추가 요청하는 필드:

### 방송/호스트

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `hostProfileImageUrl` | string/null | 선택 | 호스트 프로필 |
| `description` | string/null | 선택 | 라이브 설명 |
| `currentViewerCount` | number | 권장 | 현재 시청자 수 |
| `currentProductId` | number/null | 선택 | 현재 소개 중인 상품 |
| `categories` | array | 선택 | 라이브 대표 카테고리 목록 |

### 연결 상품

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `brandName` | string/null | 권장 | 상품 브랜드 |
| `price` | number/null | 권장 | 상시 판매 가격 또는 경매 시작가 |
| `thumbnailUrl` | string/null | 권장 | 상품 대표 이미지 |
| `saleType` | `AUCTION`, `FIXED_PRICE`/null | 권장 | 라이브 패널 표시 |
| `material` | string/null | 선택 | 상품 소재 |
| `condition` | string/null | 선택 | 상태 등급/라벨 |
| `measurements` | string/object/null | 선택 | 실측 |
| `defectSummary` | string/null | 선택 | 판매자 고지 하자 요약 |

## 4. 채팅/반응/시청 세션 계약

현재 BE에는 채팅 메시지, 반응 이모지, 영상 토큰 발급 API가 없다. 라이브 시청 화면 후속 연동을 위해 아래 계약 확정이 필요하다.

요청 후보:

```http
GET /api/lives/{liveId}/messages
POST /api/lives/{liveId}/messages
POST /api/lives/{liveId}/reactions
POST /api/lives/{liveId}/video-token
```

확정 필요:

- 채팅 전송/수신 프로토콜: REST polling, SSE, WebSocket 중 선택
- 메시지 필드: `id`, `senderId`, `senderNickname`, `content`, `createdAt`, `blocked`
- AI 답변 메시지 표시 방식
- 반응 이모지 집계 또는 fire-and-forget 정책
- OpenVidu 또는 영상 세션 토큰 발급 응답과 만료 정책

## 5. 라이브 AI 시착 계약

현재 BE는 시착 결과 조회/삭제만 있고, 라이브 패널이 필요한 현재 전신 사진 조회/변경과 시착 생성 계약은 없다. 온보딩의 `/api/me/tryon`과 같은 시착 프로필을 재사용하는 방향으로 확정 요청한다.

### 현재 회원 시착 프로필 조회

```http
GET /api/me/tryon
Authorization: Bearer {accessToken}
```

응답 후보:

```json
{
  "success": true,
  "data": {
    "bodyPhotoUrl": "https://...",
    "heightCm": 170,
    "weightKg": 60,
    "chest": 90,
    "waist": 70,
    "hip": 92
  },
  "error": null
}
```

미등록 상태는 `data=null` 또는 `T001` 중 하나로 확정한다. FE 패널은 미등록 상태를 `EMPTY`로 표시한다.

### 현재 회원 시착 프로필 변경

온보딩 통합 요청의 `PUT /api/me/tryon`을 재사용한다.

### 라이브 상품 시착 생성

```http
POST /api/lives/{liveId}/products/{productId}/tryons
Authorization: Bearer {accessToken}
Content-Type: application/json
```

응답 후보:

```json
{
  "success": true,
  "data": {
    "id": 10,
    "productId": 2001,
    "imageUrl": "https://...",
    "status": "COMPLETED",
    "createdAt": "2026-07-30T21:00:00+09:00"
  },
  "error": null
}
```

확정 필요:

- 생성이 동기 완료인지 비동기 job인지
- 상태 enum: `QUEUED`, `PROCESSING`, `COMPLETED`, `FAILED`
- 결과 조회 endpoint를 기존 `/api/users/{userId}/tryons/{id}`로 재사용할지
- 라이브에 연결된 상품만 시착 가능한지 검증
- 시착 프로필 미등록 시 오류 코드: 기존 `T001` 재사용 가능

## FE 관련 파일

- `FE/src/domains/live/api/liveListApi.ts`
- `FE/src/domains/live/api/liveWatchApi.ts`
- `FE/src/domains/live/types/liveList.types.ts`
- `FE/src/domains/live/types/liveCreate.types.ts`
- `FE/src/domains/live/types/liveWatch.types.ts`
- `FE/src/domains/live/pages/LiveListView.vue`
- `FE/src/domains/live/pages/LiveCreatePage.vue`
- `FE/src/domains/live/pages/LiveWatchPage.vue`
- `FE/src/domains/tryon/components/LiveTryOnPanel.vue`
- `FE/src/domains/tryon/types/liveTryOn.types.ts`

## 2026-07-31 최신 BE 확인 결과

라이브 기본 API와 일부 STOMP 계약은 구현되었다. FE는 목록/상세 adapter를 BE 응답에 맞추면 부분 연동할 수 있으나, 방송 영상 토큰, 경매 진행, AI 시착 생성은 아직 mock 유지가 필요하다.

### 반영 확인

| 항목 | 현재 BE 상태 |
| --- | --- |
| 예약 라이브 개설 | `POST /api/lives/schedule` 구현됨. `productIds` 필수 |
| 즉시 라이브 개설 | `POST /api/lives` 구현됨. `productIds` 필수 |
| 공개 라이브 목록 | `GET /api/lives` 구현됨. 비회원 조회 가능 |
| 라이브 상세 | `GET /api/lives/{liveId}` 구현됨. 비회원 조회 가능 |
| 상태 전환 | `PATCH /api/lives/{liveId}/status` 구현됨 |
| 라이브 상품 연결 | `POST/DELETE/GET /api/lives/{liveId}/products` 구현됨 |
| 경매 조건 설정 | `POST /api/lives/{liveId}/auctions` 구현됨 |
| 채팅 이력 | `GET /api/lives/{liveId}/chat-messages` 구현됨 |
| 채팅 STOMP | publish `/app/lives/{liveId}/chat`, subscribe `/topic/lives/{liveId}/chat` 구현됨 |
| 반응 STOMP | publish `/app/lives/{liveId}/reactions`, subscribe `/topic/lives/{liveId}/reactions` 구현됨 |
| 시청자 수 topic | `/topic/lives/{liveId}/viewers` 응답 DTO 존재 |
| 시착 결과 조회/삭제 | `GET/DELETE /api/users/{userId}/tryons/**` 구현됨 |

### FE 연동 시 주의

- `GET /api/lives` query는 `categoryIds` 복수 파라미터다. 기존 FE의 `categoryId` 단일 query와 다르다.
- 라이브 목록 응답은 `categoryId/categoryName` 단일 필드가 아니라 `categories[]`를 내려준다.
- 라이브 목록도 BE `PageResponse(content/page/...)` 구조다. FE `items/meta` 변환이 필요하다.
- 라이브 상세 `currentViewerCount`가 BE DTO에 있는데 현재 FE 타입/adapter는 이를 누락하고 `null`로 두고 있다.
- 라이브 연결 상품 응답은 `productId`, `productTitle`, `sortOrder` 중심이다. FE 시청 화면 카드에 필요한 `brandName`, `price`, `thumbnailUrl`, `saleType`, `condition`, `material`, `measurements`, `defectSummary`는 아직 없다.
- 채팅 REST endpoint는 `/messages`가 아니라 `/chat-messages`다.

### 추가 요청

- 라이브 생성 화면에서 판매자가 연결할 수 있는 상품 후보 조회 endpoint를 제공해 달라. 예: `GET /api/lives/create/products`.
- 라이브 상세 연결 상품 응답에 카드 표시용 상품 필드를 보강해 달라.
- 영상 세션/OpenVidu 토큰 발급 endpoint를 확정해 달라. 예: `POST /api/lives/{liveId}/video-token`.
- 경매 시작, 입찰, 현재 경매 snapshot, 낙찰 결과 조회/구독 계약을 확정해 달라.
- 라이브 AI 시착 생성 endpoint를 확정해 달라. 예: `POST /api/lives/{liveId}/products/{productId}/tryons`.
- 현재 회원 시착 프로필 조회/수정 endpoint(`/api/me/tryon`)과 라이브 시착 생성의 관계를 확정해 달라.
