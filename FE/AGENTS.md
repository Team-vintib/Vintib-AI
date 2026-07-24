# VinTib FE Codex 작업 규칙

이 저장소는 VinTib 프론트엔드 프로젝트입니다. Codex는 아래 기준을 우선 적용합니다.

## 작업 범위

- 프론트엔드 기술 스택은 Vue 3, TypeScript, Vite, Vue Router, Pinia, Axios, SCSS입니다.
- 화면 구현 기준은 `docs/notion/화면 기반 개발 요구 문서.md`를 1순위로 사용합니다.
- 기능 범위 기준은 `docs/notion/기능 정의서.md`를 사용합니다.
- 디자인 토큰과 시각 규칙은 `docs/notion/프론트엔드 디자인 구현 규칙.md`를 사용합니다.
- Vue 코드 작성 방식은 `docs/notion/프론트엔드 개발 공통 규칙.md`를 사용합니다.

## 자료 우선순위

1. 화면별 동작, 입력, 상태, 이동: 화면 기반 개발 요구 문서
2. 기능 범위와 MVP 여부: 기능 정의서
3. 화면 연결 흐름: Figma Wireframe Copy
4. 시각 디자인: Figma Make 프로토타입, 없으면 Figma 와이어프레임과 디자인 구현 규칙
5. 코드 구조: 기존 구현 코드와 프론트엔드 개발 공통 규칙
6. API 요청/응답: Swagger가 제공되기 전까지는 `docs/frontend/api/api-index.md`의 임시 후보를 사용

## 구현 제한

- 팀원이 작업 중일 수 있으므로 기존 파일을 임의로 삭제하거나 이동하지 않습니다.
- `src/` 변경 전에는 관련 화면의 요구사항 문서를 먼저 확인합니다.
- `확인 필요`, `미확정`, `설계 제안`으로 표시된 항목은 확정값처럼 구현하지 않습니다.
- 충돌 또는 미확정 사항은 `docs/frontend/decisions/open-questions.md`에 기록합니다.
- 새 라이브러리는 팀 합의 없이 설치하지 않습니다.
- Git commit, push, checkout, reset은 명시 요청 없이는 실행하지 않습니다.

## 구현 순서

1. 인증 화면 묶음부터 구현합니다.
2. 라우트 URL은 Codex가 제안할 수 있습니다.
3. Swagger 제공 전에는 Mock 데이터와 임시 API 후보를 사용할 수 있습니다.
4. 반응형은 우선 1440px desktop first 기준으로 진행합니다.
5. 구현 후에는 `npm run type-check`와 가능한 범위의 빌드 검증을 수행합니다.
