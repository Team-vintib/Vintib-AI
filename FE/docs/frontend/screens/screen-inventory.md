# 화면 목록

출처: `docs/notion/화면 기반 개발 요구 문서.md`

## 인증 우선 구현 화면

| 화면 ID     | 화면명                    | 권한             | 추천 라우트               | 구현 우선순위 | 상태                                                     |
| ----------- | ------------------------- | ---------------- | ------------------------- | ------------- | -------------------------------------------------------- |
| AUTH-001    | 이메일 회원가입           | 비회원           | `/auth/signup/email`      | 1             | FE 완료, BE 메일 환경변수 이슈로 이메일 발송 재검증 필요 |
| AUTH-002    | 이메일 로그인             | 비회원           | `/auth/login`             | 1             | FE 완료, BE 로그인 API E2E 재검증 필요                   |
| AUTH-001-0  | 회원가입 방식 선택        | 비회원           | `/auth/signup`            | 1             | FE 완료                                                  |
| AUTH-003    | 싸피어스 SSO 로그인       | 비회원           | `/auth/ssafy/login`       | 1             | FE 완료, BE SSO E2E 재검증 필요                          |
| AUTH-003-1  | 싸피어스 SSO 가입         | 비회원           | `/auth/ssafy/signup`      | 1             | FE 완료, BE SSO E2E 재검증 필요                          |
| AUTH-004-2  | 싸피 로그인 완료 안내     | 비회원           | `/auth/ssafy/callback`    | 1             | FE 완료, BE SSO E2E 재검증 필요                          |
| AUTH-004    | 기존 계정 연결            | 비회원/회원 후보 | `/auth/link-account`      | 1             | FE 완료, BE 계정 연결 API 대기                           |
| ONBOARD-001 | 기본 정보 입력            | 회원             | `/onboarding/basic-info`  | 2             | FE 완료, BE API 대기                                     |
| ONBOARD-002 | 관심 브랜드/카테고리 설정 | 회원             | `/onboarding/interests`   | 2             | FE 완료, BE API 대기                                     |
| ONBOARD-003 | 전신 사진/신체 정보 등록  | 회원             | `/onboarding/try-on`      | 2             | FE 완료, 저장 BE API 대기                                |
| ONBOARD-004 | 일반/사업자 회원 선택     | 회원             | `/onboarding/member-type` | 2             | FE 완료, 저장 BE API 대기. 일반은 HOME, 사업자는 BIZ-001로 이동 |
| BIZ-001     | 사업자 정보 제출          | 사업자 회원      | `/business/verification`  | 2             | FE 입력 제약·더미 제출·BIZ-001-2 인증 대기 화면과 HOME 이동 완료, BE API 대기 |

## 이후 화면 묶음

| 묶음                | 화면 ID                                                        | 상태   |
| ------------------- | -------------------------------------------------------------- | ------ |
| 홈/탐색             | HOME-001, HOME-002, SEARCH-001, SEARCH-002                     | HOME-001/002 홈 화면 구현, SEARCH는 `/search` route 후보만 연결 |
| 상품                | PROD-001~013                                                   | PROD-008 목록 껍데기와 PROD-006 상품 상세 408 정적 UI 구현, 상세 상호작용·상태 및 나머지 미구현 |
| 라이브              | LIVE-001~007                                                   | 미구현 |
| 경매                | AUCT-001~014                                                   | 미구현 |
| 구매/주문/배송/환불 | SALE-001, ORDER-001~ORDER-003, SHIP-001~SHIP-002, REFUND-001 | 미구현 |
| 포인트              | POINT-001~006                                                  | 미구현 |
| AI 시착             | TRYON-001~004                                                  | 미구현 |
| 마이페이지          | MY-001~009                                                     | 미구현 |
| 알림                | NOTI-001~005                                                   | 미구현 |

## 라우트 제안 원칙

- 화면 ID는 문서와 추적용으로 유지합니다.
- URL은 사용자가 이해하기 쉬운 영문 명사 중심으로 제안합니다.
- 인증이 필요한 화면은 라우트 가드에서 `requiresAuth` 메타를 사용합니다.
- 미확정 이동은 구현하지 않고 `docs/frontend/decisions/open-questions.md`에 기록합니다.
