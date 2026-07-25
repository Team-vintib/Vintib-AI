# 현재 프로젝트 구조

확인일: 2026-07-26

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

| 명령 | 설명 |
| --- | --- |
| `npm run dev` | Vite 개발 서버 실행 |
| `npm run build` | 타입 체크 후 빌드 |
| `npm run preview` | Vite preview |
| `npm run type-check` | `vue-tsc --build` |
| `npm run lint` | ESLint fix |
| `npm run format` | `src/` Prettier 적용 |

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
    main.scss
    tailwind.css
  domains/
    auth/
      api/
      components/
      constants/
      pages/
      types/
    onboard/
      api/
      components/
      constants/
      pages/
      types/
    biz/
      api/
      components/
      constants/
      pages/
      types/
    home/
      api/
      components/
      constants/
      pages/
      types/
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
      components/
      constants/
      pages/
      types/
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
    routes.ts
  shared/
    api/
      http.ts
    components/
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

docs/
  notion/
```

빈 폴더는 구조 보존을 위해 `.gitkeep`을 둡니다.

## 기능 ID prefix와 도메인 폴더 매핑

| Prefix | 도메인 폴더 | 기준 기능 |
| --- | --- | --- |
| `AUTH` | `domains/auth` | 회원가입, 로그인, SSO, 계정 연결 |
| `ONBOARD` | `domains/onboard` | 가입 후 기본 정보, 관심 정보, AI 시착 정보, 회원 유형 |
| `BIZ` | `domains/biz` | 사업자 인증, 세금계산서 |
| `HOME` | `domains/home` | 홈, 팔로잉 홈 |
| `SEARCH` | `domains/search` | 통합 검색, 필터 |
| `REC` | `domains/recommendation` | 개인화 추천 |
| `FOLLOW` | `domains/follow` | 팔로우, 팔로우 해제 |
| `NOTI` | `domains/notification` | 알림 센터, 라이브/경매/거래/배송 알림 |
| `PROD` | `domains/product` | 상품 등록, 상세, 목록, 관리 |
| `LIVE` | `domains/live` | 라이브 예약, 즉시 방송, 시청, 다시보기 |
| `CHAT` | `domains/chat` | 라이브 채팅, AI 답변 |
| `AUCT` | `domains/auction` | 경매 설정, 입찰, 낙찰 |
| `TRYON` | `domains/tryon` | AI 가상 시착 |
| `POINT` | `domains/point` | 포인트 충전, 내역, 출금, 정산 |
| `SALE` | `domains/sale` | 상시 판매 구매 |
| `SHIP` | `domains/shipping` | 송장 등록, 배송 조회 |
| `ORDER` | `domains/order` | 배송지, 구매 확정 |
| `REFUND` | `domains/refund` | 환불 신청, 환불 처리 |
| `MY` | `domains/my` | 마이페이지, 회원 정보, 내역 관리 |

## 도메인 내부 폴더 기준

| 폴더 | 용도 |
| --- | --- |
| `pages/` | 라우터에 직접 연결되는 화면 컴포넌트 |
| `components/` | 해당 도메인에서만 사용하는 화면 조각 |
| `api/` | 해당 도메인의 API 호출 함수 |
| `types/` | 해당 도메인의 요청, 응답, 화면 상태 타입 |
| `constants/` | 해당 도메인 전용 상수, 옵션, 메시지 |

## 공통 폴더 기준

| 폴더 | 용도 |
| --- | --- |
| `app/` | 앱 조립 계층. 라우터/Pinia provider 등 전역 설정 후보 |
| `shared/api/` | Axios 인스턴스, 공통 API 유틸. 현재 `http.ts` 제공 |
| `shared/components/` | 2개 이상 도메인에서 재사용되는 UI 컴포넌트 |
| `shared/composables/` | 2개 이상 도메인에서 재사용되는 Composition API 함수 |
| `shared/constants/` | 라우트명, 전역 옵션 등 공통 상수. 현재 `routes.ts` 제공 |
| `shared/layouts/` | 인증, 기본 서비스, 라이브 등 공통 레이아웃. 현재 `AuthLayout`, `DefaultLayout`, `LiveLayout` 제공 |
| `shared/types/` | 공통 API 응답, pagination 등 전역 타입. 현재 `api.types.ts` 제공 |
| `shared/utils/` | 포맷터, 검증기 등 순수 유틸 함수 |

## 스타일 기반

- Tailwind CSS는 Vite 플러그인 방식으로 연결합니다.
- Tailwind import는 `src/assets/tailwind.css`에서 담당합니다.
- 디자인 토큰과 전역 reset은 `src/assets/main.scss`에서 담당합니다.
- 색상, 간격, radius, 버튼 높이 등 디자인 값은 CSS 변수로 관리합니다.

## 구현 상태

- 라우터는 `router/routes.ts`로 route 배열을 분리했으며, 등록된 화면 route는 아직 없습니다.
- `App.vue`는 `RouterView`만 렌더링합니다.
- 기능 ID prefix 기준 도메인 폴더와 공통 폴더는 생성되어 있습니다.
- 각 폴더에는 구조 보존용 `.gitkeep`만 있으며 실제 화면, API, 타입 구현은 아직 없습니다.
- 전역 스타일은 디자인 토큰, reset, 기본 font-family를 포함합니다.
