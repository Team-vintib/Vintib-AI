# HOME-001 FE 홈 화면 구현 계획

작성일: 2026-07-27

## 범위

- 수정 범위는 `FE/` 내부로 제한한다.
- 기본 진입 주소 `/`는 비로그인 사용자도 접근 가능한 공개 홈으로 둔다.
- `/`에 처음 들어온 비로그인 사용자는 비로그인 기준 홈 화면을 본다.
- 로그인 세션이 있는 사용자가 `/`에 들어오면 로그인 사용자 기준 홈 화면을 본다.
- API 계약 확정 전까지는 홈 도메인 mock 데이터와 view model 타입을 사용한다.
- 새로운 외부 라이브러리는 추가하지 않는다.

## 관련 Jira

- `S15P11A108-275`: 글로벌 내비게이션바 UI 및 반응형 구현
- `S15P11A108-277`: 메뉴 라우팅, 활성 상태 및 로그인별 노출 처리
- `S15P11A108-283`: 홈 페이지 기본 레이아웃 구현
- `S15P11A108-287`: 홈 화면 Mock 데이터 렌더링 및 반응형 구현
- `S15P11A108-284`: 진행 중, 예약 라이브 카드 및 목록 UI 구현
- `S15P11A108-285`: 상시 판매, 경매 예정 상품 카드 및 목록 UI 구현
- `S15P11A108-286`: 홈 콘텐츠 UI 구현
- `S15P11A108-396`: 로그인 홈 섹션 레이아웃 구현
- `S15P11A108-398`: 비로그인 홈 진입 화면 구현

## 기본 정책

### 진입 URL

```text
/ -> HomePage
```

- `ROUTE_PATHS.HOME`의 값인 `/`를 홈 페이지로 등록한다.
- 홈 라우트에는 `requiresAuth`를 붙이지 않는다.
- 로그인 필요 메뉴나 액션은 해당 액션 시점에 `/auth/login?redirect=<target>`으로 이동시킨다.

### 사용자 상태

홈 화면은 `useAuthStore()`의 상태를 기준으로 분기한다.

- `isAuthenticated === false`
  - `GuestHome`을 렌더링한다.
  - 서비스 진입, 대표 콘텐츠 미리보기, 로그인/회원가입 CTA를 제공한다.
- `isAuthenticated === true`
  - `MemberHome`을 렌더링한다.
  - 라이브, 예약 라이브, 상품, 경매 예정, 홈 콘텐츠 섹션을 제공한다.
- `user?.onboardingCompleted === false`
  - 현재 router guard 정책과 충돌하지 않도록 확인한다.
  - 홈에서 별도 분기할지, 온보딩 라우트로 보내는 기존 정책을 유지할지 구현 전 다시 확인한다.

## 예상 파일 구조

```text
src/domains/home/
  pages/
    HomePage.vue
  components/
    GuestHome.vue
    MemberHome.vue
    HomeSection.vue
    LiveCard.vue
    LiveListSection.vue
    ProductCard.vue
    ProductListSection.vue
    AuctionListSection.vue
  constants/
    homeMockData.ts
  types/
    home.types.ts

src/shared/components/
  GlobalNavigation.vue

src/shared/layouts/
  DefaultLayout.vue
```

## 구현 단계

### 1. 홈 라우트와 페이지 shell 추가

목표:

- `/`에서 홈 페이지가 렌더링되도록 최소 라우팅과 페이지 shell을 만든다.

구현:

- `src/router/routes.ts`
  - `ROUTE_PATHS.HOME`, `ROUTE_NAMES.HOME` 라우트를 추가한다.
  - `meta.requiresAuth`는 설정하지 않는다.
- `src/domains/home/pages/HomePage.vue`
  - `authStore.hydrateSession()` 필요 여부를 확인한다.
  - `authStore.isAuthenticated` 기준으로 `GuestHome` 또는 `MemberHome`을 렌더링한다.
- `src/domains/home/components/GuestHome.vue`
  - 비로그인 홈 placeholder를 만든다.
- `src/domains/home/components/MemberHome.vue`
  - 로그인 홈 placeholder를 만든다.

관련 Jira:

- `S15P11A108-283`
- `S15P11A108-396`
- `S15P11A108-398`


### 2. 글로벌 내비게이션 기본 UI 추가

목표:

- 홈 포함 기본 화면에서 공통으로 사용할 내비게이션을 만든다.

구현:

- `src/shared/components/GlobalNavigation.vue`
  - 로고, 주요 메뉴, 검색 진입, 로그인/회원가입 또는 사용자 메뉴 영역을 구성한다.
  - desktop first 기준으로 구현한 뒤 mobile breakpoint를 추가한다.
- `src/shared/layouts/DefaultLayout.vue`
  - 상단에 `GlobalNavigation`을 포함한다.
  - 본문 영역이 nav와 겹치지 않도록 spacing을 정리한다.

관련 Jira:

- `S15P11A108-275`


### 3. 메뉴 라우팅, active 상태, 로그인별 노출 처리

목표:

- 내비게이션이 현재 route와 인증 상태를 반영하도록 만든다.

구현:

- route 상수 기반 메뉴 목록을 정의한다.
- `useRoute()` 기준으로 active 상태를 계산한다.
- 비로그인 사용자에게는 홈, 검색/둘러보기, 로그인, 회원가입 중심 메뉴를 노출한다.
- 로그인 사용자에게는 홈, 팔로잉, 알림, 마이, 포인트 등 로그인 메뉴를 노출한다.
- 로그인 필요 메뉴 클릭 시 로그인 페이지로 이동하고 `redirect` query를 유지한다.
- 아직 페이지가 없는 route는 라우트 등록 여부를 확인한 뒤 placeholder 또는 비활성 상태로 처리한다.

관련 Jira:

- `S15P11A108-277`


### 4. 홈 view model 타입과 mock 데이터 추가

목표:

- API 확정 전에도 홈 UI를 안정적으로 구현할 수 있는 데이터 계약을 만든다.

구현:

- `src/domains/home/types/home.types.ts`
  - `HomeLiveItem`
  - `HomeProductItem`
  - `HomeAuctionItem`
  - `HomeContentItem`
  - `HomeSectionLink`
- `src/domains/home/constants/homeMockData.ts`
  - 진행 중 라이브 mock
  - 예약 라이브 mock
  - 상시 판매 상품 mock
  - 경매 예정 상품 mock
  - 홈 콘텐츠 mock
- 섹션 컴포넌트는 mock 데이터를 직접 import하지 않고 props로 받도록 설계한다.

관련 Jira:

- `S15P11A108-287`


### 5. 홈 공통 섹션 컴포넌트 구현

목표:

- 여러 홈 섹션이 공유하는 제목, 설명, 전체보기 링크, empty 상태 구조를 만든다.

구현:

- `src/domains/home/components/HomeSection.vue`
  - `title`, `description`, `linkLabel`, `linkTo` props를 제공한다.
  - 콘텐츠 영역은 slot으로 받는다.
  - empty 상태가 필요한 경우 slot 또는 props로 확장한다.
- spacing과 heading 크기는 `assets/main.scss`의 design token을 우선 사용한다.

관련 Jira:

- `S15P11A108-283`
- `S15P11A108-286`
- `S15P11A108-287`


### 6. 라이브 카드와 라이브 섹션 구현

목표:

- 진행 중 라이브와 예약 라이브 목록을 mock 데이터로 렌더링한다.

구현:

- `src/domains/home/components/LiveCard.vue`
  - 썸네일, 상태 badge, 제목, 판매자, 시청자/예약자 수, 시작 시간을 표시한다.
  - `LIVE`, `예약`, `곧 시작` 상태 표현을 지원한다.
- `src/domains/home/components/LiveListSection.vue`
  - `HomeSection`을 사용해 진행 중/예약 라이브 목록을 렌더링한다.
  - desktop grid와 mobile list 또는 horizontal scroll을 적용한다.

관련 Jira:

- `S15P11A108-284`
- `S15P11A108-287`



### 7. 상품 카드와 경매 예정 섹션 구현

목표:

- 상시 판매 상품과 경매 예정 상품을 mock 데이터로 렌더링한다.

구현:

- `src/domains/home/components/ProductCard.vue`
  - 상품 이미지, 상품명, 브랜드/카테고리, 가격, 상태 badge, 찜 버튼 자리를 표시한다.
- `src/domains/home/components/ProductListSection.vue`
  - 상시 판매 상품 목록을 렌더링한다.
- `src/domains/home/components/AuctionListSection.vue`
  - 경매 예정 상품 목록을 렌더링한다.
  - 시작가, 시작 예정 시간, 남은 시간 표현을 지원한다.
- 일반 상품과 경매 상품의 데이터 구조가 너무 다르면 카드 variant 대신 별도 카드 분리를 고려한다.

관련 Jira:

- `S15P11A108-285`
- `S15P11A108-287`


### 8. 비로그인 홈 진입 화면 구현

목표:

- 처음 Vintib에 들어온 비로그인 사용자가 보는 홈 화면을 완성한다.

구현:

- `src/domains/home/components/GuestHome.vue`
  - 서비스 핵심 진입 영역을 만든다.
  - 로그인/회원가입 CTA를 연결한다.
  - 대표 라이브, 대표 상품, 경매 예정 preview를 노출한다.
  - 비로그인 제한 액션은 로그인 페이지로 유도한다.
- 비로그인 화면도 실제 탐색이 가능하도록 콘텐츠 preview를 제공한다.

관련 Jira:

- `S15P11A108-398`
- `S15P11A108-286`


### 9. 로그인 홈 섹션 레이아웃 구현

목표:

- 로그인 사용자가 홈에서 주요 탐색과 행동을 이어갈 수 있도록 섹션을 조립한다.

구현:

- `src/domains/home/components/MemberHome.vue`
  - 진행 중 라이브
  - 예약 라이브
  - 추천 또는 상시 판매 상품
  - 경매 예정 상품
  - 홈 콘텐츠 섹션
- 사용자 이름 또는 관심사 정보가 있으면 개인화 문구에 반영한다.
- mock 데이터가 비어 있을 때의 empty 상태를 확인한다.

관련 Jira:

- `S15P11A108-396`
- `S15P11A108-284`
- `S15P11A108-285`
- `S15P11A108-286`


### 10. 홈 콘텐츠 UI 구현

목표:

- 라이브와 상품 외의 홈 콘텐츠 영역을 완성한다.

구현:

- 카테고리 shortcut, 추천 셀러, 기획전, AI 착용 또는 라이브 경매 진입 영역 등 프로토타입에 맞는 콘텐츠를 구현한다.
- 클릭 대상 route가 아직 없으면 비활성 상태 또는 TODO 주석으로 명확히 남긴다.
- 홈 전체 섹션 순서와 정보 밀도를 조정한다.

관련 Jira:

- `S15P11A108-286`


### 11. 반응형, 상태별 QA, 문서 갱신

목표:

- 홈 화면이 사용자 상태와 viewport별로 깨지지 않는지 검증한다.

검증:

- 비로그인 `/` 진입
- 로그인 `/` 진입
- 온보딩 미완료 사용자 처리
- 긴 상품명, 긴 라이브명
- mock 데이터 empty 상태
- desktop, tablet, mobile layout
- nav active 상태
- 로그인 필요 메뉴 redirect

명령:

```text
npm run type-check
npm run build
```

문서:

- 구조가 변경되면 `docs/frontend/implementation/current-structure.md`를 갱신한다.
- 구현 상태가 변경되면 `docs/frontend/implementation/status.md`를 갱신한다.
- route가 변경되면 `docs/frontend/flows/route-map.md`를 갱신한다.

관련 Jira:

- `S15P11A108-275`
- `S15P11A108-287`
- 전체 HOME 관련 티켓


## 미확정 사항

- 프로토타입의 정확한 home section 순서와 copy
- 비로그인 사용자에게 어떤 콘텐츠까지 preview로 노출할지
- 온보딩 미완료 사용자를 `/`에서 바로 온보딩으로 보낼지 여부
- 판매자/사업자 권한 메뉴의 정확한 노출 조건
- 홈 콘텐츠 클릭 시 연결될 상세 route의 구현 여부
- 실제 홈 API 계약과 응답 필드

## 구현 원칙

- `/`는 공개 홈으로 유지한다.
- `HomePage.vue`는 상태 분기와 데이터 주입 중심으로 유지한다.
- `GuestHome.vue`와 `MemberHome.vue`는 화면 조립 책임을 가진다.
- 섹션 컴포넌트는 props 기반으로 작성해 mock 데이터에 직접 묶이지 않게 한다.
- 공통화는 실제 중복이 확인된 컴포넌트에만 적용한다.
- 색상, spacing, radius는 `assets/main.scss`의 design token을 우선 사용한다.
- 구현 완료 후 `npm run type-check`, `npm run build`를 수행한다.
