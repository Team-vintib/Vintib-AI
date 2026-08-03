# SY021 - 찜 목록 고도화

## 배경/목표

`MY-006/MY-009`의 찜 기능을 실제 wish API 기준으로 정리하고, 상품 목록과 같은 탐색 경험을 제공한다. 상품 카드의 찜 버튼은 로그인 사용자의 찜 상태를 정확히 표시하고, 찜 목록에서는 검색/필터와 `전체 / 즉시 구매 / 경매 예정` 탭으로 관심 상품을 나눠 볼 수 있게 만든다.

## 현재 상태 분석

- `ProductListView.vue`는 `POST /api/users/{userId}/wishes`, `DELETE /api/users/{userId}/wishes/{productId}`를 사용해 찜 토글을 낙관적으로 반영한다.
- `ProductCard.vue`는 `isLiked` prop으로 하트 활성 상태를 표시한다.
- `MyPage.vue`의 `wishlist` 섹션은 `GET /api/users/{userId}/wishes`로 찜 목록을 읽고 찜 해제를 제공하지만, 상품 목록 수준의 검색/필터/판매 방식 탭은 없다.
- 현재 BE 찜 목록 API는 `page`, `size`만 받고, 정렬은 찜한 시각 최신순 고정이다. 검색/필터 파라미터가 없으므로 FE 1차 구현은 받아온 찜 목록을 클라이언트에서 필터링한다.

## 작업 내용

1. 찜 API 호출과 응답 매핑을 `domains/product/api/productApi.ts` 또는 `domains/my/api/myApi.ts`에서 재사용 가능한 형태로 정리한다.
2. 상품 목록과 찜 목록이 같은 카드 표시 규칙을 쓰도록 `ProductListItem`에 필요한 상태 필드를 보강한다.
   - `saleStatus`를 보존해 판매 완료/비공개/경매 진행 중 상태 배지를 표시할 수 있게 한다.
   - 경매 예정 상품은 가격 대신 `경매 예정` 문구를 유지한다.
3. 상품 목록의 찜 버튼 활성화가 BE의 `isWished`/`isLiked` 필드를 안정적으로 반영하도록 매핑과 토글 실패 복구를 점검한다.
4. `/wishlist` 독립 페이지에 찜 목록 전용 검색바와 필터 패널을 추가한다.
   - 검색 대상: 상품명, 브랜드명.
   - 필터: 카테고리, 상품 상태 등급, 가격 범위.
   - 판매 방식 탭: `전체`, `즉시 구매`, `경매 예정`.
5. 찜 해제 시 현재 목록/카운트/빈 상태가 즉시 갱신되도록 처리한다.
6. 로딩, 오류, 빈 목록, 로그인 만료 상태를 기존 마이페이지 톤에 맞춰 정리한다.
7. 관련 FE 문서의 구현 상태와 구조 문서를 갱신한다.

## 구현 목록

- [x] `ProductListItem` 또는 찜 전용 view model에 `saleStatus`, `categoryId/categoryName`, `wishedAt` 등 필터/상태 표시용 필드를 추가한다.
- [x] BE 상품/찜 DTO를 FE 카드 모델로 바꾸는 매핑 함수를 중복 없이 정리한다.
- [x] 상품 목록 찜 버튼 활성 상태와 토글 실패 복구를 확인하고 필요한 경우 에러 메시지를 보강한다.
- [x] 마이페이지 찜 섹션에 상품 목록과 같은 검색 입력, 카테고리/상태/가격 필터, 초기화/적용 동작을 추가한다.
- [x] 찜 목록에 `전체 / 즉시 구매 / 경매 예정` 탭을 추가하고 `saleType` 기준으로 목록을 나눠 보여준다.
- [x] 찜 목록 카드에서 상품 상세 이동, 찜 해제, 판매 상태 배지를 제공한다.
- [x] 찜 목록의 로딩/오류/빈 목록/검색 결과 없음 상태를 분리한다.
- [x] 마이페이지 내부 `wishlist` 섹션을 제거하고 헤더 찜 링크를 `/wishlist`로 연결한다.
- [x] 찜 목록 상품 이미지가 비어 있을 때 로컬 상품 이미지 fallback을 표시한다.
- [x] `FE/docs/frontend/implementation/status.md`, `FE/docs/frontend/implementation/current-structure.md`를 갱신한다.
- [x] `npm run type-check`와 `npm run build`로 검증한다.

## 확인이 필요한 사항

- BE 찜 목록 API가 검색/필터를 직접 지원하지 않으므로, 1차 구현은 클라이언트 필터링으로 진행한다. 찜 수가 많아져 서버 필터/페이지네이션이 필요해지면 `GET /api/users/{userId}/wishes`에 `keyword`, `categoryIds`, `conditionGrades`, `minPrice`, `maxPrice`, `saleType` 지원을 BE에 요청해야 한다.
- 기능 정의서에는 찜 목록과 팔로우 목록이 같은 화면 묶음으로 표현되어 있지만, 이번 작업은 사용자 요청에 맞춰 찜 상품 목록만 고도화한다.
