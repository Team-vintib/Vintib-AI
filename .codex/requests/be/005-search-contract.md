# 검색 도메인 API 계약 요청

## 요청자 파트 / 대상 파트

- 요청자: FE
- 대상: BE

## 배경/이유

FE 검색 결과 화면은 상품, 라이브, 회원 결과를 탭으로 구분하고 카테고리/상태/가격/판매 유형 필터와 정렬, 페이지네이션을 제공한다. 현재 BE에 검색 API가 없어 `domains/search`의 mock data를 클라이언트에서 필터링하고 있으므로 FE 구현 기준으로 통합 검색 API 계약 확정을 요청한다.

기존 `008-search-result-api-contract.md`를 이 문서로 병합한다.

## 현재 구현 확인

- BE 검색 컨트롤러/서비스는 없다.
- FE는 검색어가 없으면 초기 상태를 표시하고 API 호출 없이 대기할 수 있다.
- FE는 상품 찜/회원 팔로우 상태를 화면 상태로만 토글한다. 실제 저장 API가 확정되면 social/follow 도메인 API로 연결한다.

## 요청 API

통합 검색 단일 endpoint를 우선 후보로 요청한다.

```http
GET /api/search
Authorization: Bearer {accessToken} 선택
```

상품/라이브/회원 탭별 endpoint 분리가 더 적절하다면 endpoint 분리 여부와 각 응답 구조 확정을 요청한다.

## Query 파라미터

| 파라미터 | 타입 | 필수 | 규칙 |
| --- | --- | --- | --- |
| `keyword` | string | 필수 | 검색어 |
| `type` | enum | 선택 | `all`, `product`, `live`, `member` |
| `categories` | number[] 또는 comma string | 선택 | 상품 카테고리 ID |
| `conditions` | string[] 또는 comma string | 선택 | `S`, `A`, `B`, `C` |
| `saleTypes` | string[] 또는 comma string | 선택 | `DIRECT`, `AUCTION` |
| `minPrice` | number | 선택 | 0 이상 |
| `maxPrice` | number | 선택 | 0 이상, `minPrice <= maxPrice` |
| `sort` | enum | 선택 | `LATEST`, `PRICE_ASC`, `PRICE_DESC` |
| `page` | number | 선택 | 1-base 또는 0-base 여부 확정 필요 |
| `size` | number | 선택 | 페이지 크기 |

가격 범위가 잘못되면 `400`, `C001`, field `minPrice` 또는 `maxPrice`로 내려주길 요청한다.

## 응답 후보

```json
{
  "success": true,
  "data": {
    "products": {
      "items": [],
      "meta": {
        "page": 1,
        "size": 20,
        "totalElements": 0,
        "totalPages": 0
      }
    },
    "lives": {
      "items": [],
      "meta": {
        "page": 1,
        "size": 20,
        "totalElements": 0,
        "totalPages": 0
      }
    },
    "members": {
      "items": [],
      "meta": {
        "page": 1,
        "size": 20,
        "totalElements": 0,
        "totalPages": 0
      }
    }
  },
  "error": null
}
```

BE 공통 `PageResponse<T>`를 재사용한다면 실제 응답 구조는 `content/page/size/totalElements/totalPages/hasNext`로 문서화하고, FE가 adapter에서 `items/meta`로 변환한다.

## 상품 결과 필드

| 필드 | 타입 | 필수 | 규칙 |
| --- | --- | --- | --- |
| `id` | number | 필수 | 상품 ID |
| `brand` | string | 필수 | 브랜드 표시명 |
| `name` | string | 필수 | 상품명 |
| `sellerName` | string | 필수 | 판매자 닉네임 |
| `price` | number | 필수 | 상시 판매 가격 또는 표시 가격 |
| `createdAt` | string | 필수 | ISO date-time |
| `conditionGrade` | enum | 필수 | `S`, `A`, `B`, `C` |
| `saleType` | enum | 필수 | `DIRECT`, `AUCTION` |
| `categoryName` | string | 필수 | 카테고리 표시명 |
| `imageUrl` | string | 필수 | 대표 이미지 |
| `imageAlt` | string/null | 선택 | 없으면 FE 생성 가능 |
| `isLiked` | boolean | 필수 | 로그인 사용자 기준, 비로그인 false |
| `bidCount` | number/null | 경매 상품 | 현재 입찰 수 |
| `timeLeftLabel` | string/null | 경매 상품 | 남은 시간 표시 문자열 또는 FE 계산용 종료 시각으로 대체 가능 |
| `isLive` | boolean/null | 선택 | 라이브 판매 중 여부 |
| `viewerCount` | number/null | 선택 | 라이브 판매 중이면 시청자 수 |

## 라이브 결과 필드

| 필드 | 타입 | 필수 | 규칙 |
| --- | --- | --- | --- |
| `id` | number | 필수 | 라이브 ID |
| `title` | string | 필수 | 방송명 |
| `hostName` | string | 필수 | 호스트 닉네임 |
| `status` | enum | 필수 | `LIVE`, `SCHEDULED`, `ENDED` |
| `scheduledAt` | string/null | 상태별 | 예약 방송 |
| `startedAt` | string/null | 상태별 | 진행/종료 방송 |
| `productCount` | number | 필수 | 연결 상품 수 |
| `thumbnailUrl` | string | 필수 | 썸네일 |

## 회원 결과 필드

| 필드 | 타입 | 필수 | 규칙 |
| --- | --- | --- | --- |
| `id` | number | 필수 | 회원 ID |
| `nickname` | string | 필수 | 닉네임 |
| `profileImageUrl` | string/null | 선택 | 프로필 이미지 |
| `description` | string | 필수 | 소개 문구, 없으면 빈 문자열 |
| `followerCount` | number | 필수 | 팔로워 수 |
| `productCount` | number | 필수 | 판매 상품 수 |
| `liveCount` | number | 필수 | 라이브 수 |
| `isFollowing` | boolean | 필수 | 로그인 사용자 기준, 비로그인 false |

## 사용자 액션 API 확인 요청

검색 결과에서 사용자 액션을 실제 저장하려면 아래 기존/예정 API를 FE가 사용할 수 있는지 확정 요청한다.

- 상품 찜: `POST /api/users/{id}/wishes` 또는 현재 구현된 wish endpoint
- 상품 찜 해제
- 회원 팔로우
- 회원 팔로우 해제

FE가 현재 회원 ID를 보내지 않는 `/api/me/**` 형태가 필요한지도 함께 확정해 달라.

## FE 관련 파일

- `FE/src/domains/search/pages/SearchResultsPage.vue`
- `FE/src/domains/search/types/search.types.ts`
- `FE/src/domains/search/constants/searchMockData.ts`
- `FE/src/domains/search/constants/searchFilterOptions.ts`
- `FE/docs/frontend/api/api-index.md`

## 2026-07-31 최신 BE 확인 결과

현재 BE에는 통합 검색 API가 없다. 이 문서의 요청은 전체 유효하다.

FE 검색 화면은 다음 결과를 한 화면에서 다룬다.

- 상품
- 라이브
- 회원/판매자

우선 구현 요청:

- `GET /api/search` 단일 endpoint 또는 도메인별 endpoint 조합 방식을 확정해 달라.
- query 이름과 enum을 확정해 달라: `keyword`, `type`, `categories`, `conditions`, `saleTypes`, `minPrice`, `maxPrice`, `sort`, `page`, `size`.
- `type=all`일 때 섹션별 preview를 내려줄지, FE가 각 탭 endpoint를 조합할지 확정해 달라.
- 검색 결과 상품에는 `isWished`, 회원에는 `isFollowing`을 포함해 달라.
