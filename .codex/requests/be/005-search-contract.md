# 005 Search API 요청

## 1. 요청 개요

- 요청 파트: FE
- 대상 파트: BE
- 요청 목적: 검색 결과 화면에서 상품/라이브/회원 결과를 통합 조회할 수 있도록 API 계약을 정리한다.
- 우선순위: P1
- 시연 필수 여부: 검색 화면 시연 시 필수. 홈/상품 상세 중심 시연이면 보류 가능.

## 2. 현재 연동 상태

- 연동 완료 API: 없음
- FE 구현 완료 범위
  - `SearchResultsPage.vue` 화면 구현
  - 검색 탭, 필터, 정렬 UI 구현
  - `searchApi` adapter 구조 구현
- 현재 임시 처리 또는 Mock 사용 여부
  - BE `GET /api/search`가 없어 실제 연결은 보류 상태다.
  - 화면은 mock data 기반으로 렌더링 가능하다.

## 3. 추가 구현 요청

### 3.1 통합 검색

- Method / Endpoint: `GET /api/search`
- 요청 목적: 검색어와 필터 조건으로 상품/라이브/회원 결과를 조회한다.
- FE 사용처: `SearchResultsPage.vue`
- 요청 데이터
  - Query
    - `keyword`: string, 필수
    - `type`: `ALL` | `PRODUCT` | `LIVE` | `USER`, 필수
    - `categories`: number[] 또는 string[], 선택, id 기준 권장
    - `conditions`: string[], 선택
    - `saleTypes`: string[], 선택
    - `minPrice`: number | null
    - `maxPrice`: number | null
    - `sort`: string | null
    - `page`: number, 필수, 0-base
    - `size`: number, 필수
- 응답 데이터
  - `products`: PageResponse<Product> | null
  - `lives`: PageResponse<Live> | null
  - `users`: PageResponse<User> | null
  - Product item: `id`, `title`, `brandName`, `thumbnailUrl`, `price`, `saleType`, `saleStatus`, `isWished`
  - User item: `id`, `nickname`, `profileImageUrl`, `followerCount`, `productCount`, `isFollowing`
- 응답 예시

```json
{
  "success": true,
  "data": {
    "products": {
      "content": [
        {
          "id": 1,
          "title": "빈티지 자켓",
          "brandName": "Levi's",
          "thumbnailUrl": null,
          "price": 59000,
          "saleType": "DIRECT_SALE",
          "saleStatus": "ON_SALE",
          "isWished": false
        }
      ],
      "page": 0,
      "size": 20,
      "totalElements": 1,
      "totalPages": 1,
      "hasNext": false
    },
    "lives": null,
    "users": null
  },
  "error": null
}
```

## 4. 기존 API 변경 요청

- 기존 요청·응답에서 변경할 내용: 없음
- 추가할 필드: 없음
- 변경 영향 범위: 없음

## 5. 보류 또는 시연 제외 범위

- 현재 구현하지 않아도 되는 기능
  - 검색 화면을 시연하지 않으면 통합 검색 API는 보류 가능
  - 회원 공개 프로필 화면이 없으면 회원 결과 클릭 동작은 보류 가능
- 추후 구현 예정 기능
  - 추천 검색어
  - 최근 검색어 서버 저장
  - 검색 결과 하이라이트

## 6. 협의 필요 사항

- FE·BE 간 결정이 필요한 내용
  - `categories` query를 id 배열로 받을지 comma-separated string으로 받을지
  - `type=ALL`일 때 각 섹션 preview 개수
  - 비회원 요청에서 `isWished`, `isFollowing`을 `false`로 줄지 `null`로 줄지
  - 회원 결과 상세 route 정책
- 아직 확정되지 않은 응답 구조나 정책
  - Live result item 필드
  - 검색 정렬 enum
  - 상품 상태/판매 방식 enum 이름

## 7. 추가 요청 없음

- 이미 정상 연동된 API: 없음
- 기존 규격을 유지하면 되는 기능: 없음
