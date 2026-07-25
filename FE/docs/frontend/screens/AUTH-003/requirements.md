# AUTH-003 싸피어스 SSO 로그인

출처: `docs/notion/화면 기반 개발 요구 문서.md`

## 목적

비회원이 SSAFYERS 통합 계정으로 인증을 시작하고, 이메일 로그인으로 돌아갈 수 있게 합니다.

## 추천 라우트

- `/auth/ssafy`

## 진입 경로

- `AUTH-001`의 싸피어스로 가입하기
- `AUTH-002`의 SSAFY로 로그인

## 핵심 구성

- 싸피어스로 로그인 버튼
- 이메일 로그인으로 돌아가기
- 인증 도움말
- SSL 보안 연결 안내
- 2단계 인증 지원 안내

## 입력 및 검증

입력 필드는 없습니다.

## 주요 동작

| 사용자 행동 | 처리 | 결과 |
| --- | --- | --- |
| 싸피어스로 로그인 | SSO 인증 시작 | 인증 후 `AUTH-004-2` 또는 `AUTH-004` |
| 이메일 로그인으로 돌아가기 | 이메일 로그인 화면 이동 | `AUTH-002` |

## 연동 데이터

- 임시 callback 후보: `POST /api/auth/ssafy/callback`
- 요청 후보: `authorizationCode`, `redirectUri`
- 응답 후보: `linked`, `nextStep`, `user`

## 상태 및 예외

- SSO 인증 실패
- SSO 인증 취소
- redirect 오류
- 기존 계정 연결 필요

## 미확정

- SSO 식별자와 기존 계정 연결 기준
- redirect URI 허용 목록
