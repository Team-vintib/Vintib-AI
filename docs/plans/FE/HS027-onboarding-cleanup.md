# HS027 — 온보딩 파트 최종 점검 정리

## 배경/목표
온보딩(담당: 김현수) 최종 디자인 전 점검. `docs/requests/FE` 004/005/006 반영. 화면 구조 변경 없이 문구·검증·응답 처리만 손본다.

## 작업 내용
- **전화번호(004)**: 안내 힌트·에러 예시·placeholder에서 하이픈 표기 제거 + 입력/전송을 **숫자만**으로(서버가 `^\d{10,11}$` 검증, 하이픈 넣으면 400).
- **관심(005)**: 저장 시 400 `P008`(없는 브랜드)/`P009`(없는 카테고리) 전용 에러 안내.
- **회원유형(006)**: 완료 응답 바디의 `onboardingCompleted`를 store에 반영(로컬 하드코딩 제거).

## 구현 목록
- [ ] `OnboardingBasicInfoView.vue`: hint/placeholder/에러예시 하이픈 제거, 입력 핸들러 숫자만(11자)
- [ ] `OnboardingInterestsView.vue`: `applyApiError`에 P008/P009 코드 분기
- [ ] `onboarding.ts`: `completeOnboarding` 응답 타입에 프로필(onboardingCompleted 등) 추가
- [ ] `OnboardingMemberTypeView.vue`: 응답 `onboardingCompleted`로 `updateUser`
- [ ] 로컬 확인(5173)

## 브랜치
- `feat/60-member-basic-info-and-preferences` ♻️재사용: 전화번호, 관심
- `feat/60-member-type-selection` ♻️재사용: 회원유형

## Jira
온보딩은 스프린트 8개 티켓에 없음 → **관련 Jira 없음**(수정 없음으로 기록).
