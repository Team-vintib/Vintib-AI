# 현재 프로젝트 구조

확인일: 2026-07-30

## 기술 스택

- Vue 3
- TypeScript
- Vite
- Vue Router
- Pinia
- Axios
- Tailwind CSS
- SCSS

## 주요 명령

| 명령                 | 설명                 |
| -------------------- | -------------------- |
| `npm run dev`        | Vite 개발 서버 실행  |
| `npm run build`      | 타입 체크 후 빌드    |
| `npm run preview`    | Vite preview         |
| `npm run type-check` | `vue-tsc --build`    |
| `npm run lint`       | ESLint fix           |
| `npm run format`     | `src/` Prettier 적용 |

## 현재 폴더

```text
src/
  App.vue
  main.ts
  app/
    providers/
      pinia/
      router/
  assets/
    images/
      logo.png
      products/
        product-denim-jacket.webp
        product-knit.webp
        product-leather-bag.webp
        product-sneakers.webp
        product-trench-coat.webp
        product-watch.webp
    main.scss
    tailwind.css
  domains/
    auth/
      api/
        authApi.ts
      components/
        EmailVerificationField.vue
        LoginForm.vue
        SignupForm.vue
        SsafySsoStartCard.vue
      constants/
      pages/
        AuthLinkAccountPage.vue
        LoginPage.vue
        SignupEntryPage.vue
        SignupPage.vue
        SsafyLoginPage.vue
        SsafySignupPage.vue
        SsafySsoCallbackPage.vue
        SsafySsoPage.vue
      stores/
        authStore.ts
      types/
        auth.types.ts
    onboard/
      api/
        onboarding.ts
        postcode.ts
      components/
        BaseButton.vue
        BaseField.vue
        BaseInput.vue
        FullBodyPhotoUploader.vue
        OnboardingLayout.vue
        OnboardingStepIndicator.vue
      constants/
      pages/
        OnboardingBasicInfoView.vue
        OnboardingInterestsView.vue
        OnboardingMemberTypeView.vue
        OnboardingTryOnView.vue
      types/
        kakao-postcode.d.ts
    biz/
      api/
      components/
        BusinessCertificateUploader.vue
      constants/
        businessVerification.ts
      pages/
        BusinessVerificationPage.vue
        BusinessVerificationPendingPage.vue
      stores/
        businessVerificationStore.ts
      types/
    home/
      api/
        homeViewApi.ts
      components/
        GuestHome.vue
        HomeContentCard.vue
        HomeHero.vue
        HomeSearchPanel.vue
        HomeSection.vue
        LiveCard.vue
        MemberHome.vue
        ProductCard.vue
      constants/
        homeMockData.ts
      pages/
        HomePage.vue
      types/
        homeView.types.ts
    search/
      api/
      components/
        SearchLiveResultCard.vue
        SearchMemberResultCard.vue
        SearchResultTabs.vue
        SearchStatePanel.vue
      constants/
        searchFilterOptions.ts
        searchMockData.ts
      pages/
        SearchResultsPage.vue
      types/
        search.types.ts
    recommendation/
      api/
      components/
      constants/
      pages/
      types/
    follow/
      api/
      components/
      constants/
      pages/
      types/
    notification/
      api/
      components/
      constants/
      pages/
      types/
    product/
      api/
        productDetailApi.ts
      components/
        AiQualityAnalysisPanel.vue
        ProductCard.vue
        ProductDetailInformation.vue
        ProductDetailSkeleton.vue
        ProductDetailStatePanel.vue
        ProductFilterPanel.vue
        ProductImageGallery.vue
        ProductPurchaseSummary.vue
        ProductSellerLivePanel.vue
      constants/
        productDetailMockData.ts
        productListMockData.ts
      pages/
        ProductDetailView.vue
        ProductListView.vue
      types/
        productDetail.types.ts
        productList.types.ts
    live/
      api/
        liveListApi.ts
        liveWatchApi.ts
      components/
        LiveListCard.vue
        LiveListFilter.vue
        LiveListState.vue
        LiveProductQueue.vue
        LiveSelectedProduct.vue
        LiveVideoStage.vue
        LiveWatchHeader.vue
        LiveWatchSidePanel.vue
        LiveWatchState.vue
      constants/
        liveCreateMockData.ts
        liveListFilterOptions.ts
        liveListMockData.ts
        liveWatchMockData.ts
      pages/
        LiveCreatePage.vue
        LiveListView.vue
        LiveWatchPage.vue
      types/
        liveCreate.types.ts
        liveList.types.ts
        liveWatch.types.ts
    chat/
      api/
      components/
      constants/
      pages/
      types/
    auction/
      api/
      components/
      constants/
      pages/
      types/
    tryon/
      api/
      components/
        LiveTryOnPanel.vue
      constants/
        liveTryOnMockData.ts
      pages/
      types/
        liveTryOn.types.ts
    point/
      api/
      components/
      constants/
      pages/
      types/
    sale/
      api/
      components/
      constants/
      pages/
      types/
    shipping/
      api/
      components/
      constants/
      pages/
      types/
    order/
      api/
      components/
      constants/
      pages/
      types/
    refund/
      api/
      components/
      constants/
      pages/
      types/
    my/
      api/
      components/
      constants/
      pages/
      types/
  router/
    index.ts
    route-meta.d.ts
    routes.ts
  shared/
    api/
      authTokenStorage.ts
      http.ts
    components/
      GlobalNavigation.vue
      RoutePlaceholder.vue
    composables/
    constants/
      routes.ts
    layouts/
      AuthLayout.vue
      DefaultLayout.vue
      LiveLayout.vue
    types/
      api.types.ts
    utils/
      validators.ts

docs/
  notion/
```

빈 폴더는 구조 보존을 위해 `.gitkeep`을 둡니다.

## 기능 ID prefix와 도메인 폴더 매핑

| Prefix    | 도메인 폴더              | 기준 기능                                             |
| --------- | ------------------------ | ----------------------------------------------------- |
| `AUTH`    | `domains/auth`           | 회원가입, 로그인, SSO, 계정 연결                      |
| `ONBOARD` | `domains/onboard`        | 가입 후 기본 정보, 관심 정보, AI 시착 정보, 회원 유형 |
| `BIZ`     | `domains/biz`            | 사업자 인증, 세금계산서                               |
| `HOME`    | `domains/home`           | 홈, 팔로잉 홈                                         |
| `SEARCH`  | `domains/search`         | 통합 검색, 필터                                       |
| `REC`     | `domains/recommendation` | 개인화 추천                                           |
| `FOLLOW`  | `domains/follow`         | 팔로우, 팔로우 해제                                   |
| `NOTI`    | `domains/notification`   | 알림 센터, 라이브/경매/거래/배송 알림                 |
| `PROD`    | `domains/product`        | 상품 등록, 상세, 목록, 관리                           |
| `LIVE`    | `domains/live`           | 라이브 예약, 즉시 방송, 시청, 다시보기                |
| `CHAT`    | `domains/chat`           | 라이브 채팅, AI 답변                                  |
| `AUCT`    | `domains/auction`        | 경매 설정, 입찰, 낙찰                                 |
| `TRYON`   | `domains/tryon`          | AI 가상 시착                                          |
| `POINT`   | `domains/point`          | 포인트 충전, 내역, 출금, 정산                         |
| `SALE`    | `domains/sale`           | 상시 판매 구매                                        |
| `SHIP`    | `domains/shipping`       | 송장 등록, 배송 조회                                  |
| `ORDER`   | `domains/order`          | 배송지, 구매 확정                                     |
| `REFUND`  | `domains/refund`         | 환불 신청, 환불 처리                                  |
| `MY`      | `domains/my`             | 마이페이지, 회원 정보, 내역 관리                      |

## 도메인 내부 폴더 기준

| 폴더          | 용도                                     |
| ------------- | ---------------------------------------- |
| `pages/`      | 라우터에 직접 연결되는 화면 컴포넌트     |
| `components/` | 해당 도메인에서만 사용하는 화면 조각     |
| `api/`        | 해당 도메인의 API 호출 함수              |
| `types/`      | 해당 도메인의 요청, 응답, 화면 상태 타입 |
| `constants/`  | 해당 도메인 전용 상수, 옵션, 메시지      |

## 공통 폴더 기준

| 폴더                  | 용도                                                                                              |
| --------------------- | ------------------------------------------------------------------------------------------------- |
| `app/`                | 앱 조립 계층. 라우터/Pinia provider 등 전역 설정 후보                                             |
| `shared/api/`         | Axios 인스턴스, 공통 API 유틸. 현재 `http.ts` 제공                                                |
| `shared/components/`  | 2개 이상 도메인에서 재사용되는 UI 컴포넌트                                                        |
| `shared/composables/` | 2개 이상 도메인에서 재사용되는 Composition API 함수                                               |
| `shared/constants/`   | 라우트명, 전역 옵션 등 공통 상수. 현재 `routes.ts` 제공                                           |
| `shared/layouts/`     | 인증, 기본 서비스, 라이브 등 공통 레이아웃. 현재 `AuthLayout`, `DefaultLayout`, `LiveLayout` 제공. `DefaultLayout`은 화면별 `contentMaxWidth` 지정 가능 |
| `shared/types/`       | 공통 API 응답, pagination 등 전역 타입. 현재 `api.types.ts` 제공                                  |
| `shared/utils/`       | 포맷터, 검증기 등 순수 유틸 함수                                                                  |

## 스타일 기반

- Tailwind CSS는 Vite 플러그인 방식으로 연결합니다.
- Tailwind import는 `src/assets/tailwind.css`에서 담당합니다.
- 디자인 토큰과 전역 reset은 `src/assets/main.scss`에서 담당합니다.
- 색상, 간격, radius, 버튼 높이 등 디자인 값은 CSS 변수로 관리합니다.
- `DefaultLayout`은 전역 reset과 무관하게 중앙 콘텐츠 폭과 반응형 바깥 여백을 유지하도록 scoped SCSS를 사용합니다.
- 기본 콘텐츠 폭은 `--layout-content-max-width`이며, 화면에서 `contentMaxWidth` prop으로
  폭을 조정할 수 있습니다. 홈 화면은 `1200px`을 사용합니다.

## 구현 상태

- 라우터는 `router/routes.ts`로 route 배열을 분리했으며 AUTH-001~AUTH-004 후보,
  ONBOARD-001~ONBOARD-004, BIZ-001·BIZ-001-2, HOME, FOLLOWING_HOME placeholder,
  LIVE_LIST·LIVE_CREATE·LIVE_WATCH 실제 화면, 공개 PROD-008 route가 등록되어 있습니다.
- `router/index.ts`에는 `requiresAuth`, `guestOnly` 메타 기반 인증 guard가 구현되어 있습니다.
- `App.vue`는 `RouterView`만 렌더링합니다.
- 기능 ID prefix 기준 도메인 폴더와 공통 폴더가 생성되어 있습니다.
- `domains/auth`에는 회원가입 방식 선택 화면, 이메일 회원가입 화면, 이메일 로그인 화면, 이메일 인증 UI, SSAFY 로그인/가입 시작 화면, SSO callback 화면, 계정 연결 화면, 인증 API 호출 함수와 타입, 인증 store가 구현되어 있습니다.
- `domains/onboard`에는 기본 정보, 관심 정보, AI 시착 정보 입력·저장 화면과 ONBOARD-004 이동 확인용 임시 화면 및 관련 API·컴포넌트가 구현되어 있습니다.
- `domains/biz`에는 BIZ-001 사업자 정보 입력·검증 화면, 사업자등록증 이미지 선택
  컴포넌트, FE 더미 제출 상태 store와 BIZ-001-2 인증 대기 화면이 구현되어 있습니다.
  BIZ-001-2의 메인 이동은 HOME route로 연결되어 있으며, 실제 인증 API는 후속 작업 대기 중입니다.
- `domains/home`에는 HOME 공개 route, 로그인 여부에 따른 `GuestHome`/`MemberHome`
  분기, 홈 검색 패널, 섹션 shell, 공통 홈 hero/content 카드, 라이브 카드, 상품 카드,
  화면 확인용 mock 데이터와 `HomeViewData` view model 타입이 구현되어 있습니다.
  `homeViewApi.ts`는 현재 mock 데이터를 반환하는 adapter 자리이며, `HomePage`는
  loading/error/retry 상태를 처리합니다.
  실제 HOME API 계약이 확정되면 adapter 내부를 HTTP 호출과 응답 매핑으로 교체합니다.
- `domains/product`에는 PROD-008 상품 목록 View와 S15P11A108-408·410·412 상품 상세 UI가
  구현되어 있습니다. 상품 목록은 실사형 로컬 WebP를 사용하고 최소·최대 가격 범위를 검증해
  mock 상품을 필터링하며 결과 없음 상태를 제공합니다. 상품 목록 카드는 상품 ID가 포함된 상세
  route로 이동합니다. 상세 화면은
  썸네일과 대표 이미지·AI 원본/검수 이미지 쌍을 함께 변경하며 찜·장바구니·라이브 알림 상태,
  기존 라이브 route 이동과 미구현 CTA 안내를 제공합니다. 구매 영역 아래에는 유사 상품의
  가격대 분포와 선택 상품 상세 이동을 제공하는 `ProductPriceDistribution`이 있으며, 실제
  추천 API 전까지 명시적인 mock view model을 사용합니다. 상세 조회의 로딩·오류·상품 없음·
  판매 완료와 AI 분석 전·중·완료·결과 없음·실패 상태를 구분하며 mock adapter에서 데이터를
  받습니다. 실제 API 계약이 확정되면 adapter 내부를 교체합니다.
- `domains/live`에는 S15P11A108-413·415·418 공개 라이브 목록 View, 진행 중·예정 상태 카드,
  로컬 이미지 기반 mock 데이터와 라이브 시청 route 연결, 카테고리·방송 상태 필터,
  최신 방송·시청자·제목 정렬과 초기화가 구현되어 있습니다. 공개 목록에서는 종료 방송과
  상품 판매 방식 조건을 제외합니다. 목록 DTO·adapter와 API 호출 함수, loading skeleton,
  전체 빈 목록·필터 결과 없음·오류·재시도 상태를 제공합니다.
  `origin/develop-BE@dd6a0b6`에 `GET /api/lives`가 구현됐지만 최종 `009` 계약의
  복수 `categories[]`, 공통 `PageResponse.content`, nullable `viewerCount`와
  `VIEWERS_DESC` 미지원 정책을 기존 418 adapter에 반영하기 전까지 기본값은 mock입니다.
- `domains/live`에는 LIVE-001/002 라이브 개설 화면이 구현되어 있습니다. `/lives/new`에서
  라이브 유형, 방송 정보, 판매 상품, 예약 일정, 장비 확인, 완료 단계를 순차 진행하며
  필수값과 과거 일정을 검증합니다. 상품 검색/선택은 mock 데이터로 처리하고, 즉시 시작의
  장비 확인은 `navigator.mediaDevices.getUserMedia` 기반 카메라 미리보기와 마이크 권한
  확인을 순차 실행합니다. 실제 생성/예약 API와 방송 SDK 연동은 후속 작업 대기 중입니다.
- `domains/live`에는 S15P11A108-419 LIVE-005 시청 화면 전체 구조가 구현되어 있습니다.
  `/lives/:liveId`에서 방송 헤더, 상품 큐, mock 영상 stage, 선택 상품 정보와 경매 패널
  영역을 dark live layout으로 제공합니다. loading·오류·방송 없음·상품 없음·예정·종료
  상태를 mock query로 확인할 수 있고 `GET /api/lives/{liveId}` DTO adapter를 분리했습니다.
  현재 동시 시청자, 현재 상품과 상세 상품 정보는 Swagger 계약에 없으므로 기본값은 mock이며
  실제 스트리밍과 상세 API 연동은 후속 작업 대기 중입니다.
- `domains/chat`에는 S15P11A108-423 라이브 채팅 overlay가 구현되어 있습니다. Figma 더미
  메시지 목록, 판매자 메시지 구분, 하트·불·박수·놀람 반응과 로컬 입력을 제공하며 실제
  WebSocket/STOMP·과거 메시지·AI 답변 연동은 대기 중입니다.
- `domains/auction`에는 S15P11A108-423 시청자 경매 패널이 구현되어 있습니다. 현재가·다음
  입찰가·타이머·최고 입찰자·사용 가능 포인트와 입찰 CTA를 표시하고, mock 처리 중·최근
  입찰자·포인트 부족·예정·종료·상품 없음 상태를 제공합니다. 실제 snapshot·입찰·event와
  포인트 처리는 `012-live-watch-detail-contract-gaps.md` 계약 확정 후 연결합니다.
- `domains/tryon`에는 S15P11A108-425 라이브 AI 시착 패널이 구현되어 있습니다. 등록 사진
  있음·없음, 로컬 이미지 변경, 생성 중·결과·실패·재시도와 결과 저장 피드백을 mock으로
  제공하며, 상품 변경 시 이전 결과를 초기화합니다. 실제 사진·생성·저장 계약은
  `013-live-tryon-contract.md` 확정 후 연결합니다.
- 나머지 도메인 폴더는 구조 보존용 `.gitkeep`만 유지합니다.
- `shared/api/authTokenStorage.ts`에는 local/session storage 기반 인증 토큰 저장 유틸이 구현되어 있습니다.
- `shared/utils/validators.ts`에는 회원가입과 로그인 입력 검증에 사용하는 순수 검증 유틸이 구현되어 있습니다.
- 전역 스타일은 디자인 토큰, reset, 기본 font-family와 온보딩 오류 토큰을 포함합니다.

### 2026-07-28 검색 화면 반영

- `domains/search`는 SEARCH-001/002 공개 route, 검색 결과 탭, 상품/라이브/회원 mock 결과 카드,
  카테고리·상태·가격·판매 유형 필터, loading/error/empty/filter-empty/price-error 상태 화면을 구현했습니다.
- 검색어·탭·필터는 `/search` query 기반으로 동작하며, 실제 통합 검색 API 계약 확정 전까지
  `searchMockData.ts`에서 클라이언트 필터링합니다.
- `src/assets/main.scss`에는 상품 목록과 검색 화면이 공유하는 필터 패널 폭, 본문/캡션/버튼 글자 크기,
  font-weight, line-height 토큰을 추가했습니다.
