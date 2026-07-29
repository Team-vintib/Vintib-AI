# S15P11A108-401 검색 결과 화면 API 계약 보완 요청

## 요청 배경

FE의 검색 결과 화면은 상품, 라이브, 회원 결과를 탭으로 구분하고 카테고리·상태·가격·판매 유형
필터와 정렬, 페이지네이션을 제공하도록 구현되어 있다.

현재 실제 검색 API 계약이 없어 `domains/search`의 mock data를 클라이언트에서 필터링하고
있으므로, 아래 FE 선행 계약을 기준으로 통합 검색 API와 사용자 액션 API 정책 확정을 요청한다.

## 요청 API

통합 검색 단일 endpoint를 우선 후보로 요청한다.

```http
GET /api/search
Authorization: Bearer {accessToken} 선택
```

상품/라이브/회원 탭별 endpoint 분리가 더 적절하다면 endpoint 분리 여부와 각 응답 구조 확정이
필요하다.

## query 후보

| 필드 | 타입 | 필수 | 규칙 |
| --- | --- | --- | --- |
| `keyword` | string | 필수 | 검색어 |
| `type` | enum | 선택 | `all`, `product`, `live`, `member`. 기본값 `all` |
| `page` | number | 선택 | 개별 탭 페이지 번호. 기본값 `1` |
| `size` | number | 선택 | 페이지 크기. 기본값 BE 확정 필요 |
| `categories` | string[] | 선택 | 상품 카테고리 복수 선택 |
| `conditions` | string[] | 선택 | 상품 상태 등급 복수 선택 |
| `saleTypes` | enum[] | 선택 | `DIRECT`, `AUCTION` |
| `minPrice` | number | 선택 | 최소 가격 |
| `maxPrice` | number | 선택 | 최대 가격 |
| `sort` | enum | 선택 | `LATEST`, `PRICE_ASC`, `PRICE_DESC` |

- `all` 탭과 1페이지에서는 FE가 `page`를 생략할 수 있다.
- 검색어 변경, 탭 변경, 필터 적용, 정렬 변경 시 FE는 `page`를 1페이지로 초기화한다.
- `status=loading|error|empty` query는 FE 상태 화면 확인용 mock query이며 실제 API query가 아니다.

## 응답 규격

성공:

```http
200 OK
```

```json
{
  "success": true,
  "data": {
    "counts": {
      "product": 0,
      "live": 0,
      "member": 0
    },
    "products": {
      "items": [],
      "page": 1,
      "size": 20,
      "totalPages": 0,
      "totalElements": 0
    },
    "lives": {
      "items": [],
      "page": 1,
      "size": 20,
      "totalPages": 0,
      "totalElements": 0
    },
    "members": {
      "items": [],
      "page": 1,
      "size": 20,
      "totalPages": 0,
      "totalElements": 0
    }
  },
  "error": null
}
```

- 위 구조는 FE 후보이며 실제 pagination envelope 필드명 확정이 필요하다.
- `all` 탭에서는 상품/라이브/회원 결과 preview 개수와 전체 count 제공 방식 확정이 필요하다.
- 개별 탭에서는 해당 탭 결과와 pagination 정보를 제공해야 한다.

## 필요한 응답 후보

### 상품 결과

| 필드 | 타입 | 필수 | 규칙 |
| --- | --- | --- | --- |
| `id` | number/string | 필수 | 상품 상세 이동과 카드 key |
| `title` | string | 필수 | 상품명 |
| `thumbnailUrl` | string | 필수 | 접근 가능한 대표 이미지 URL |
| `price` | number/null | 선택 | 상품 가격 |
| `saleType` | enum | 필수 | `DIRECT`, `AUCTION` |
| `condition` | string/null | 선택 | 상품 상태 등급 |
| `sellerName` | string | 필수 | 판매자명 |
| `isWished` | boolean/null | 로그인 시 선택 | 회원별 찜 상태 |
| `createdAt` | string | 정렬 기준 요청 | 최신순 정렬 기준 |

### 라이브 결과

| 필드 | 타입 | 필수 | 규칙 |
| --- | --- | --- | --- |
| `id` | number/string | 필수 | 라이브 상세 이동과 카드 key |
| `title` | string | 필수 | 라이브 제목 |
| `thumbnailUrl` | string | 필수 | 접근 가능한 대표 이미지 URL |
| `status` | enum | 필수 | 라이브 상태 |
| `startedAt` | string/null | 선택 | 시작 일시 |
| `scheduledAt` | string/null | 선택 | 예약 일시 |
| `viewerCount` | number/null | 선택 | 시청자 수 |
| `productCount` | number/null | 선택 | 연결 상품 수 |
| `hostName` | string | 필수 | 호스트/판매자명 |

### 회원 결과

| 필드 | 타입 | 필수 | 규칙 |
| --- | --- | --- | --- |
| `id` | number/string | 필수 | 회원 프로필 이동과 카드 key |
| `nickname` | string | 필수 | 회원 표시명 |
| `profileImageUrl` | string/null | 선택 | 프로필 이미지 |
| `followerCount` | number/null | 선택 | 팔로워 수 |
| `productCount` | number/null | 선택 | 판매 상품 수 |
| `isFollowing` | boolean/null | 로그인 시 선택 | 회원별 팔로우 상태 |

## FE 처리

- `/search` route는 공개 접근으로 연결되어 있다.
- `keyword`, `type`, `page`, `sort`, 필터 query를 URL에 반영한다.
- `전체` 탭은 상품/라이브/회원 섹션별 3개 preview를 보여주고, `전체보기` 클릭 시 `type=product|live|member`로 이동한다.
- `product`, `live`, `member` 개별 탭은 페이지네이션을 제공한다.
- 비로그인 상태에서 찜/팔로우를 누르면 `/auth/login?redirect=...`로 이동한다.
- 로그인 상태의 찜/팔로우는 현재 화면 안에서만 mock toggle 처리한다.

## BE 확인 필요

1. 통합 검색 단일 endpoint와 탭별 endpoint 분리 중 어떤 구조를 사용할지 확정해야 한다.
2. 탭별 결과 count 제공 방식과 pagination envelope 필드명을 확정해야 한다.
3. `all` 탭 preview 개수와 `전체보기` 진입 시 재호출 정책을 확정해야 한다.
4. 상품 정렬 기준과 query 값을 확정해야 한다. FE 후보는 `LATEST`, `PRICE_ASC`, `PRICE_DESC`이다.
5. 상품, 라이브, 회원 결과 DTO 필드와 nullable 정책을 확정해야 한다.
6. 상품 찜 등록/해제 endpoint와 비로그인 클릭 처리 정책을 확정해야 한다.
7. 회원 팔로우 등록/해제 endpoint와 비로그인 클릭 처리 정책을 확정해야 한다.
8. 회원 검색 결과 카드 클릭 시 이동할 회원 프로필 route 또는 조회 endpoint를 확정해야 한다.
9. 구현 후 Swagger에 검색 query, 응답 DTO, pagination, 오류 응답을 문서화해야 한다.

## FE 관련 파일

- `FE/src/domains/search/pages/SearchResultsPage.vue`
- `FE/src/domains/search/types/search.types.ts`
- `FE/src/domains/search/constants/searchMockData.ts`
- `FE/docs/frontend/api/api-index.md`
- `FE/docs/frontend/decisions/open-questions.md`
