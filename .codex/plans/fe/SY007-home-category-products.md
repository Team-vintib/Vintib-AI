# HOME 카테고리별 상품 섹션 계획

## 배경/목표

프로토타입에는 홈 화면에 `<테마별 상품>` 섹션이 있지만 현재 FE 홈에는 해당 섹션이 없다. GuestHome과 MemberHome 모두에서 공통으로 노출되는 `카테고리별 상품` 탭 섹션을 추가한다.

## 작업 내용

- 회원/비회원 홈 모두에서 같은 카테고리별 상품 탭 섹션을 노출한다.
- 기존 `HomeSection`과 `ProductCard` 스타일을 재사용해 홈 화면 톤을 유지한다.
- 현재 BE 홈 상품 응답에는 `categoryName`과 카테고리별 묶음 응답이 없으므로, 이번 FE 작업에서는 홈 mock 보조 데이터 기반으로 섹션을 구성한다.
- 추후 BE가 `categoryName` 또는 `categoryProductSections`를 제공하면 `homeViewApi.ts` adapter만 실제 응답 매핑으로 교체한다.
- BE 요청 문서에는 이미 홈 상품 카드에 `categoryName`이 필요하다는 내용을 남겼다: `.codex/requests/be/009-home-card-response-fields.md`

## 구현 목록

- [x] `homeView.types.ts`에 카테고리별 상품 섹션 타입을 추가한다.
  - 예: `HomeCategoryProductSection`
  - 필드 후보: `id`, `title`, `description?`, `categoryName`, `products`
- [x] `HomeViewData`에 `categoryProductSections`를 추가한다.
- [x] `homeMockData.ts`에 카테고리별 상품 mock 섹션을 추가한다.
- [x] `homeViewApi.ts`에서 BE 응답에 없는 동안 `homeMockData.categoryProductSections`를 유지하도록 매핑한다.
- [x] 카테고리별 상품 전용 컴포넌트를 추가하거나, GuestHome/MemberHome 내부에서 공통 렌더링을 구성한다.
- [x] GuestHome에 `카테고리별 상품` 섹션을 추가한다.
- [x] MemberHome에도 같은 `카테고리별 상품` 섹션을 추가한다.
- [x] 상품 클릭은 기존과 동일하게 `/products/{id}`로 이동한다.
- [x] 반응형 grid는 기존 홈 상품 grid와 동일한 3열/2열/모바일 규칙을 우선 재사용한다.
- [x] `npm run type-check`, `npm run lint`, 가능하면 `npm run build`로 검증한다.

## 배치 후보

### GuestHome

현재 흐름:

1. 검색
2. Hero
3. 지금 진행 중인 라이브
4. 예약 라이브
5. 판매 상품
6. 경매 예정 상품
7. 콘텐츠 카드

추가 후보:

- `판매 상품` 뒤, `경매 예정 상품` 앞에 `카테고리별 상품` 배치
- 이유: 일반 상품 탐색 흐름에서 자연스럽고, 경매 예정 상품과 역할이 구분된다.

### MemberHome

현재 흐름:

1. 검색
2. Hero
3. 내가 팔로우한 판매자
4. 지금 진행 중인 라이브
5. 예약 라이브
6. 내 취향의 빈티지 상품
7. 경매 예정 상품
8. 콘텐츠 카드

추가 후보:

- `내 취향의 빈티지 상품` 뒤, `경매 예정 상품` 앞에 `카테고리별 상품` 배치
- 이유: 개인화 추천 후 일반 탐색 섹션으로 이어지고, 경매 예정과 구분된다.

## 확인이 필요한 미결정 사항

- 섹션명은 사용자 확인에 따라 `카테고리별 상품`으로 사용한다.
- UI는 사용자 확인에 따라 카테고리 탭 형태로 구현한다.
- 현재 BE 응답에는 카테고리별 묶음이 없으므로, 실제 데이터 전환 시 BE 계약이 필요하다.
