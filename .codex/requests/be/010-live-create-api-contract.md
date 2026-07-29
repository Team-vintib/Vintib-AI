# S15P11A108-406/433/407 라이브 개설 API 계약 요청

## 요청 배경

FE의 라이브 개설 화면은 `/lives/new`에서 라이브 유형 선택, 방송 정보 입력, 판매 상품 선택,
예약 일정 입력, 장비 확인, 완료 단계를 순차 진행하도록 구현되어 있다.

현재 실제 라이브 생성/예약 API와 판매 상품 검색 API 계약이 없어 `domains/live`의 mock data와
화면 상태만으로 동작하므로, 아래 FE 선행 구조를 기준으로 BE 계약 확정을 요청한다.

## 요청 API

라이브에 연결할 판매 상품 조회 API가 필요하다.

```http
GET /api/lives/create/products
Authorization: Bearer {accessToken}
```

라이브 즉시 생성과 예약 생성을 하나의 endpoint로 처리하는 형태를 우선 후보로 요청한다.

```http
POST /api/lives
Authorization: Bearer {accessToken}
Content-Type: application/json
```

즉시 시작 라이브에서 생성과 실제 송출 시작을 분리해야 한다면 아래 endpoint 추가 여부도 확인이
필요하다.

```http
POST /api/lives/{liveId}/start
Authorization: Bearer {accessToken}
```

- 라이브 개설은 로그인 사용자를 전제로 한다.
- 판매자 권한 또는 일반 회원 개설 가능 여부는 BE 정책 확정이 필요하다.
- 장비 확인은 현재 FE에서 `navigator.mediaDevices.getUserMedia`로 카메라/마이크 권한과 미리보기를
  처리한다. BE 장비 테스트 API는 별도로 필요하지 않지만, 실제 송출 SDK 연동 시 송출 토큰/URL
  발급 계약은 필요하다.

## 상품 조회 query 후보

| 필드 | 타입 | 필수 | 규칙 |
| --- | --- | --- | --- |
| `keyword` | string | 선택 | 상품명, 브랜드명 검색어 |
| `page` | number | 선택 | 기본값 `1` |
| `size` | number | 선택 | 기본값 BE 확정 필요 |
| `status` | enum | 선택 | 라이브 연결 가능한 상품 상태. 후보: `ON_SALE`, `AVAILABLE` |

- FE는 현재 검색어가 비어 있어도 선택 가능한 상품 목록을 보여준다.
- 라이브에 연결 가능한 상품 상태 조건은 BE에서 확정해야 한다.
- 이미 판매 완료, 삭제, 검수 미완료, 다른 라이브에 연결된 상품의 노출 가능 여부 확인이 필요하다.

## 라이브 생성 요청 후보

```json
{
  "mode": "IMMEDIATE",
  "title": "가을 아우터 라이브",
  "description": "오늘 입기 좋은 빈티지 아우터를 소개합니다.",
  "mainBrand": "Burberry",
  "productIds": [101, 102],
  "scheduledAt": null
}
```

예약 라이브:

```json
{
  "mode": "SCHEDULED",
  "title": "주말 빈티지 백 예약 방송",
  "description": "가방과 잡화를 중심으로 소개합니다.",
  "mainBrand": "Prada",
  "productIds": [103],
  "scheduledAt": "2026-07-30T20:00:00+09:00"
}
```

| 필드 | 타입 | 필수 | 규칙 |
| --- | --- | --- | --- |
| `mode` | enum | 필수 | `IMMEDIATE`, `SCHEDULED` |
| `title` | string | 필수 | 방송 제목. FE 현재 최대 40자 |
| `description` | string | 필수 | 한 줄 소개. FE 현재 최대 80자 |
| `mainBrand` | string | 필수 | 대표 브랜드 |
| `productIds` | number[]/string[] | 필수 | 1개 이상 |
| `scheduledAt` | string/null | 예약 필수 | ISO 8601 일시. `IMMEDIATE`는 `null` |

- FE는 예약 일시가 현재 시각 이후인지 선검증한다.
- BE에서도 필수값, 글자 수, 상품 소유권, 상품 상태, 예약 가능 시간을 재검증해야 한다.
- `scheduledAt`의 timezone 기준은 `Asia/Seoul` 또는 offset 포함 ISO 문자열 중 하나로 확정이 필요하다.

## 응답 규격

판매 상품 조회 성공:

```http
200 OK
```

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": 101,
        "name": "90s 오버핏 데님 재킷",
        "brand": "Levi's",
        "category": "아우터",
        "price": 89000,
        "thumbnailUrl": "https://..."
      }
    ],
    "page": 1,
    "size": 20,
    "totalPages": 1,
    "totalElements": 1
  },
  "error": null
}
```

라이브 생성 성공:

```http
201 Created
```

```json
{
  "success": true,
  "data": {
    "liveId": 301,
    "mode": "IMMEDIATE",
    "status": "READY",
    "title": "가을 아우터 라이브",
    "description": "오늘 입기 좋은 빈티지 아우터를 소개합니다.",
    "mainBrand": "Burberry",
    "productIds": [101, 102],
    "scheduledAt": null,
    "createdAt": "2026-07-29T14:30:00+09:00",
    "watchUrl": "/lives/301",
    "broadcast": {
      "ingestUrl": "rtmp://...",
      "streamKey": "optional",
      "token": "optional",
      "expiresAt": "2026-07-29T16:30:00+09:00"
    }
  },
  "error": null
}
```

- 예약 라이브는 `status` 후보로 `SCHEDULED`를 내려주길 요청한다.
- 즉시 라이브에서 송출 정보를 FE가 직접 사용하지 않는 구조라면 `broadcast`는 생략 가능하다.
- 생성 후 FE 이동 정책은 즉시 라이브는 `liveId` 기반 방송/시청 route, 예약 라이브는 라이브 목록 이동이다.

## 필요한 응답 후보

### 선택 상품

| 필드 | 타입 | 필수 | 규칙 |
| --- | --- | --- | --- |
| `id` | number/string | 필수 | 선택 상태와 key, 생성 요청 `productIds`에 사용 |
| `name` | string | 필수 | 상품명 |
| `brand` | string | 필수 | 브랜드 표시명 |
| `category` | string | 필수 | 카테고리 표시명 |
| `price` | number | 필수 | 표시 가격 |
| `thumbnailUrl` | string | 필수 | 접근 가능한 대표 이미지 URL |
| `status` | enum | 선택 | 선택 가능 상태 표시가 필요하면 사용 |

### 라이브 생성 결과

| 필드 | 타입 | 필수 | 규칙 |
| --- | --- | --- | --- |
| `liveId` | number/string | 필수 | 생성된 라이브 식별자 |
| `mode` | enum | 필수 | `IMMEDIATE`, `SCHEDULED` |
| `status` | enum | 필수 | 후보: `READY`, `LIVE`, `SCHEDULED` |
| `title` | string | 필수 | 생성된 방송 제목 |
| `description` | string | 필수 | 한 줄 소개 |
| `mainBrand` | string | 필수 | 대표 브랜드 |
| `productIds` | number[]/string[] | 필수 | 연결된 상품 ID 목록 |
| `scheduledAt` | string/null | 예약 필수 | 예약 일시 |
| `createdAt` | string | 필수 | 생성 일시 |
| `watchUrl` | string/null | 선택 | FE route 조립 대신 BE 제공이 필요하면 사용 |
| `broadcast.ingestUrl` | string/null | 즉시 시작 후보 | 송출 서버 URL |
| `broadcast.streamKey` | string/null | 즉시 시작 후보 | 송출 키 |
| `broadcast.token` | string/null | 즉시 시작 후보 | 방송 SDK 인증 토큰 |
| `broadcast.expiresAt` | string/null | 즉시 시작 후보 | 송출 정보 만료 시각 |

## 오류 응답 후보

| 상황 | HTTP | 코드 후보 | FE 처리 |
| --- | --- | --- | --- |
| 인증 없음 | 401 | `UNAUTHORIZED` | 로그인 화면으로 이동 |
| 개설 권한 없음 | 403 | `LIVE_CREATE_FORBIDDEN` | 권한 안내 |
| 필수값 누락/형식 오류 | 400 | `INVALID_LIVE_CREATE_REQUEST` | 필드 오류 표시 |
| 과거 예약 시간 | 400 | `INVALID_SCHEDULE_TIME` | 일정 오류 표시 |
| 상품 없음 | 404 | `PRODUCT_NOT_FOUND` | 상품 재선택 안내 |
| 상품 선택 불가 | 409 | `PRODUCT_NOT_AVAILABLE_FOR_LIVE` | 상품 재선택 안내 |
| 송출 정보 발급 실패 | 500/502 | `BROADCAST_SESSION_CREATE_FAILED` | 재시도 안내 |

## FE 처리

- BE 계약 확정 전까지 `liveCreateMockData.ts`의 상품 mock과 페이지 내부 상태로 화면을 렌더링한다.
- 상품 검색 API가 확정되면 상품 조회를 adapter 함수로 분리하고, 응답 DTO를 `LiveCreateProduct`로 매핑한다.
- 라이브 생성 API가 확정되면 완료 단계 진입 전에 `POST /api/lives`를 호출하도록 변경한다.
- 즉시 라이브 생성 성공 시 `liveId`를 사용해 라이브 진행/시청 route로 이동한다.
- 예약 라이브 생성 성공 시 라이브 목록 route로 이동한다.
- 장비 확인 실패는 현재 FE 브라우저 권한 오류로 처리하며, BE 오류와 분리한다.

## BE 확인 필요

1. 라이브 개설 권한 기준을 일반 회원으로 볼지, 판매자/사업자 인증 사용자로 제한할지 확정해야 한다.
2. 라이브 생성 endpoint를 즉시/예약 공통으로 둘지, 별도 endpoint로 분리할지 확정해야 한다.
3. 즉시 라이브 생성과 실제 송출 시작을 같은 요청에서 처리할지, `start` 요청으로 분리할지 확정해야 한다.
4. 연결 가능한 상품 조회 endpoint와 상품 상태 조건을 확정해야 한다.
5. 라이브에 연결 가능한 상품 개수 제한을 확정해야 한다.
6. 제목, 한 줄 소개, 대표 브랜드 글자 수와 허용 문자를 확정해야 한다.
7. 예약 가능 최소 시간, 최대 예약 가능 기간, timezone 처리 기준을 확정해야 한다.
8. 방송 SDK/WebRTC 도입 시 FE에 필요한 송출 정보 필드와 보안 정책을 확정해야 한다.
9. 구현 후 Swagger에 라이브 생성 요청/응답 DTO, 상품 조회 query, 오류 응답을 문서화해야 한다.

## FE 관련 파일

- `FE/src/domains/live/pages/LiveCreatePage.vue`
- `FE/src/domains/live/types/liveCreate.types.ts`
- `FE/src/domains/live/constants/liveCreateMockData.ts`
- `FE/src/shared/constants/routes.ts`
- `FE/src/app/providers/router/routes.ts`
