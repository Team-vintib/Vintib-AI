# 공개 라이브 목록 API 계약 요청

- **요청 파트**: FE
- **대상 파트**: BE
- **관련 이슈**: `S15P11A108-413`, `S15P11A108-415`, `S15P11A108-418`
- **관련 화면**: 라이브 목록 `/lives`

## 배경

FE는 공개 라이브 목록에서 카드, 방송 상태, 카테고리 필터와 정렬을 구현하고 있습니다.
현재는 mock data를 사용하며, `S15P11A108-418`에서 실제 목록 API로 교체할 예정입니다.

공개 목록에는 `LIVE`, `SCHEDULED` 상태만 노출합니다. `ENDED`, `CANCELED` 방송과
경매·상시 판매 같은 판매 방식 조건은 이 화면의 필터 및 조회 대상에서 제외합니다.

## 2026-07-29 현재 확인 결과

`origin/develop-BE` `7962ec7` 기준으로 아래 내용을 확인했습니다.

- `GET /api/lives/{liveId}` 라이브 상세 조회는 구현되어 있습니다.
- 공개 목록용 `GET /api/lives`는 아직 구현되어 있지 않습니다.
- `LiveDetailResponse`에는 `id`, `hostNickname`, `title`, `thumbnailUrl`, `status`,
  `scheduledAt`, `startedAt`, `endedAt`, `peakViewerCount`가 있습니다.
- 목록 필터에 필요한 `categoryId`, `categoryName`과 진행 중인 방송의
  현재 `viewerCount`는 제공되지 않습니다.
- `LiveRepository`에는 목록 필터·정렬·pagination 조회가 없습니다.
- `GET /api/categories` 공개 카테고리 마스터는 이미 구현되어 있어 그대로 재사용할 수 있습니다.
- `SecurityConfig`에는 상세 조회 `GET /api/lives/{liveId}`만 공개되어 있으므로
  목록 `GET /api/lives`도 비회원 허용 규칙에 추가해야 합니다.

따라서 FE는 목록 호출 함수와 DTO adapter까지 준비하되 기본 실행에서는 mock adapter를 사용합니다.
아래 계약이 반영되기 전에는 `VITE_LIVE_LIST_API_ENABLED`를 `true`로 전환하지 않습니다.

## 요청 API 1: 공개 라이브 목록 조회

- **Method / URL**: `GET /api/lives`
  - FE 공통 Axios의 `baseURL`이 `/api`이므로 FE 코드에서는 `GET /lives`로 호출합니다.
- **인증**: 비회원도 조회 가능한 공개 API
- **Content-Type**: `application/json`

### 요청 query

| 이름         | 타입                                  | 필수   | 기본값   | 설명                  |
| ------------ | ------------------------------------- | ------ | -------- | --------------------- |
| `categoryId` | `Long`                                | 아니요 | 전체     | 라이브 대표 카테고리  |
| `status`     | `LIVE \| SCHEDULED`                   | 아니요 | 전체     | 공개 목록 방송 상태   |
| `sort`       | `LATEST \| VIEWERS_DESC \| TITLE_ASC` | 아니요 | `LATEST` | 정렬 기준             |
| `page`       | `int`                                 | 아니요 | `0`      | 0부터 시작하는 페이지 |
| `size`       | `int`                                 | 아니요 | `12`     | 페이지 크기           |

요청 예시:

```http
GET /api/lives?categoryId=10&status=LIVE&sort=VIEWERS_DESC&page=0&size=12
```

### 성공 응답

프로젝트 공통 `ApiResponse<PageResponse<T>>` 구조에 맞춰 주시기를 요청합니다.

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "liveId": 101,
        "title": "90s 데님 재킷 라이브 셀렉션",
        "hostId": 31,
        "hostNickname": "Archive Room",
        "thumbnailUrl": "https://cdn.example.com/live/101.jpg",
        "broadcastStatus": "LIVE",
        "categoryId": 10,
        "categoryName": "아우터",
        "scheduledAt": "2026-07-29T11:00:00+09:00",
        "startedAt": "2026-07-29T11:02:10+09:00",
        "viewerCount": 128
      }
    ],
    "meta": {
      "page": 0,
      "size": 12,
      "totalElements": 25,
      "totalPages": 3
    }
  },
  "error": null
}
```

### 카드 필수 필드

| 필드              | 타입              | nullable | FE 사용처                            |
| ----------------- | ----------------- | -------- | ------------------------------------ |
| `liveId`          | `Long`            | 아니요   | `/lives/{liveId}` 이동               |
| `title`           | `String`          | 아니요   | 카드 제목                            |
| `hostId`          | `Long`            | 아니요   | 판매자 식별                          |
| `hostNickname`    | `String`          | 아니요   | 판매자 표시명                        |
| `thumbnailUrl`    | `String`          | 가능     | 카드 이미지, null이면 FE 기본 이미지 |
| `broadcastStatus` | enum              | 아니요   | `LIVE`, `SCHEDULED` 상태 배지        |
| `categoryId`      | `Long`            | 아니요   | 카테고리 필터 식별자                 |
| `categoryName`    | `String`          | 아니요   | 카테고리 표시명                      |
| `scheduledAt`     | ISO-8601 datetime | 가능     | 예정 방송 시각                       |
| `startedAt`       | ISO-8601 datetime | 가능     | 실제 시작 시각                       |
| `viewerCount`     | `int`             | 아니요   | 카드 시청자 수                       |

시간 값은 시간대가 포함된 ISO-8601 문자열로 전달해 주세요.
FE adapter는 `LIVE`이면 `startedAt`, `SCHEDULED`이면 `scheduledAt`을 카드 표시 시각으로 사용합니다.

### 상태와 시청자 수 정책

- 공개 목록 응답에는 `LIVE`, `SCHEDULED`만 포함합니다.
- `ENDED`, `CANCELED`는 상태 query 허용값과 공개 목록 결과에서 모두 제외합니다.
- `viewerCount` 기준:
  - `LIVE`: 현재 동시 시청자 수
  - `SCHEDULED`: `0`
- 현재 동시 시청자 수의 원천이 OpenVidu/Redis 등이라면 조회 방식과 갱신 주기를 Swagger에 명시해 주세요.

### 정렬 정책

- 모든 정렬은 동률일 때 순서가 흔들리지 않도록 마지막 기준을 `liveId DESC`로 둡니다.
- `LATEST`: `LIVE`는 `startedAt`, `SCHEDULED`는 `scheduledAt` 기준 내림차순
- `VIEWERS_DESC`: `viewerCount DESC`, 이후 표시 시각 내림차순
- `TITLE_ASC`: 한글 제목 오름차순

### 빈 목록과 오류

- 조건에 맞는 라이브가 없으면 `404` 대신 `200 OK`, `items: []`,
  `totalElements: 0`, `totalPages: 0`을 반환해 주세요.
- 잘못된 status, sort, 음수 page/size는 `400`과 공통 `ApiErrorBody`로 반환해 주세요.
- 서버 오류는 `500`과 공통 오류 envelope를 사용해 주세요.

## 확인된 API 2: 카테고리 필터 목록

페이지네이션된 현재 목록에서 카테고리를 추출하면 전체 필터 항목을 구성할 수 없으므로
카테고리 마스터 조회가 필요합니다.

- 현재 공통 카테고리 API `GET /api/categories`가 구현되어 있으므로 그대로 재사용합니다.
- 라이브 전용 category endpoint 또는 `usage=LIVE` query는 요청하지 않습니다.
- 라이브 목록 응답의 `categoryId`가 이 API의 `id`를 참조해야 합니다.

응답 항목:

```json
{
  "success": true,
  "data": [
    {
      "id": 10,
      "parentId": null,
      "name": "아우터",
      "depth": 1
    }
  ],
  "error": null
}
```

## BE에서 확정이 필요한 도메인 항목

1. 현재 `live` 테이블에 `category_id`가 없다면 아래 중 한 가지 기준 확정이 필요합니다.
   - 라이브에 대표 카테고리를 직접 저장
   - 연결된 `live_product` 상품 카테고리에서 대표값 결정
2. 라이브에 복수 카테고리를 허용한다면 응답을 `categories[]`로 바꾸고 query를
   `categoryIds` 복수 선택으로 제공해 주세요.
3. `LIVE` 상태의 현재 동시 시청자 수를 어디에서 조회할지 확정이 필요합니다.
4. 공개 목록에서 `ENDED`, `CANCELED`가 조회되지 않는 정책을 API와 Swagger에 명시해 주세요.

## FE 임시 처리

- BE 목록 endpoint가 준비될 때까지 mock data를 브라우저에서만 필터링·정렬합니다.
- FE 임시 공개 상태는 `LIVE`, `SCHEDULED`입니다.
- FE 임시 정렬은 `LATEST`, `VIEWERS_DESC`, `TITLE_ASC`입니다.
- URL query 동기화와 서버 pagination은 실제 API 연결 전까지 사용하지 않습니다.
- `S15P11A108-418`에서 요청 계약 기준 DTO·화면 adapter와 loading, empty, error,
  retry 상태를 구현했습니다.
- mock 상태 확인 URL은 `/lives?mock=loading`, `/lives?mock=empty`,
  `/lives?mock=error`입니다.
- 목록 endpoint, 카테고리 ID와 현재 시청자 수, query/pagination 계약이 반영되면
  환경 플래그를 켜고 실제 응답 E2E를 진행합니다.

## 완료 기준

- Swagger에 공개 목록 endpoint, query와 응답 DTO가 문서화되어야 합니다.
- 전체·상태·카테고리 필터와 각 정렬 조건의 통합 테스트가 필요합니다.
- `ENDED`, `CANCELED`가 공개 목록과 pagination 집계에서 제외되는 테스트가 필요합니다.
- 빈 결과가 `200`의 빈 page로 반환되는 테스트가 필요합니다.

## 관련 자료

- API 후보 목록: `APIs.md`
- FE 공통 응답 타입: `FE/src/shared/types/api.types.ts`
- FE 화면: `FE/src/domains/live/pages/LiveListView.vue`
- FE 타입: `FE/src/domains/live/types/liveList.types.ts`
- FE 계획: `.codex/plans/fe/HS015-live-list.md`
