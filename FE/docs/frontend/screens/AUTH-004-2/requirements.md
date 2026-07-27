# AUTH-004-2 싸피 인증 callback 처리

출처: `docs/notion/화면 기반 개발 요구 문서.md`

## 목적

SSAFYERS 인증 callback 응답을 처리하고 다음 단계로 이동합니다.

## 추천 라우트

- `/auth/ssafy/callback`

## 진입 경로

- `AUTH-003` 또는 `AUTH-003-1` 인증 callback

## 핵심 구성

- 인증 처리 중 안내
- 인증 실패 안내
- 다시 인증하기 버튼
- 로그인 또는 회원가입 선택 화면으로 돌아가기

## 입력 및 검증

| 항목              | 필수 | 조건                  | 오류 처리       |
| ----------------- | ---- | --------------------- | --------------- |
| authorizationCode | 필수 | callback query `code` | 오류 안내       |
| source            | 선택 | `login` 또는 `signup` | 기본값 `signup` |

## 주요 동작

| 사용자 행동   | 처리                       | 결과                                     |
| ------------- | -------------------------- | ---------------------------------------- |
| callback 처리 | `nextStep` 확인            | `AUTH-004`, `ONBOARD-001` 또는 홈        |
| 다시 인증하기 | SSO 재시도                 | source 기준 `AUTH-003` 또는 `AUTH-003-1` |
| 돌아가기      | source 기준 이전 화면 이동 | `AUTH-002` 또는 `AUTH-001-0`             |

## 연동 데이터

- `POST /api/auth/ssafy/callback` 응답의 `accessToken`, `linked`, `nextStep`, `user`, `email`

## 상태 및 예외

- callback code 누락
- 인증 만료
- 기존 계정 연결 필요
- 온보딩 필요

## 미확정

- `싸피`와 `싸피어스` 표기 최종 통일
- 인증 성공 정보 표시 화면을 별도로 둘지 여부
