# 현재 프로젝트 구조

확인일: 2026-07-27

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
      constants/
      pages/
      types/
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
      components/
      constants/
      pages/
      types/
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
      constants/
      pages/
      types/
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
  LIVE placeholder, 공개 PROD-008
  route가 등록되어 있습니다.
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
  기존 라이브 route 이동과 미구현 CTA 안내를 제공합니다. 상세 조회의 로딩·오류·상품 없음·
  판매 완료와 AI 분석 전·중·완료·결과 없음·실패 상태를 구분하며 mock adapter에서 데이터를
  받습니다. 실제 API 계약이 확정되면 adapter 내부를 교체합니다.
- 나머지 도메인 폴더는 구조 보존용 `.gitkeep`만 유지합니다.
- `shared/api/authTokenStorage.ts`에는 local/session storage 기반 인증 토큰 저장 유틸이 구현되어 있습니다.
- `shared/utils/validators.ts`에는 회원가입과 로그인 입력 검증에 사용하는 순수 검증 유틸이 구현되어 있습니다.
- 전역 스타일은 디자인 토큰, reset, 기본 font-family와 온보딩 오류 토큰을 포함합니다.
