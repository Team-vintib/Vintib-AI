# FE

빈티지·세컨핸드 의류 라이브 경매 플랫폼 프론트엔드.

## 담당 범위

기능정의서 4장 기준 아래 화면을 담당한다.

- 회원가입/로그인, 마이페이지 (프로필, 거래 내역, 포인트/정산, 정산 계좌)
- 홈, 검색/필터, 팔로우, 알림, 추천 노출
- 상품 등록 폼, 상품 상세, 상시 판매/경매 상품 목록
- 라이브 시청 화면 (영상, 실시간 채팅, 자막, 경매 현황)
- 실시간 경매 UI (입찰 버튼, 포인트 홀드 표시, 낙찰 결과)
- AI 가상 시착 UI (전신 사진 등록, 시착 결과 조회/저장)
- 포인트 충전/결제, 배송 조회, 구매 확정 화면

## 기술 스택

- Vue.js 3.5.x, TypeScript, Vite
- 상태관리: Pinia / 라우팅: Vue Router
- 스타일: Tailwind CSS, SCSS
- HTTP: Axios
- Lint/Format: ESLint(flat config) + Prettier
- 실시간: STOMP over WebSocket 도입 예정 (`@stomp/stompjs`, 아직 미설치)
- 라이브 영상 재생: 방송 인프라 확정 후 결정 (HLS.js 또는 WebRTC SDK)
- UI 컴포넌트 라이브러리: 미확정 (Vuetify / Element Plus / Naive UI 중 검토)

## 실행 방법

1. `npm install`
2. `.env.example`을 `.env`로 복사 후 값 조정
3. `npm run dev` (기본 5173 포트, `/api`는 `VITE_API_BASE_URL`로 프록시)

## 디렉터리 구조

```
FE/
├── index.html
├── vite.config.ts
├── eslint.config.js
├── package-lock.json
├── src/
│   ├── main.ts
│   ├── App.vue
│   ├── app/
│   │   └── providers/
│   ├── assets/
│   │   ├── tailwind.css
│   │   └── main.scss
│   ├── router/
│   │   ├── index.ts
│   │   └── routes.ts
│   ├── domains/
│   │   ├── auth/
│   │   ├── onboard/
│   │   ├── biz/
│   │   ├── home/
│   │   ├── search/
│   │   ├── recommendation/
│   │   ├── follow/
│   │   ├── notification/
│   │   ├── product/
│   │   ├── live/
│   │   ├── chat/
│   │   ├── auction/
│   │   ├── tryon/
│   │   ├── point/
│   │   ├── sale/
│   │   ├── shipping/
│   │   ├── order/
│   │   ├── refund/
│   │   └── my/
│   └── shared/
│       ├── api/
│       ├── components/
│       ├── composables/
│       ├── constants/
│       ├── layouts/
│       ├── types/
│       └── utils/
```

도메인 폴더는 기능정의서의 기능 ID prefix 기준으로 분리한다. 각 도메인은 `pages`, `components`, `api`, `types`, `constants` 하위 폴더를 가진다.

## 스타일 기준

- Tailwind CSS는 `src/assets/tailwind.css`에서 import한다.
- 디자인 토큰과 전역 reset은 `src/assets/main.scss`에서 관리한다.
- 화면과 컴포넌트에서는 HEX 값을 직접 반복하지 않고 CSS 변수 또는 Tailwind arbitrary value로 참조한다.
