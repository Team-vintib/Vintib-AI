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
- 스타일: SCSS
- HTTP: Axios
- Lint/Format: ESLint(flat config) + Prettier
- 실시간: STOMP over WebSocket 도입 예정 (`@stomp/stompjs`, 아직 미설치)
- 라이브 영상 재생: 방송 인프라 확정 후 결정 (HLS.js 또는 WebRTC SDK)
- UI 컴포넌트 라이브러리: 미확정 (Vuetify / Element Plus / Naive UI 중 검토)

> `node`/`npm`이 로컬에 없어 `npm create vue@latest` 대신 동일한 구성(Vue 3 + TS + Router + Pinia + ESLint + Prettier)을 수동으로 작성함. 패키지 버전은 npm 레지스트리 최신 기준.

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
├── src/
│   ├── main.ts
│   ├── App.vue
│   ├── router/index.ts
│   └── assets/main.scss
```

`components/`, `views/`, `stores/` 등 도메인별 폴더는 화면 설계 확정 후 추가.