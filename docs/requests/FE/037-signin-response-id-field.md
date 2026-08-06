# 037 로그인/재발급 응답에 `id` 추가 (GET /api/me 대체)

## 요청자 파트 / 대상 파트

BE → FE

## 배경/이유

`001-auth-contract.md`에서 `GET /api/me` 신설과 `signin`/`reissue` 응답에 `user`/`nextStep`
전체 추가를 요청했었다. 별도 엔드포인트나 중첩 `user` 객체 없이, **가장 작은 변경으로 같은
문제를 해결**하기로 했다 — FE가 로그인 직후 자기 자신의 `id`를 몰라서 기존
`GET /api/users/{id}`(이미 email/name/nickname/memberType/onboardingCompleted/
businessVerificationStatus 등 필요한 필드를 전부 갖고 있음)를 못 부르는 게 진짜 문제였다.

## 요청 내용

- `POST /api/auth/signin`, `POST /api/auth/reissue`, `POST /api/auth/google`,
  `POST /api/auth/google/link` 응답에 `id`(회원 id, number) 필드가 추가됐다.
- 사용 방법: 로그인 성공 후 응답의 `id`로 바로 `GET /api/users/{id}`를 호출하면 온보딩 상태를
  포함한 전체 프로필을 받을 수 있다. JWT를 직접 디코딩해서 `sub`를 꺼내던 방식은 더 이상 필요
  없다.
- **하지 않은 것**: `GET /api/me` 엔드포인트는 만들지 않았다. `user` 전체 객체나 `nextStep`도
  로그인 응답에 넣지 않았다 — 프로필이 필요하면 `id`로 `GET /api/users/{id}`를 한 번 더
  호출해야 한다(요청-응답 왕복이 하나 늘지만 계약이 단순해진다).
- 회원가입 직후 자동 로그인, `memberType` 기본값 등 `001`의 나머지 협의 사항은 전부 **현재
  구현 그대로 유지**하기로 확정했다(추가 변경 없음).

### 응답 예시 (`POST /api/auth/signin`)

```json
{
  "success": true,
  "data": {
    "accessToken": "eyJ...",
    "refreshToken": "eyJ...",
    "id": 1
  },
  "error": null
}
```

## 관련 자료

- 원 요청: `docs/requests/BE/001-auth-contract.md` §3.1·§4 (삭제됨)
- 구현: `TokenResponse`, `GoogleAuthResponse`, `AuthService#issueTokens`
- 기존 프로필 조회: `GET /api/users/{id}` (`UserController`, `MemberProfileResponse`)
