# 회원가입 이메일 인증 UX 개선

**요청자 파트**: BE(사용자 피드백 전달)
**대상 파트**: FE

## 배경

`SignupForm.vue`/`EmailVerificationField.vue`(이메일 중복 확인 → 인증코드 발송 → 인증코드 확인) 흐름에
대한 UX 피드백. 지금은 중복 확인이 성공해도 "인증코드를 발송해 주세요" 메시지만 뜨고, 사용자가
"인증코드 발송" 버튼을 별도로 눌러야 한다(`handleSendVerificationCode`는 자동 호출되지 않음).
타이머 UI도 없다.

## 요청 내용

1. **중복 확인 성공 시 인증코드 자동 발송**: `checkEmailDuplicate` 응답이 성공(200)이면
   `handleSendVerificationCode`를 바로 이어서 호출해줘 — 사용자가 "인증코드 발송" 버튼을 따로
   누르지 않아도 되게.
2. **5분 타이머 표시 + 만료 시 재발송 버튼 활성화**: 인증코드 발송 후 인증코드 입력란 아래에
   카운트다운(5분)을 보여주고, 5분이 다 지나면 그때 "재발송" 버튼을 활성화해줘.
   - BE `EmailVerificationService.CODE_TTL`이 정확히 5분이라 숫자가 일치한다.
   - 참고: BE는 별도로 60초 재발송 쿨다운(`RESEND_COOLDOWN`)만 두고 있어서, 원한다면 60초 후에도
     재발송을 열어줄 수 있다 — 이번 요청은 "5분 다 채우고 열기"로 더 엄격하게 가는 것이니, 60초
     쿨다운 쪽으로 바꾸고 싶으면 그렇게 조정해도 BE 쪽엔 문제없다.

## 관련 자료

- `BE/src/main/java/com/ssafy/backend/auth/service/EmailVerificationService.java`(TTL/쿨다운 상수)
- `FE/src/domains/auth/components/SignupForm.vue`, `EmailVerificationField.vue`

## 처리 결과

(FE 반영 후 기입)
