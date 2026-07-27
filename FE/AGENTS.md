# VinTib FE Codex 작업 규칙

이 저장소는 VinTib 프론트엔드 프로젝트입니다. Codex는 아래 기준을 우선 적용합니다.
루트 `AGENTS.md`의 공통 규율(새 기능 계획 선승인, 파트 간 요청 문서, push 금지 등)은 이 폴더 작업에도 그대로 적용됩니다.

## 작업 범위

- 프론트엔드 기술 스택은 Vue 3, TypeScript, Vite, Vue Router, Pinia, Axios, SCSS입니다.
- 화면 구현 기준은 `docs/notion/화면 기반 개발 요구 문서.md`를 1순위로 사용합니다.
- 기능 범위 기준은 `docs/notion/기능 정의서.md`를 사용합니다.
- 디자인 토큰과 시각 규칙은 `docs/notion/프론트엔드 디자인 구현 규칙.md`를 사용합니다.
- Vue 코드 작성 방식은 `docs/notion/프론트엔드 개발 공통 규칙.md`를 사용합니다.
- FE 작업은 `FE/` 내부만 수정합니다. `BE/`, `AI/`, `infra/` 등 다른 파트는 읽기만 하며 직접 수정하지 않습니다.

## 새 기능 계획

신규 화면/기능 등 새 기능은 바로 구현하지 않습니다. 먼저 계획을 세워 `.codex/plans/fe/`(루트 기준)에 md로 기록하고, 사용자 승인 후 그 계획대로 구현합니다. 파일 규칙(경로, `<이니셜><번호>-slug.md` 형식, 계획 내용 구성)은 루트 `.claude/plans/README.md`를 그대로 따르되 저장 위치만 `.codex/plans/fe/`를 씁니다. 버그 수정 등 설계 판단이 필요 없는 변경에는 적용하지 않습니다.

기존 `001-onboarding-...` 형식의 계획 파일은 이 규칙 이전에 작성된 것으로 소급 변경하지 않습니다. 새로 작성하는 계획 파일부터 `<이니셜><번호>-slug.md` 형식을 적용합니다.

## 다른 파트 요청

BE/AI 코드는 직접 수정하지 않습니다. BE나 AI 쪽 변경이 필요하면 `.codex/requests/be/` 또는 `.codex/requests/ai/`(루트 기준)에 md로 요청 문서를 남깁니다. 형식은 루트 `.claude/requests/README.md`를 그대로 따르되 저장 위치만 `.codex/requests/<대상 파트>/`를 씁니다.

## 자료 우선순위

1. 화면별 동작, 입력, 상태, 이동: 화면 기반 개발 요구 문서
2. 기능 범위와 MVP 여부: 기능 정의서
3. 화면 연결 흐름: Figma Wireframe Copy
4. 시각 디자인: Figma Make 프로토타입, 없으면 Figma 와이어프레임과 디자인 구현 규칙
5. 코드 구조: 기존 구현 코드와 프론트엔드 개발 공통 규칙
6. API 요청/응답: Swagger가 제공되기 전까지는 `docs/frontend/api/api-index.md`의 임시 후보를 사용

## 작업 시작 전 필수 확인

- 새 화면 또는 화면 단위 기능을 구현하기 전에는 반드시 관련 프로토타입과 Figma Wireframe을 먼저 확인합니다.
- 계획 문서를 작성할 때도 프로토타입과 Figma Wireframe에서 확인한 화면 구조, 네비게이션, 주요 UI 요소를 반영합니다.
- 구현 시 현재 저장소에 이미 구현된 다른 페이지와 컴포넌트를 함께 확인해 레이아웃, spacing, 색상, 버튼, 카드 스타일이 기존 화면과 어긋나지 않도록 합니다.
- 프로토타입과 기존 구현이 충돌하면 기존 구현을 우선하되, 충돌 내용은 계획 문서나 `docs/frontend/decisions/open-questions.md`에 남깁니다.

## 구현 제한

- FE 폴더 외 AI, BE,infra 폴더는 조회만 가능하며, 절대 수정, 삭제, 생성 등 업데이트 않습니다.
- 팀원이 작업 중일 수 있으므로 기존 파일을 임의로 삭제하거나 이동하지 않습니다.
- `src/` 변경 전에는 관련 화면의 요구사항 문서를 먼저 확인합니다.
- `src/` 변경 전에는 관련 프로토타입과 Figma Wireframe을 확인하고, 현재 구현된 유사 페이지의 디자인 구성을 함께 참고합니다.
- `확인 필요`, `미확정`, `설계 제안`으로 표시된 항목은 확정값처럼 구현하지 않습니다.
- API 요청/응답 필드는 FE에서 임의로 확정하지 않습니다. Swagger, `APIs.md`, DB/기능 문서로 확인되지 않은 필드는 `임시 view model`, `Mock 전용`, `BE 확인 필요`처럼 표시하고, BE 판단이 필요하면 루트 `.claude/requests/be/`에 요청 문서를 남깁니다.
- 충돌 또는 미확정 사항은 `docs/frontend/decisions/open-questions.md`에 기록합니다.
- 새 라이브러리는 팀 합의 없이 설치하지 않습니다.
- Git commit, push, checkout, reset은 명시 요청 없이는 실행하지 않습니다.

## src 구조 규칙

`src/`는 앱 조립 계층, 도메인 계층, 공통 계층으로 나눕니다.

```text
src/
  app/
  domains/
  shared/
  assets/
  router/
  App.vue
  main.ts
```

- `app/`: 라우터, Pinia 등 앱 전역 provider와 앱 조립 코드 후보를 둡니다.
- `domains/`: 기능정의서의 기능 ID prefix 기준으로 화면과 도메인 코드를 분리합니다.
- `shared/`: 2개 이상 도메인에서 실제로 재사용되는 공통 코드만 둡니다.
- `assets/main.scss`: 전역 스타일과 디자인 변수 선언 위치입니다.
- `router/index.ts`: 현재 라우터 진입점입니다. 라우트가 많아지면 도메인별 route 정의를 import하는 방식으로 확장합니다.

## 도메인 prefix 매핑

기능정의서의 기능 ID prefix를 아래 폴더에 매핑합니다.

| Prefix | 폴더 | 담당 영역 |
| --- | --- | --- |
| `AUTH` | `domains/auth` | 회원가입, 로그인, SSO, 계정 연결 |
| `ONBOARD` | `domains/onboard` | 온보딩 |
| `BIZ` | `domains/biz` | 사업자 인증, 사업자 기능 |
| `HOME` | `domains/home` | 홈, 팔로잉 홈 |
| `SEARCH` | `domains/search` | 검색, 필터 |
| `REC` | `domains/recommendation` | 추천 |
| `FOLLOW` | `domains/follow` | 팔로우 |
| `NOTI` | `domains/notification` | 알림 |
| `PROD` | `domains/product` | 상품 등록, 상품 상세, 상품 관리 |
| `LIVE` | `domains/live` | 라이브 예약, 방송, 시청 |
| `CHAT` | `domains/chat` | 채팅, AI 답변 표시 |
| `AUCT` | `domains/auction` | 경매, 입찰, 낙찰 |
| `TRYON` | `domains/tryon` | AI 가상 시착 |
| `POINT` | `domains/point` | 포인트, 출금, 정산 |
| `SALE` | `domains/sale` | 상시 판매 구매 |
| `SHIP` | `domains/shipping` | 배송, 송장 |
| `ORDER` | `domains/order` | 주문, 배송지, 구매 확정 |
| `REFUND` | `domains/refund` | 환불 |
| `MY` | `domains/my` | 마이페이지 |

## 도메인 내부 구조

각 도메인은 같은 하위 폴더를 사용합니다.

```text
domains/<domain>/
  pages/
  components/
  api/
  types/
  constants/
```

- `pages/`: 라우터에 직접 연결되는 화면 컴포넌트입니다. 예: `domains/auth/pages/SignupPage.vue`
- `components/`: 해당 도메인 안에서만 쓰는 컴포넌트입니다.
- `api/`: 해당 도메인의 API 호출 함수입니다.
- `types/`: 해당 도메인의 요청, 응답, 화면 상태 타입입니다.
- `constants/`: 해당 도메인 전용 상수, 옵션, 메시지입니다.
- 빈 폴더 보존을 위해 `.gitkeep`은 유지합니다. 실제 파일이 생겨도 폴더를 비우지 않는 한 임의 삭제하지 않습니다.

## 공통 코드 이동 기준

- 한 도메인에서만 쓰는 코드는 해당 도메인 안에 둡니다.
- 2개 이상 도메인에서 실제로 재사용될 때만 `shared/`로 이동합니다.
- 공통화를 예상해서 먼저 `shared/`에 만들지 않습니다.
- 디자인 토큰, 색상, radius, spacing 같은 전역 변수는 `assets/main.scss`에서만 선언합니다.
- Tailwind를 사용할 때도 색상 값은 하드코딩하지 않고 CSS 변수 참조를 우선합니다.

## 문서 갱신 규칙

- 구조 변경 시 `docs/frontend/implementation/current-structure.md`를 함께 갱신합니다.
- 구현 상태가 바뀌면 `docs/frontend/implementation/status.md`를 함께 갱신합니다.
- 신규 화면/기능 구현 전 계획 기록 규칙은 위 "새 기능 계획" 섹션을 따릅니다.
- 화면 요구사항이 바뀌면 해당 `docs/frontend/screens/<SCREEN-ID>/requirements.md` 또는 원천 문서를 함께 확인합니다.

## 구현 순서

1. 인증 화면 묶음부터 구현합니다.
2. 라우트 URL은 Codex가 제안할 수 있습니다.
3. Swagger 제공 전에는 Mock 데이터와 임시 API 후보를 사용할 수 있습니다.
4. 반응형은 우선 1440px desktop first 기준으로 진행합니다.
5. 구현 후에는 `npm run type-check`와 가능한 범위의 빌드 검증을 수행합니다.