# 구현 상태

확인일: 2026-07-26

| 영역            | 상태   | 비고                                                                                           |
| --------------- | ------ | ---------------------------------------------------------------------------------------------- |
| 프로젝트 초기화 | 완료   | Vue/Vite/TS 구성 존재                                                                          |
| src 도메인 구조 | 완료   | 기능 ID prefix 기준 `domains/*`, 공통 `shared/*`, 앱 조립 `app/*` 생성                         |
| Tailwind CSS    | 완료   | Vite 플러그인 연결, `src/assets/tailwind.css` import                                           |
| 디자인 토큰     | 완료   | `src/assets/main.scss`에 색상/간격/radius/버튼 높이/오류 변수 선언                             |
| 라우터          | 부분   | `router/routes.ts`로 route 배열 분리, ONBOARD-001~003 등록                                     |
| Pinia           | 부분   | 앱 등록 완료, store 없음                                                                       |
| Axios           | 부분   | `shared/api/http.ts` 공통 인스턴스, ApiResponse envelope 정규화, AUTH-001·ONBOARD-001·002 연동 |
| 스타일          | 부분   | Tailwind와 전역 SCSS 기반 완료, 온보딩 UI 컴포넌트 및 회원가입 화면 스타일 구현                |
| 레이아웃        | 부분   | 공통 슬롯 레이아웃, 인증 레이아웃, 온보딩 단계 레이아웃 구현                                   |
| 인증 화면       | 부분   | AUTH-001 이메일 회원가입 FE 완료, BE 메일 환경변수 이슈로 이메일 발송 E2E 재검증 필요          |
| 온보딩 화면     | 부분   | ONBOARD-001 FE 완료, ONBOARD-002 저장·건너뛰기·이동 완료, ONBOARD-003 임시 화면                |
| 공통 컴포넌트   | 부분   | 온보딩 도메인에 BaseButton, BaseInput, BaseField, 단계 표시 구현                               |
| API 타입        | 부분   | 공통 응답/에러/pagination, 인증 요청/응답 타입, 온보딩 필드 오류 타입 구현                     |
| Mock 데이터     | 미구현 | 인증 화면부터 가능                                                                             |
| 테스트/검증     | 부분   | lint, type-check, build, AUTH-001 화면/입력 상태 검증, ONBOARD-001·002 브라우저 동작 검증      |
