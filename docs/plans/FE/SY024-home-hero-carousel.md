# Home Hero Carousel

## 배경/목표

홈 화면 상단의 기존 단일 히어로 배너를 VinTib 핵심 기능을 소개하는 3개 배너 캐러셀로 변경한다. 이벤트 광고처럼 보이지 않도록 빈티지 패션 매거진 톤을 유지하고, 라이브 진입/서비스 탐색/판매자 등록 행동을 자연스럽게 유도한다.

사용자 요청에 `PointWalletPage.vue` 링크가 포함되어 있으나 요구사항의 대상은 홈 화면이므로 포인트 페이지는 수정하지 않는다.

## 작업 내용

- `FE/src/domains/home/components/HomeHeroCarousel.vue`를 새로 추가한다.
- 회원/비회원 홈 컴포넌트의 기존 `HomeHero` 사용부를 새 캐러셀로 교체한다.
- 첫 번째 배너는 `HomeViewData.liveNow`가 있으면 진행 중 라이브, 없으면 `scheduledLives` 중 가장 가까운 예약 라이브를 사용한다.
- 라이브/예약 라이브 데이터가 없거나 이미지 URL이 비어도 깨지지 않도록 Unsplash 기반 fallback 이미지를 적용한다.
- 두 번째/세 번째 배너는 정적 카피와 이미지 구성을 사용하되 CTA는 각각 상품 목록과 상품 등록 페이지로 연결한다.
- 배너 전체 클릭과 CTA 클릭 모두 같은 목적지로 이동하게 하며, CTA 클릭이 중복 라우팅을 유발하지 않도록 이벤트 처리를 분리한다.
- 좌우 화살표, 드래그/스와이프, 인디케이터 클릭, 키보드 좌우 방향키 이동을 지원한다.
- 5초 자동 전환을 적용하고 hover, focus-in, 드래그/스와이프, 수동 이동 중에는 일시 정지한다.
- `prefers-reduced-motion: reduce` 환경에서는 slide transition 시간을 최소화한다.
- 기존 전역 CSS 변수와 요청 색상 팔레트(Warm Paper, Ink Black, Vintage Green, Accent Red, Film Gray, Gold Foil)를 CSS 변수 참조 또는 컴포넌트 scoped 스타일 안에서 사용한다.

## 구현 목록

- [x] 홈 라이브 데이터를 받아 캐러셀 slide view model로 변환하는 computed 구조 작성
- [x] 진행 중 라이브/예약 라이브 분기와 날짜 표시 포맷 구현
- [x] 3개 배너의 공통 레이아웃, CTA 위치, 이미지 영역 오버레이, fallback 이미지 구현
- [x] 무한 순환 이전/다음 이동과 pill 인디케이터 구현
- [x] pointer drag/swipe 및 keyboard 이동 처리 구현
- [x] 5초 자동 전환과 hover/focus/manual interaction pause 처리 구현
- [x] 이미지 비율로 커지지 않도록 desktop 300px, mobile 340px 고정 높이로 조정
- [x] `MemberHome.vue`, `GuestHome.vue`에서 기존 `HomeHero`를 `HomeHeroCarousel`로 교체
- [x] 불필요해진 기존 히어로 버튼 스타일 정리 또는 남는 사용처 확인
- [x] `npm run type-check`로 타입 검증

## 확인 필요/미결정

- 현재 홈 API의 `scheduledLives` 정렬 보장은 FE에서 확정할 수 없으므로, 캐러셀 내부에서 `scheduledAt` 기준으로 가장 가까운 예약 라이브를 선택한다.
- 배너 3의 상품 등록 CTA는 기존 `ROUTE_PATHS.PRODUCT_CREATE`를 사용한다. 비회원 접근 시 기존 라우터/페이지의 인증 처리 정책을 따른다.
- 배너 1의 진행 중 라이브 CTA는 선택된 라이브가 있으면 `/lives/:liveId`, 없으면 `/lives`로 이동한다.
