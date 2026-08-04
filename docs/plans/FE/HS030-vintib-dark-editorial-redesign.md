# HS030 — VinTib 다크 에디토리얼 전면 리디자인

## 배경/목표

FE 앱 전체 UI를 공유된 **VinTib 디자인 시스템**(다크 에디토리얼, 이미지 중심, 얇은 선·모노스페이스 라벨)으로 전환한다. 현재는 라이트 테마(`--color-page: #F7F6F2`, 브랜드 그린 `#294335`)이며, 이를 다크(`#0A0A0A` + 포인트 `#C43D46`)로 뒤집는다. 기능·API·라우팅은 건드리지 않는 **순수 시각 전환**이다.

## 핵심 전략 — 토큰 우선(foundation-first)

- 디자인이 `src/assets/main.scss`의 `:root` 토큰에 집중돼 있다. 전체 104개 `.vue` 중 **100개가 `var(--color-*)`/`var(--space-*)`/`var(--radius-*)`를 소비**하고, 하드코딩 hex는 ~40곳뿐이다.
- 따라서 **토큰 값만 교체하면 앱 전체가 즉시 다크 에디토리얼로 전환**된다(Phase 0). 이후 화면별로 구조 패턴(히어로·카드·모노 라벨·헤어라인 그리드·배지 정렬)만 정밀 손질한다.
- **토큰 이름은 유지하고 값만 바꾼다.** 그래야 100개 파일이 자동 상속한다. 새 개념(모노 라벨색, 헤어라인 그리드색 등)은 토큰을 *추가*한다.
- `--space-*` 스케일(4~64px)은 값이 범용적이라 그대로 둔다(1302회 참조 무변경).

## 핵심 결정 사항

1. **1차 CTA 색 의미 변경.** VinTib에서 1차 CTA는 컬러 채움이 아니라 **흰 블록**(`#F2F0ED` 배경 / `#0A0A0A` 글자), 호버 시 `#C43D46`. 현재 `--color-primary`(그린, 314회 참조)가 버튼·활성 상태·강조에 모두 쓰인다. → `--color-primary`를 **`#F2F0ED`(포그라운드 잉크)** 로 매핑하면 `background:var(--color-primary);color:var(--color-text-inverse)` 버튼이 곧바로 "흰 블록 CTA"가 된다. 포인트 레드는 별도 토큰(`--color-live`/신규 `--color-accent`)으로만 LIVE·경매에 쓴다. 버튼 컴포넌트는 Phase 1에서 hover 글자색까지 손본다.
2. **라이트→다크 flip 리스크.** 흰 배경·밝은 대비를 전제한 컴포넌트(하드코딩 hex 40곳 포함)는 다크에서 깨질 수 있다. Phase별 도메인 점검으로 잡는다. `prefers-reduced-motion`에서도 콘텐츠는 항상 보이게 한다(리빌 실패 시에도).
3. **라이브 화면은 이미 다크.** `--color-live-*` 토큰군이 존재하고 라이브 화면은 이미 다크라 VinTib에 가장 가깝다. 이 토큰들도 VinTib 다크값으로 정렬한다.
4. **폰트: Google Fonts CDN.** `index.html`에 Archivo(600) + IBM Plex Sans KR(300/400/500) + IBM Plex Mono(400/500) link 추가. 신규 토큰 `--font-display`/`--font-body`/`--font-mono`.
5. **레이아웃 풀블리드.** 현재 중앙정렬 `max-width:1320px` → VinTib는 폭 제한 없이 좌우 40px 거터. `DefaultLayout`에서 조정.

## 토큰 매핑 요약 (Phase 0)

| 토큰 | 현재(라이트) | VinTib(다크) |
| --- | --- | --- |
| `--color-page` | #F7F6F2 | **#0A0A0A** |
| `--color-surface` | #FFFFFF | **#141312** |
| `--color-surface-secondary` | #F0F0EB | **#101010** |
| `--color-text-primary` | #171815 | **#F2F0ED** |
| `--color-text-secondary` | #686A64 | **#B8B3AF** |
| `--color-text-muted` | #92948E | **#9A9591** |
| `--color-text-inverse` | #FFFFFF | **#0A0A0A** |
| `--color-border` | #E1E0DA | **#232120** |
| `--color-border-strong` | #C9C8C1 | **#3A3735** |
| `--color-primary` | #294335 | **#F2F0ED** (흰 잉크 = CTA/활성) |
| `--color-primary-hover` | #1F352A | **#C43D46** |
| `--color-primary-soft` | #E7EEE9 | **#141312** |
| `--color-live` / `--color-auction` | #C43D46 / #A92F38 | **#C43D46** (포인트 유지) |
| `--radius-control/card/media/modal` | 8/12/16/16px | **5px** |
| `--radius-chip` | 999px | **5px** (pill 폐지) |
| `--color-live-*` (다크 UI군) | 그린틴트 다크 | VinTib 중립 다크(#0A0A0A/#141312/#232120/#F2F0ED/#9A9591) |
| (신규) `--color-border-grid` | — | #1B1918 (헤어라인 그리드 갭) |
| (신규) `--color-border-input` | — | #2A2827 |
| (신규) `--color-text-caption` | — | #6B6663 |
| (신규) `--color-accent-hover` | — | #D45A62 |
| (신규) `--font-display/body/mono` | — | Archivo / IBM Plex Sans KR / IBM Plex Mono |

세부 값은 구현 시 규칙 문서(사용자 제공)를 최종 기준으로 미세조정한다.

## 구현 목록 (Phase 체크리스트)

- [ ] **P0 파운데이션** — `main.scss` 토큰 전면 교체, 신규 토큰 추가, body 폰트/색/무게(300), `img` 톤 필터 유틸(`saturate .88 contrast 1.04 brightness .95`), 전역 모노/라벨 유틸 클래스, `prefers-reduced-motion` 가드. `index.html` Google Fonts link. → 이 시점에서 앱 전체가 다크로 전환(라이브로 확인).
- [ ] **P1 공통 크롬·레이아웃** — `GlobalNavigation`, `AppFooter`, `AppSearchBar`, `DefaultLayout`(풀블리드 40px), `AuthLayout`, `LiveLayout`, `RoutePlaceholder`. 1차/2차 CTA 버튼 규칙, 활성 탭 흰 블록.
- [ ] **P2 공용 카드 패턴** — `ProductCard`(home·product), `LiveCard`, `LiveListCard`, `HomeSection`(섹션 헤더 헤어라인 + `View all →`), onboard `BaseButton/BaseInput/BaseField`, 헤어라인 그리드(`gap:1px;bg:#1B1918`) 유틸.
- [ ] **P3 홈** — `HomePage`, `HomeHero`(640px 풀블리드 3중 스크림), `MemberHome`, `GuestHome`, `CategoryProductTabs`, `HomeSearchPanel`.
- [ ] **P4 상품** — 리스트/상세/필터레일(232px)/갤러리/스펙 테이블(헤어라인 격자)/가격분포 차트/구매 요약/등록/AI 품질 패널.
- [ ] **P5 라이브** — 리스트·시청·방송·비디오 스테이지·상품 큐·선택상품·미판매 관리·방송종료 대시보드·헤더/상태.
- [ ] **P6 채팅·경매** — `LiveChatOverlay`, `LiveAuctionPanel`(경매 패널: 44px 모노 현재가·3px 진행바·입찰 추이 막대·풀폭 #C43D46 버튼), `SellerAuctionPanel`, `LiveAuctionResultOverlay`.
- [ ] **P7 AI 시착** — `TryOnPage`, `TryOnComposer`, `TryOnResultGallery`, `LiveTryOnPanel`(보라 `--color-ai`는 중립/포인트로 정리).
- [ ] **P8 온보딩·사업자** — onboarding 4 뷰 + 컴포넌트, biz 인증/대기 페이지, 업로더.
- [ ] **P9 인증** — login/signup/entry/link + SSAFY SSO 페이지·폼.
- [ ] **P10 팀원 도메인 정밀화** — my/point/notification/profile/search (P0 상속으로 이미 다크; 카드·라벨·모노 수치 손질).
- [ ] **P11 모션** — 스크롤 리빌(620ms, 55ms 스태거), 카드 호버(-3px + img scale 1.045), LIVE 도트 펄스, 차트 scaleY. `transform/opacity`만.
- [ ] **P12 마감 점검** — 하드코딩 hex 잔여 제거, 대비/접근성, reduced-motion, 반응형(1024/768/480), 라이트 잔재 스윕.

## 확인 필요 / 미결정

- **브랜치**: 스토리 단위 규칙상 현재 `feat/210-ai-tryon-entry-area`가 아니라 리디자인 전용 브랜치 권장(예: `feat/vintib-redesign`, Jira 티켓 번호 확인 필요). 브랜치 생성/푸시는 사용자가 결정·실행.
- **`--color-direct-sale`(파랑)·`--color-ai`(보라)·`--color-timer`(주황)**: VinTib 팔레트엔 없음. 중립/포인트로 정리할지 각 배지에서 판단(P4/P7에서 확정).
- **이미지 자산**: VinTib은 "이미지가 주인공". 현재 목/실데이터 이미지가 부족한 화면은 회색 박스 대신 기존 이미지 프레임(`#131211`) 유지. 실이미지 연동은 별도.
- **팀원 도메인(P10)**: 전체 앱 리디자인으로 합의됨. 진행 중 팀원 작업과 충돌 가능 → 커밋 단위를 도메인별로 잘게 나눠 리베이스 부담 최소화.
