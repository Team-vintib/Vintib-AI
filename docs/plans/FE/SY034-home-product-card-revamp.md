# 홈 화면 상품 카드/배너 개선

## 배경/목표

홈 화면(상품 카드, 배너, 카테고리별 상품 섹션)에 쌓인 UI 불일치·버그를 정리한다. 홈 상품 카드를
상품 목록 카드와 동일한 디자인으로 통일하고, 배너에 새 슬라이드 2개를 추가하고, 카테고리별 상품이
하나도 뜨지 않는 문제를 진단한다.

## 작업 내용

### 1. 홈 상품 카드(`home/components/ProductCard.vue`)를 상품목록 카드 디자인에 맞춘다

- 좌상단 판매방식 뱃지(`badgeLabel`/`badgeVariant`, "경매 예정"/"바로 구매") prop을 제거하고,
  대신 `conditionGrade` prop을 받아 상품목록 카드와 동일한 `{grade}급` 뱃지를 렌더링한다
  (`v-if`로 빈 값이면 숨김 — "미등록"은 별도 텍스트 없이 뱃지 자체를 숨긴다).
- 찜(하트) 버튼을 상품목록 카드와 동일한 원형 스타일(`border-radius: 50%`,
  `backdrop-filter: blur(4px)`, hover 시 `scale(1.05)`)로 맞춘다.
- 가격/경매시작가 텍스트의 `font-family: var(--font-mono)`를 상품목록 카드처럼 `inherit`으로
  바꿔 숫자-한글 혼용 시 폰트가 깨져 보이는 문제를 없앤다.
- `formatPrice`의 `value === undefined` 폴백 문구를 "시작가 미정" → "경매예정"으로 바꾼다
  (BE 계약상 `price`가 없는 경우는 경매 예정 상품뿐이라 이 폴백만 바꾸면 충분하다).
- `MemberHome.vue`/`GuestHome.vue`에서 이 컴포넌트를 쓰는 모든 곳(팔로우한 판매자의 상품,
  판매 상품, 경매 예정 상품, 카테고리별 상품)에서 `badge-label`/`badge-variant` prop 전달을
  제거하고 `condition-grade` prop을 넘긴다.

### 2. 등급(grade) 데이터를 홈에 채운다 — BE 변경 없이 N+1 상세 조회로

- `/home` 응답(`ProductCardResponse`)에는 `conditionGrade` 필드가 없다. BE를 바꾸지 않기로
  했으므로, `HomePage.vue`에서 홈 데이터 로드 후 화면에 노출되는 상품 id를 전부 모아
  (`getHomeProducts`와 동일한 방식) 각각 `getProductDetail(id)`를 병렬 호출해
  `Map<productId, conditionGrade>`를 만든다.
- 실패한 개별 호출은 무시(해당 상품은 등급 뱃지 없이 표시)하고 전체 로딩을 막지 않는다.
- 이 맵을 `MemberHome`/`GuestHome`에 prop으로 내려 각 `ProductCard`의 `condition-grade`를
  채운다.
- 홈 상품 카드 개수(최대 20+20+8×7 등)만큼 상세 API가 호출되므로 홈 로딩이 느려질 수 있다는
  점은 감수한다(사용자 확인 완료).

### 3. 배너(`HomeHeroCarousel.vue`)

- CTA 버튼(`.home-hero-slide__cta`)의 세로 위치를 슬라이드 텍스트 길이와 무관하게 배너 높이
  기준 고정 위치(중앙)에 오도록 레이아웃을 바꾼다(현재는 텍스트 블록 흐름에 따라 붙어 있어
  슬라이드마다 버튼 위치가 들쭉날쭉하다).
- 슬라이드 맨 앞에 새 슬라이드를 추가한다 — **팔로워 많은 판매자의 예약 라이브**:
  - `HomePage.vue`에서 `homeData.scheduledLives`(이미 BE가 `hostId`를 내려주므로 FE 타입
    `HomeLiveCardItem`/응답 매핑에 `hostId` 추가)의 호스트들 중 중복을 제거하고, 각 호스트에
    대해 기존 `getPublicProfile(hostId)`(`GET /users/{id}/profile`)를 호출해
    `followerCount`를 얻는다.
  - 팔로워 수가 가장 많은 호스트의 예약 라이브를 골라 `{ live, hostFollowerCount }` 형태로
    `HomeHeroCarousel`에 prop으로 내린다. 대상이 없으면(예약 라이브 없음) 이 슬라이드는 만들지
    않는다.
  - CTA 라벨은 "알림 설정"이며, 클릭 시 기존 `registerLiveReminder(liveId)`
    (`POST /lives/{liveId}/reminders`)를 호출한다. 별도의 최초 구독 여부 조회는 하지 않고
    (해당 API가 토글이 아니라 등록/취소가 분리돼 있고, 홈에는 구독 상태 조회 API가 없음),
    클릭 후 로컬 상태로 "알림 설정 완료"를 보여주는 정도로 간단히 처리한다.
  - BE 변경 불필요 — 기존 `/home`, `/users/{id}/profile`, `/lives/{liveId}/reminders` 조합.
- 배너 2번째로 **찜 많은 상품** 슬라이드를 추가하는 건(원 요청 8번) 이번 범위에서 제외한다
  — wishCount를 내려주는 BE API/필드가 전혀 없어 기존 API 조합으로 만들 수 없다(사용자 확인
  완료, 필요 시 추후 별도로 BE 요청 문서를 작성한다).

### 4. 카테고리별 상품 섹션 — BE 버그, FE에서 수정 불가

- 원인 파악 완료: `BE/.../home/service/HomeService.java`의 `categoryProductSections()`가
  카테고리 트리를 한 단계만 내려가며 상품 조회 대상 카테고리 id를 모은다(성별 루트 → 그
  직계 자식인 중분류까지만 포함, 실제 상품이 걸리는 소분류 id는 누락). 그 결과 상품 조회
  쿼리 대상 카테고리 id 목록에 소분류가 전혀 없어 상품이 항상 0건으로 나온다. 또한 "루트"를
  `parentId == null`(성별: 남성/여성/공용)로 잡고 있어, DTO 주석이 말하는 의도
  (아우터·상의·하의·신발·가방·액세서리 6탭)와도 어긋난다.
- FE 코드는 다른 파트를 직접 수정하지 않으므로, 이 원인과 함께 `docs/requests/BE/028-...md`로
  버그 리포트를 남긴다. FE의 `homeViewApi.ts` 매핑 로직(소분류→중분류 하드코딩 매핑 등)은
  BE가 의도대로(중분류 6탭 + 소분류까지 포함한 상품 조회) 고치면 그대로 맞아떨어지므로 지금은
  손대지 않는다.

### 5. "경매 예정 상품" 전체보기 → 상품 목록의 경매 탭으로 연결

- `MemberHome.vue`/`GuestHome.vue`의 "경매 예정 상품" `HomeSection`의 `link-to`를
  `ROUTE_PATHS.PRODUCT_LIST` 단순 경로 대신 `{ path: ROUTE_PATHS.PRODUCT_LIST, query: { saleType: 'AUCTION' } }`
  형태로 바꾼다.
- `ProductListView.vue`가 마운트 시 `route.query.saleType` 값이 `PRODUCT_SALE_TYPE_TABS`의
  id(`ALL`/`DIRECT`/`AUCTION`)와 일치하면 `selectedSaleType` 초기값으로 반영하도록
  `useRoute()`를 도입한다(현재는 항상 `'ALL'`로 시작).

## 구현 목록

- [x] `home/components/ProductCard.vue`: 판매방식 뱃지 제거 → `conditionGrade` 뱃지로 교체,
      찜 버튼 스타일을 상품목록 카드와 통일, 가격 폰트 `inherit`으로 변경,
      "시작가 미정" → "경매예정" 문구 변경
- [x] `MemberHome.vue`/`GuestHome.vue`: `ProductCard` 호출부에서 배지 prop 제거, 등급 맵
      기반 `condition-grade` prop 연결, 경매 예정 섹션 `link-to`에 `saleType=AUCTION` 쿼리
      추가
- [x] `HomePage.vue`: 홈 상품 id 수집 → `getProductDetail` 병렬 호출로 등급 맵 생성 후 하위
      컴포넌트에 전달
- [x] `home/types/homeView.types.ts`, `home/api/homeViewApi.ts`: `HomeLiveCardItem`/응답
      매핑에 `hostId` 추가
- [x] `HomePage.vue`: 예약 라이브 호스트별 `getPublicProfile` 병렬 호출로 팔로워 최다 호스트
      선정, `HomeHeroCarousel`에 인기 호스트 슬라이드 데이터 전달
- [x] `HomeHeroCarousel.vue`: CTA 버튼 세로 위치 고정 레이아웃 수정, 인기 호스트 슬라이드
      추가(알림 설정 버튼은 `registerLiveReminder` 호출)
- [x] `product/pages/ProductListView.vue`: 마운트 시 `route.query.saleType`으로 초기 탭 반영
- [x] `docs/requests/BE/028-home-category-products-empty.md` 작성(카테고리별 상품 0건 버그)
- [x] `npm run type-check`, `npm run lint` 통과 확인. 브라우저 확장 미연결로 실제 화면 확인은
      못함 — `npm run dev`로 로컬 확인 필요

## 확인이 필요한 미결정 사항

- 없음 — 위 방향은 모두 사용자 확인을 거쳤다(등급은 N+1 상세 호출, 찜 많은 상품 배너는 이번
  범위 제외, CTA 버튼은 배너 높이 기준 세로 중앙 고정).

## 후속 수정 (2026-08-05)

1차 구현 후 실제 화면에서 발견된 문제를 추가로 고쳤다.

- 배너 CTA 버튼(세로 고정 위치)이 2줄 설명이 있는 슬라이드의 텍스트와 겹치는 문제: 텍스트
  블록을 슬라이드 상단 62% 영역으로 제한(`max-height: 62%; overflow: hidden`)하고 버튼을 그
  아래 72% 고정 위치로 옮겼다.
- 캐러셀 이전/다음 화살표가 세로 중앙에 안 맞아 보이던 문제: 텍스트 글리프(‹›) 대신 SVG
  셰브런 아이콘으로 교체했다(폰트 자체의 상하 비대칭 여백이 원인이었음).
- 카테고리별 상품 섹션: BE `categoryProductSections`가 버그로 항상 빈 배열이라(028 참고) FE에서
  독립적으로 채우도록 바꿨다. 상품 목록 페이지와 똑같은 방식 — `GET /categories`로 카테고리
  트리를 받아 소분류(depth 3)를 대분류(depth 2) 이름으로 묶고(`buildProductCategoryOptions`,
  `product/api/productApi.ts`로 추출해 두 화면이 공유), 각 탭마다
  `GET /api/products?categoryIds=...&size=8&sort=LATEST`를 호출해 채운다. 카드도 홈 전용
  `ProductCard`가 아니라 상품 목록 카드(`product/components/ProductCard.vue`)를 그대로 재사용해
  등급 뱃지가 별도 조회 없이 바로 나온다. `CategoryProductTabs.vue`가
  `HomeProductCardItem[]` 대신 `ProductListItem[]`(`ProductCategoryTabSection`)을 받도록
  바뀌었다.
