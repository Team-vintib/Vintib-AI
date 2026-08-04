# SY027 회원가입 이메일 인증 흐름 개선

## 배경/목표

회원가입 폼의 "중복 확인" → "인증코드 발송" 2단계 흐름을 "인증코드 발송" 버튼 하나로 합친다. 클릭 시 중복확인 후 통과하면 바로 인증코드를 발송한다. 코드 발송 후에는 "인증코드" 라벨 옆에 5분 카운트다운 타이머(작고 얇은 빨간 글씨)를 표시한다. `docs/requests/FE/015-signup-email-verification-ux.md`에 이미 요청돼 있던 내용이고, BE의 `CODE_TTL`(5분) 확인 완료.

## 작업 내용

- `EmailVerificationField.vue`: 중복확인 버튼/props/emit 제거. `isDuplicateChecked` prop을 `isCodeSent`로 교체(코드 발송 여부로 입력창/확인버튼 게이트). "인증코드" 라벨 옆 타이머 `<span>`(`codeExpiresInLabel` prop) 추가.
- `SignupForm.vue`: 중복확인 핸들러 + 발송 핸들러를 `handleRequestVerificationCode` 하나로 병합. 발송 성공 시 300초 카운트다운 시작(1초 간격 `setInterval`), 0이 되면 재발송 가능하도록 되돌림. 인증 성공/이메일 재입력/언마운트 시 타이머 정지.
- 재발송 정책: 타이머가 0이 될 때까지 재발송 버튼 비활성화(카운트다운 값 = 재발송 가능 시점).

## 구현 목록

- [ ] `EmailVerificationField.vue` 수정
- [ ] `SignupForm.vue` 수정
- [ ] `vue-tsc --noEmit` 통과 확인
