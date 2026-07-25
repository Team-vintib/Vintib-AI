# 구현 상태

확인일: 2026-07-26

| 영역 | 상태 | 비고 |
| --- | --- | --- |
| 프로젝트 초기화 | 완료 | Vue/Vite/TS 구성 존재 |
| src 도메인 구조 | 완료 | 기능 ID prefix 기준 `domains/*`, 공통 `shared/*`, 앱 조립 `app/*` 생성 |
| Tailwind CSS | 완료 | Vite 플러그인 연결, `src/assets/tailwind.css` import |
| 디자인 토큰 | 완료 | `src/assets/main.scss`에 색상/간격/radius/버튼 높이 변수 선언 |
| 라우터 | 부분 | `router/routes.ts`로 route 배열 분리, 실제 화면 route는 미등록 |
| Pinia | 부분 | 앱 등록 완료, store 없음 |
| Axios | 부분 | `shared/api/http.ts` 공통 인스턴스 생성, 인증/재발급 정책은 미확정 |
| 스타일 | 부분 | Tailwind와 전역 SCSS 기반 완료, 공통 UI 컴포넌트는 미구현 |
| 레이아웃 | 부분 | `AuthLayout`, `DefaultLayout`, `LiveLayout` 기본 슬롯 레이아웃 생성 |
| 인증 화면 | 미구현 | 첫 구현 대상 |
| 온보딩 화면 | 미구현 | 인증 직후 흐름 |
| 공통 컴포넌트 | 미구현 | BaseButton/BaseInput부터 권장 |
| API 타입 | 부분 | `shared/types/api.types.ts` 공통 응답/에러/pagination 타입 생성 |
| Mock 데이터 | 미구현 | 인증 화면부터 가능 |
| 테스트/검증 | 부분 | `npm run type-check`, `npm run build-only` 통과 |
