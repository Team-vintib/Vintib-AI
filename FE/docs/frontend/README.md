# VinTib 프론트엔드 구현 준비 문서

이 폴더는 Notion 원본 문서를 화면 구현에 바로 사용할 수 있도록 재구성한 작업 문서입니다.

## 원본 기준 문서

- `docs/notion/기능 정의서.md`
- `docs/notion/화면 기반 개발 요구 문서.md`
- `docs/notion/프론트엔드 개발 공통 규칙.md`
- `docs/notion/프론트엔드 디자인 구현 규칙.md`

## 확정된 작업 기준

- 화면 구현 기준: 화면 기반 개발 요구 문서
- Figma Make와 화면 기반 문서가 다를 때: 화면 기반 문서 우선
- 화면 연결 기준: Figma Wireframe Copy
- 첫 구현 묶음: 인증
- 라우트 URL 제안: Codex 허용
- Mock 데이터 선구현: 허용
- API 명세: Swagger 제공 예정, 제공 전까지 임시 후보 사용
- 반응형: 1440px desktop first 우선

## 폴더 역할

- `product/`: 기능 범위, MVP, 제외 범위
- `screens/`: 화면 ID별 요구사항
- `flows/`: 사용자 흐름과 라우팅 초안
- `auth/`: 권한과 라우트 가드 기준
- `design-system/`: 디자인 토큰과 공통 UI 규칙
- `api/`: Swagger 전 임시 API 후보와 Mock 기준
- `components/`: 공통 컴포넌트 후보와 우선순위
- `implementation/`: 현재 코드 구조와 구현 상태
- `decisions/`: 미확정 사항과 결정 기록
- `testing/`: 화면별 완료 조건
